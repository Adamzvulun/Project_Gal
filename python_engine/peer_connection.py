"""
Peer connection module.

Manages a single TCP connection to one peer using the Peer Wire Protocol (BEP-3).
Handles handshake, message parsing, state machine, and message sending/receiving.
"""

import asyncio
import collections
import logging
import struct
import time
from enum import IntEnum
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Protocol constants
PROTOCOL_STRING = b'BitTorrent protocol'
PROTOCOL_STRING_LEN = len(PROTOCOL_STRING)
HANDSHAKE_LEN = 1 + PROTOCOL_STRING_LEN + 8 + 20 + 20  # 68 bytes
BLOCK_SIZE = 16384  # 16 KB - standard block size
MAX_MESSAGE_SIZE = 2 * 1024 * 1024  # 2 MB max message size
CONNECTION_TIMEOUT = 30  # seconds
REQUEST_TIMEOUT = 60  # seconds
MAX_PENDING_REQUESTS = 50

# Retention window for per-peer download samples. Must be >= the longest
# sliding window any consumer will query (currently 20s for tit-for-tat,
# 30s for download_rate display).
DOWNLOAD_SAMPLE_RETENTION = 30  # seconds

# Symmetric retention for per-peer upload samples. Used by seeding-mode
# tit-for-tat which sorts by bytes_sent_in_window instead of received.
UPLOAD_SAMPLE_RETENTION = 30  # seconds

# A peer that has unchoked us but sent no PIECE for this long is "snubbed":
# the unchoke loop demotes them so they don't permanently hold a slot.
# Matches mainline BitTorrent / libtorrent (Cohen 2003 §3).
SNUB_THRESHOLD = 60.0  # seconds


class MessageType(IntEnum):
    """Peer Wire Protocol message types."""
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8
    KEEP_ALIVE = -1  # Special: 0-length message


class PeerMessage:
    """Represents a parsed peer wire protocol message."""

    def __init__(self, msg_type: MessageType, payload: bytes = b''):
        self.type = msg_type
        self.payload = payload
        self.timestamp = time.time()

    @property
    def piece_index(self) -> Optional[int]:
        """For HAVE, REQUEST, PIECE, CANCEL messages: the piece index."""
        if self.type in (MessageType.HAVE,):
            return struct.unpack('!I', self.payload[:4])[0]
        if self.type in (MessageType.REQUEST, MessageType.PIECE, MessageType.CANCEL):
            return struct.unpack('!I', self.payload[:4])[0]
        return None

    @property
    def block_offset(self) -> Optional[int]:
        """For REQUEST, PIECE, CANCEL: the block offset within the piece."""
        if self.type in (MessageType.REQUEST, MessageType.CANCEL):
            return struct.unpack('!I', self.payload[4:8])[0]
        if self.type == MessageType.PIECE:
            return struct.unpack('!I', self.payload[4:8])[0]
        return None

    @property
    def block_length(self) -> Optional[int]:
        """For REQUEST, CANCEL: the requested block length."""
        if self.type in (MessageType.REQUEST, MessageType.CANCEL):
            return struct.unpack('!I', self.payload[8:12])[0]
        return None

    @property
    def block_data(self) -> Optional[bytes]:
        """For PIECE: the actual block data."""
        if self.type == MessageType.PIECE:
            return self.payload[8:]
        return None

    @property
    def bitfield_data(self) -> Optional[bytes]:
        """For BITFIELD: the raw bitfield bytes."""
        if self.type == MessageType.BITFIELD:
            return self.payload
        return None

    def __repr__(self):
        return f"PeerMessage({self.type.name}, payload_len={len(self.payload)})"


class PeerConnectionError(Exception):
    """Raised when peer connection encounters an error."""
    pass


class PeerConnection:
    """Manages a TCP connection to a single BitTorrent peer.

    Implements the Peer Wire Protocol with full state machine management.

    State machine:
        am_choking: We are choking the peer (default: True)
        am_interested: We are interested in the peer (default: False)
        peer_choking: Peer is choking us (default: True)
        peer_interested: Peer is interested in us (default: False)
    """

    def __init__(self, ip: str, port: int, info_hash: bytes, peer_id: bytes,
                 num_pieces: int, on_message: Optional[Callable] = None):
        """Initialize peer connection.

        Args:
            ip: Peer's IP address.
            port: Peer's port.
            info_hash: 20-byte torrent info hash.
            peer_id: Our 20-byte peer ID.
            num_pieces: Total number of pieces in the torrent.
            on_message: Optional callback for received messages.
        """
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.our_peer_id = peer_id
        self.num_pieces = num_pieces
        self.on_message = on_message

        # Peer info
        self.remote_peer_id: Optional[bytes] = None

        # State machine
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        # Peer's pieces (bitfield)
        self.peer_pieces = [False] * num_pieces

        # Connection state
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._handshake_complete = False
        self._read_task: Optional[asyncio.Task] = None

        # Statistics
        self.bytes_downloaded = 0
        self.bytes_uploaded = 0
        self.download_rate = 0.0  # bytes per second
        # (timestamp, bytes_received) samples retained for
        # DOWNLOAD_SAMPLE_RETENTION seconds. Used both for the rate display
        # and for tit-for-tat's sliding-window contribution metric.
        self._download_samples: "collections.deque[tuple[float, int]]" = collections.deque()
        # Symmetric (timestamp, bytes_sent) samples used by seeding-mode
        # tit-for-tat to rank peers by how fast we are uploading to them.
        self._upload_samples: "collections.deque[tuple[float, int]]" = collections.deque()
        self._last_activity = 0
        self._pending_requests = 0
        self._last_request_time: float = 0
        self._last_piece_time: float = 0  # last time we received a PIECE response
        # Timestamp the handshake completed. Used as the fallback "last signal"
        # for snubbing detection so a freshly-unchoked peer gets the full
        # threshold to deliver its first block before being marked snubbed.
        self._connect_time: float = 0

    @property
    def connected(self) -> bool:
        return self._connected and self._handshake_complete

    async def connect(self):
        """Establish TCP connection and perform handshake."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port),
                timeout=CONNECTION_TIMEOUT
            )
            self._connected = True
            self._last_activity = time.time()
            logger.info(f"TCP connected to {self.ip}:{self.port}")
        except (asyncio.TimeoutError, OSError) as e:
            raise PeerConnectionError(f"Failed to connect to {self.ip}:{self.port}: {e}")

        # Perform handshake
        await self._send_handshake()
        await self._receive_handshake()
        self._handshake_complete = True
        self._connect_time = time.time()
        logger.info(f"Handshake complete with {self.ip}:{self.port}")

    async def _send_handshake(self):
        """Send the BitTorrent handshake message."""
        handshake = (
            bytes([PROTOCOL_STRING_LEN]) +
            PROTOCOL_STRING +
            b'\x00' * 8 +  # Reserved bytes
            self.info_hash +
            self.our_peer_id
        )
        self._writer.write(handshake)
        await self._writer.drain()

    async def _receive_handshake(self):
        """Receive and validate the peer's handshake."""
        try:
            data = await asyncio.wait_for(
                self._reader.readexactly(HANDSHAKE_LEN),
                timeout=CONNECTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise PeerConnectionError("Handshake timeout")
        except asyncio.IncompleteReadError:
            raise PeerConnectionError("Connection closed during handshake")

        # Parse handshake
        pstrlen = data[0]
        if pstrlen != PROTOCOL_STRING_LEN:
            raise PeerConnectionError(f"Invalid protocol string length: {pstrlen}")

        pstr = data[1:1 + pstrlen]
        if pstr != PROTOCOL_STRING:
            raise PeerConnectionError(f"Invalid protocol string: {pstr!r}")

        # reserved = data[1 + pstrlen:1 + pstrlen + 8]  # Can check for extensions
        received_info_hash = data[1 + pstrlen + 8:1 + pstrlen + 8 + 20]
        self.remote_peer_id = data[1 + pstrlen + 8 + 20:1 + pstrlen + 8 + 40]

        if received_info_hash != self.info_hash:
            raise PeerConnectionError("Info hash mismatch during handshake")

        self._last_activity = time.time()

    async def start_message_loop(self):
        """Start the message reading loop."""
        self._read_task = asyncio.create_task(self._message_loop())

    async def _message_loop(self):
        """Continuously read and process messages from the peer."""
        try:
            while self._connected:
                message = await self._read_message()
                if message is None:
                    break
                self._last_activity = time.time()
                await self._handle_message(message)
        except PeerConnectionError as e:
            logger.warning(f"Peer {self.ip}:{self.port} error: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Unexpected error from peer {self.ip}:{self.port}: {e}")
        finally:
            await self.disconnect()

    async def _read_message(self) -> Optional[PeerMessage]:
        """Read a single length-prefixed message from the peer."""
        try:
            length_bytes = await asyncio.wait_for(
                self._reader.readexactly(4),
                timeout=REQUEST_TIMEOUT * 2
            )
        except asyncio.TimeoutError:
            raise PeerConnectionError("Read timeout")
        except asyncio.IncompleteReadError:
            return None  # Connection closed

        length = struct.unpack('!I', length_bytes)[0]

        if length == 0:
            return PeerMessage(MessageType.KEEP_ALIVE)

        if length > MAX_MESSAGE_SIZE:
            raise PeerConnectionError(
                f"Message too large: {length} bytes (max {MAX_MESSAGE_SIZE})"
            )

        try:
            payload = await asyncio.wait_for(
                self._reader.readexactly(length),
                timeout=REQUEST_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise PeerConnectionError("Payload read timeout")
        except asyncio.IncompleteReadError:
            return None

        msg_id = payload[0]
        msg_payload = payload[1:]

        try:
            msg_type = MessageType(msg_id)
        except ValueError:
            logger.warning(f"Unknown message type {msg_id} from {self.ip}:{self.port}")
            return None

        return PeerMessage(msg_type, msg_payload)

    async def _handle_message(self, message: PeerMessage):
        """Process a received message and update state."""
        if message.type == MessageType.KEEP_ALIVE:
            return

        elif message.type == MessageType.CHOKE:
            self.peer_choking = True
            self._pending_requests = 0
            logger.debug(f"Peer {self.ip}:{self.port} choked us")

        elif message.type == MessageType.UNCHOKE:
            self.peer_choking = False
            logger.debug(f"Peer {self.ip}:{self.port} unchoked us")

        elif message.type == MessageType.INTERESTED:
            self.peer_interested = True
            logger.debug(f"Peer {self.ip}:{self.port} is interested")

        elif message.type == MessageType.NOT_INTERESTED:
            self.peer_interested = False
            logger.debug(f"Peer {self.ip}:{self.port} is not interested")

        elif message.type == MessageType.HAVE:
            piece_index = message.piece_index
            if 0 <= piece_index < self.num_pieces:
                self.peer_pieces[piece_index] = True
            else:
                raise PeerConnectionError(
                    f"Invalid piece index in HAVE: {piece_index}"
                )

        elif message.type == MessageType.BITFIELD:
            self._parse_bitfield(message.bitfield_data)

        elif message.type == MessageType.PIECE:
            data_len = len(message.block_data) if message.block_data else 0
            self.bytes_downloaded += data_len
            self._pending_requests = max(0, self._pending_requests - 1)
            now = time.time()
            self._last_piece_time = now
            self._download_samples.append((now, data_len))
            # Evict samples outside the retention window.
            cutoff = now - DOWNLOAD_SAMPLE_RETENTION
            while self._download_samples and self._download_samples[0][0] < cutoff:
                self._download_samples.popleft()
            if self._download_samples:
                total_bytes = sum(b for _, b in self._download_samples)
                duration = now - self._download_samples[0][0]
                if duration > 0:
                    self.download_rate = total_bytes / duration

        elif message.type == MessageType.REQUEST:
            pass  # Will be handled by download manager

        elif message.type == MessageType.CANCEL:
            pass  # Will be handled by download manager

        # Notify callback
        if self.on_message:
            await self.on_message(self, message)

    def _parse_bitfield(self, data: bytes):
        """Parse a bitfield message into the peer_pieces array."""
        for byte_idx, byte_val in enumerate(data):
            for bit_idx in range(8):
                piece_idx = byte_idx * 8 + bit_idx
                if piece_idx >= self.num_pieces:
                    break
                self.peer_pieces[piece_idx] = bool(byte_val & (1 << (7 - bit_idx)))

    # -- Sending messages --

    async def send_message(self, msg_type: MessageType, payload: bytes = b''):
        """Send a message to the peer.

        Args:
            msg_type: The message type.
            payload: The message payload (without message ID).
        """
        if not self._connected:
            raise PeerConnectionError("Not connected")

        if msg_type == MessageType.KEEP_ALIVE:
            data = struct.pack('!I', 0)
        else:
            msg_id = bytes([int(msg_type)])
            full_payload = msg_id + payload
            data = struct.pack('!I', len(full_payload)) + full_payload

        try:
            self._writer.write(data)
            await self._writer.drain()
        except (OSError, ConnectionError) as e:
            raise PeerConnectionError(f"Failed to send message: {e}")

    async def send_interested(self):
        """Send INTERESTED message and update state."""
        await self.send_message(MessageType.INTERESTED)
        self.am_interested = True

    async def send_not_interested(self):
        """Send NOT_INTERESTED message and update state."""
        await self.send_message(MessageType.NOT_INTERESTED)
        self.am_interested = False

    async def send_choke(self):
        """Send CHOKE message and update state."""
        await self.send_message(MessageType.CHOKE)
        self.am_choking = True

    async def send_unchoke(self):
        """Send UNCHOKE message and update state."""
        await self.send_message(MessageType.UNCHOKE)
        self.am_choking = False

    async def send_have(self, piece_index: int):
        """Send HAVE message for a completed piece."""
        payload = struct.pack('!I', piece_index)
        await self.send_message(MessageType.HAVE, payload)

    async def send_bitfield(self, pieces: list):
        """Send BITFIELD message with our current pieces.

        Args:
            pieces: List of booleans indicating which pieces we have.
        """
        num_bytes = (len(pieces) + 7) // 8
        bitfield = bytearray(num_bytes)
        for i, have in enumerate(pieces):
            if have:
                bitfield[i // 8] |= (1 << (7 - (i % 8)))
        await self.send_message(MessageType.BITFIELD, bytes(bitfield))

    async def send_request(self, piece_index: int, begin: int, length: int):
        """Send REQUEST message for a block.

        Args:
            piece_index: Index of the piece.
            begin: Byte offset within the piece.
            length: Number of bytes to request.

        Raises:
            PeerConnectionError: If peer is choking or too many pending requests.
        """
        if self.peer_choking:
            raise PeerConnectionError("Cannot request: peer is choking us")
        if self._pending_requests >= MAX_PENDING_REQUESTS:
            raise PeerConnectionError("Too many pending requests")

        payload = struct.pack('!III', piece_index, begin, length)
        await self.send_message(MessageType.REQUEST, payload)
        self._pending_requests += 1
        self._last_request_time = time.time()

    async def send_piece(self, piece_index: int, begin: int, data: bytes):
        """Send PIECE message with block data.

        Args:
            piece_index: Index of the piece.
            begin: Byte offset within the piece.
            data: The block data.
        """
        payload = struct.pack('!II', piece_index, begin) + data
        await self.send_message(MessageType.PIECE, payload)
        data_len = len(data)
        self.bytes_uploaded += data_len
        # Mirror of the download path: append a sample and evict stale
        # entries left-to-right so the deque stays bounded.
        now = time.time()
        self._upload_samples.append((now, data_len))
        cutoff = now - UPLOAD_SAMPLE_RETENTION
        while self._upload_samples and self._upload_samples[0][0] < cutoff:
            self._upload_samples.popleft()

    async def send_cancel(self, piece_index: int, begin: int, length: int):
        """Send CANCEL message for a previously requested block."""
        payload = struct.pack('!III', piece_index, begin, length)
        await self.send_message(MessageType.CANCEL, payload)

    async def send_keep_alive(self):
        """Send a keep-alive message (zero-length)."""
        await self.send_message(MessageType.KEEP_ALIVE)

    async def disconnect(self):
        """Close the connection to the peer."""
        self._connected = False
        self._handshake_complete = False

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass

        logger.info(f"Disconnected from {self.ip}:{self.port}")

    @property
    def can_request(self) -> bool:
        """Check if we can send more requests to this peer."""
        if not self._connected or self.peer_choking:
            return False
        if self._pending_requests >= MAX_PENDING_REQUESTS:
            # If we have pending requests but haven't received a response in 15s,
            # the counter is likely stuck — reset it
            if self._last_request_time > 0 and self._pending_requests > 0:
                time_since_last_piece = time.time() - max(self._last_piece_time, self._last_request_time)
                if time_since_last_piece > 15:
                    logger.debug(f"Resetting stuck _pending_requests for {self.ip}:{self.port}")
                    self._pending_requests = 0
                    return True
            return False
        return True

    @property
    def request_capacity(self) -> int:
        """How many more requests we can send to this peer."""
        return max(0, MAX_PENDING_REQUESTS - self._pending_requests)

    def has_piece(self, piece_index: int) -> bool:
        """Check if the peer has a specific piece."""
        if 0 <= piece_index < len(self.peer_pieces):
            return self.peer_pieces[piece_index]
        return False

    def time_since_last_activity(self) -> float:
        """Seconds since last message received."""
        if self._last_activity == 0:
            return float('inf')
        return time.time() - self._last_activity

    def bytes_received_in_window(self, window: float = 20.0) -> int:
        """Bytes received from this peer within the last `window` seconds.

        This is the sliding-window contribution metric used by tit-for-tat
        unchoke decisions. Reading older samples than the retention window
        (DOWNLOAD_SAMPLE_RETENTION) yields a truncated answer — callers
        should not pass a window larger than retention.

        Pure read: does not mutate the sample deque (eviction happens on
        PIECE message receipt).
        """
        if not self._download_samples:
            return 0
        cutoff = time.time() - window
        total = 0
        for t, b in self._download_samples:
            if t >= cutoff:
                total += b
        return total

    def bytes_sent_in_window(self, window: float = 20.0) -> int:
        """Bytes uploaded to this peer within the last `window` seconds.

        Seeding-mode tit-for-tat sorts by this metric: when we're a pure
        seeder we have nothing to receive, so the leech sort key
        (bytes_received_in_window) is permanently zero. Picking peers
        that are draining our upload fastest helps the swarm most.

        Pure read; does not mutate the deque (eviction happens on
        send_piece). Caller must not pass a window > UPLOAD_SAMPLE_RETENTION.
        """
        if not self._upload_samples:
            return 0
        cutoff = time.time() - window
        total = 0
        for t, b in self._upload_samples:
            if t >= cutoff:
                total += b
        return total

    def is_snubbed(self, threshold: float = SNUB_THRESHOLD) -> bool:
        """True iff this peer has unchoked us but stopped delivering blocks.

        A peer is snubbed when all of the following hold:
            * `peer_choking is False` — they advertised willingness to send,
              so silence is on them, not us.
            * `_last_request_time > 0` — we have actually asked them for at
              least one block. A peer we never queried can't be snubbing us.
            * `now - last_signal > threshold` — where `last_signal` is the
              most recent of: last PIECE received, or handshake completion.
              The connect-time fallback gives a freshly-unchoked peer the
              full threshold to deliver its first block.

        If `peer_choking is True` we can't tell whether silence is snubbing
        or normal choking, so we return False — the choke decision will
        rotate them out naturally.
        """
        if self.peer_choking:
            return False
        if self._last_request_time <= 0:
            return False
        last_signal = max(self._last_piece_time, self._connect_time)
        if last_signal <= 0:
            return False
        return (time.time() - last_signal) > threshold

    def __repr__(self):
        state = "connected" if self.connected else "disconnected"
        return f"PeerConnection({self.ip}:{self.port}, {state})"
