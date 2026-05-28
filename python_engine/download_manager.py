"""
Download manager module.

The central brain of the download process. Manages peer connections,
implements choke/unchoke (Tit-for-Tat) and piece selection algorithms,
and coordinates the overall download flow.
"""

import asyncio
import collections
import concurrent.futures
import json
import logging
import os
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from . import bencode
from .peer_connection import PeerConnection, PeerMessage, MessageType, PeerConnectionError, BLOCK_SIZE
from .piece_manager import PieceManager, PieceStatus, Block
from .tracker_client import TrackerClient, Peer, TrackerResponse, generate_peer_id
from .torrent_metadata import TorrentMetadata
from .security import SecurityManager

logger = logging.getLogger(__name__)

# Constants
CHOKE_INTERVAL = 10  # seconds between choke/unchoke decisions
MAX_UNCHOKED_PEERS = 4  # number of peers to unchoke
MAX_CONNECTIONS = 50
KEEP_ALIVE_INTERVAL = 60  # seconds
PIECE_REQUEST_TIMEOUT = 30  # seconds before resetting a stale in-progress piece
PEER_CLEANUP_INTERVAL = 15  # seconds between dead peer cleanup passes
# Tit-for-tat sliding-window length. Two choke cycles (CHOKE_INTERVAL=10s)
# fit inside this window, so the metric is stable across cycles.
TIT_FOR_TAT_WINDOW = 20  # seconds


class DownloadState(Enum):
    """States of a download."""
    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    # Post-completion live state: download is done but we keep serving
    # peers. Distinct from COMPLETED (terminal) so the choke loop can
    # keep running and the seed-mode branch of _tit_for_tat_unchoke
    # activates. _load_state restores complete-on-disk downloads as
    # COMPLETED; user action (start) promotes them to SEEDING.
    SEEDING = "Seeding"
    CANCELLED = "Cancelled"
    ERROR = "Error"


class AlgorithmType(Enum):
    """Piece/peer selection algorithm type."""
    RAREST_FIRST = "rarest_first"
    RANDOM = "random"
    TIT_FOR_TAT = "tit_for_tat"
    ROUND_ROBIN = "round_robin"


class DownloadStats:
    """Statistics for a download."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.bytes_downloaded = 0
        self.bytes_uploaded = 0
        self.download_speed = 0.0
        self.upload_speed = 0.0
        self.connected_peers = 0
        self.total_peers_seen = 0
        self.peak_speed = 0.0
        self.choke_count = 0
        self.unchoke_count = 0
        self.choke_cycles = 0   # number of times the peer algo ran

    @property
    def elapsed_time(self) -> float:
        if self.start_time is None:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def average_speed(self) -> float:
        elapsed = self.elapsed_time
        if elapsed > 0:
            return self.bytes_downloaded / elapsed
        return 0.0


class Download:
    """Manages the download of a single torrent.

    Coordinates tracker communication, peer connections, piece selection,
    and data verification.
    """

    def __init__(self, torrent: TorrentMetadata, download_dir: str,
                 state_dir: str,
                 piece_algorithm: AlgorithmType = AlgorithmType.RAREST_FIRST,
                 peer_algorithm: AlgorithmType = AlgorithmType.TIT_FOR_TAT):
        self.id = str(uuid.uuid4())[:8]
        self.torrent = torrent
        self.download_dir = download_dir
        self.state_dir = state_dir
        self.piece_algorithm = piece_algorithm
        self.peer_algorithm = peer_algorithm

        self.state = DownloadState.QUEUED
        self.stats = DownloadStats()
        self.security = SecurityManager()

        # Peer management
        self.peer_id = generate_peer_id()
        self._connections: Dict[str, PeerConnection] = {}
        self._tracker: Optional[TrackerClient] = None
        self._known_peers: Set[Peer] = set()

        # Piece management
        self.piece_manager = PieceManager(
            num_pieces=torrent.num_pieces,
            piece_length=torrent.piece_length,
            total_size=torrent.total_size,
            piece_hashes=torrent.pieces
        )

        # Async tasks
        self._main_task: Optional[asyncio.Task] = None
        self._choke_task: Optional[asyncio.Task] = None
        self._keep_alive_task: Optional[asyncio.Task] = None
        self._speed_samples = []

        # Thread pool for hash verification and disk I/O
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        # Per-peer piece assignment: peer_key -> piece_index they're working on
        self._peer_piece: Dict[str, int] = {}

        # Round-robin state
        self._rr_index = 0

        # Snubbing: track which peers we have already logged as snubbed
        # so we don't spam an INFO line every 10-second choke cycle. The
        # entry is removed when a peer leaves the snubbed set.
        self._previously_snubbed: Set[str] = set()

        # Guard to ensure completion logic runs exactly once
        self._completion_handled = False

        # Live log buffer (last 200 messages for GUI polling)
        self._log_buffer = collections.deque(maxlen=200)
        self._log_counter = 0

        # Event callbacks
        self._on_progress = None
        self._on_complete = None
        self._on_state_change = None

    def _log(self, message: str):
        """Add a message to the live log buffer."""
        self._log_counter += 1
        entry = {
            "seq": self._log_counter,
            "time": round(time.time(), 2),
            "msg": message
        }
        self._log_buffer.append(entry)
        logger.info(f"[{self.id}] {message}")

    def get_logs(self, since_seq: int = 0) -> List[dict]:
        """Get log entries newer than since_seq."""
        return [e for e in self._log_buffer if e["seq"] > since_seq]

    @property
    def progress(self) -> float:
        return self.piece_manager.progress

    @property
    def file_name(self) -> str:
        return self.torrent.name

    @property
    def file_size(self) -> int:
        return self.torrent.total_size

    @property
    def connected_peers(self) -> int:
        return sum(1 for c in self._connections.values() if c.connected)

    def on_progress(self, callback: Callable):
        self._on_progress = callback

    def on_complete(self, callback: Callable):
        self._on_complete = callback

    def on_state_change(self, callback: Callable):
        self._on_state_change = callback

    async def start(self):
        """Start the download process."""
        if self.state in (DownloadState.RUNNING,):
            return

        self.state = DownloadState.RUNNING
        self.stats.start_time = time.time()

        self._log(f"Starting download: {self.torrent.name}")
        self._log(f"Size: {self.torrent.total_size} bytes, Pieces: {self.torrent.num_pieces}, Tracker: {self.torrent.announce}")

        self._main_task = asyncio.create_task(self._download_loop())

    async def _download_loop(self):
        """Main download coordination loop."""
        try:
            # Initialize tracker
            self._tracker = TrackerClient(
                announce_url=self.torrent.announce,
                info_hash=self.torrent.info_hash,
                peer_id=self.peer_id,
                port=6881
            )
            self._tracker.left = self.torrent.total_size

            # Initial announce
            self._log(f"Contacting tracker: {self.torrent.announce}")
            response = await self._tracker.announce(event='started',
                                                    left=self.torrent.total_size)
            for peer in response.peers:
                self._known_peers.add(peer)
            self.stats.total_peers_seen = len(self._known_peers)
            self._log(f"Tracker responded: {len(response.peers)} peers found")

            # Start choke/unchoke timer
            self._choke_task = asyncio.create_task(self._choke_loop())
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())

            # Start periodic tracker announces
            await self._tracker.start_periodic_announce(
                callback=self._on_tracker_response
            )

            # Connect to peers (non-blocking — don't wait for all 50 attempts)
            asyncio.create_task(self._connect_to_peers())

            # Main piece request loop
            last_cleanup = time.time()
            while not self.piece_manager.is_complete and self.state == DownloadState.RUNNING:
                # Reset pieces stuck in IN_PROGRESS for too long
                self.piece_manager.reset_stale_pieces(PIECE_REQUEST_TIMEOUT)

                await self._request_pieces()
                await asyncio.sleep(0.1)

                # Periodically clean up dead peers and try new ones
                now = time.time()
                if now - last_cleanup > PEER_CLEANUP_INTERVAL:
                    self._cleanup_dead_peers()
                    await self._connect_to_peers()
                    last_cleanup = now

                # Update stats
                self._update_speed()
                self._tracker.update_stats(
                    uploaded=self.stats.bytes_uploaded,
                    downloaded=self.stats.bytes_downloaded,
                    left=self.piece_manager.bytes_remaining
                )

            if self.piece_manager.is_complete:
                await self._complete_download()

        except asyncio.CancelledError:
            self._log("Download cancelled")
        except Exception as e:
            self._log(f"Download error: {e}")
            logger.error(f"Download error: {e}", exc_info=True)
            self.state = DownloadState.ERROR
        finally:
            self._save_state()

    def _cleanup_dead_peers(self):
        """Remove disconnected peers from the connection pool."""
        dead_keys = [
            key for key, conn in self._connections.items()
            if not conn.connected
        ]
        for key in dead_keys:
            del self._connections[key]
            self._peer_piece.pop(key, None)
            self.piece_manager.clear_peer_requests(key)
            self.piece_manager.remove_peer(key)
            logger.debug(f"Cleaned up dead peer: {key}")

    async def _connect_to_peers(self):
        """Connect to known peers."""
        self._cleanup_dead_peers()

        tasks = []
        for peer in list(self._known_peers):
            peer_key = f"{peer.ip}:{peer.port}"
            if peer_key in self._connections:
                continue
            if self.security.is_peer_banned(peer_key):
                continue
            if len(self._connections) >= MAX_CONNECTIONS:
                break

            tasks.append(self._connect_peer(peer))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _connect_peer(self, peer: Peer):
        """Connect to a single peer."""
        peer_key = f"{peer.ip}:{peer.port}"

        conn = PeerConnection(
            ip=peer.ip,
            port=peer.port,
            info_hash=self.torrent.info_hash,
            peer_id=self.peer_id,
            num_pieces=self.torrent.num_pieces,
            on_message=self._on_peer_message
        )

        try:
            await conn.connect()
            self._connections[peer_key] = conn

            # Send our bitfield
            await conn.send_bitfield(self.piece_manager.get_our_bitfield())

            # Start message loop
            await conn.start_message_loop()

            self._log(f"Connected to peer {peer_key}")
        except PeerConnectionError as e:
            logger.debug(f"Failed to connect to {peer_key}: {e}")
        except Exception as e:
            logger.debug(f"Failed to connect to {peer_key}: {e}")

    async def _on_peer_message(self, conn: PeerConnection, message: PeerMessage):
        """Handle messages from peers."""
        peer_key = f"{conn.ip}:{conn.port}"

        if message.type == MessageType.BITFIELD:
            self.piece_manager.update_peer_pieces(peer_key, conn.peer_pieces)
            # Check if peer has pieces we need
            if self._peer_has_needed_pieces(conn):
                await conn.send_interested()

        elif message.type == MessageType.HAVE:
            piece_idx = message.piece_index
            self.piece_manager.update_peer_have(peer_key, piece_idx)
            if not self.piece_manager.has_piece(piece_idx) and not conn.am_interested:
                await conn.send_interested()

        elif message.type == MessageType.UNCHOKE:
            # Peer unchoked us — immediately try to request pieces
            await self._request_from_peer(peer_key, conn)

        elif message.type == MessageType.CHOKE:
            # Peer choked us — all our pending requests are silently dropped
            # Clear block request state so other peers can pick up those blocks
            self.piece_manager.clear_peer_requests(peer_key)

        elif message.type == MessageType.PIECE:
            piece_idx = message.piece_index
            offset = message.block_offset
            data = message.block_data

            if data is None:
                return

            # Guard: skip if piece is already completed (duplicate from another peer)
            piece = self.piece_manager.pieces[piece_idx]
            if piece.status == PieceStatus.COMPLETED:
                return

            is_complete = self.piece_manager.submit_block(piece_idx, offset, data)
            self.stats.bytes_downloaded += len(data)

            if is_complete:
                # Run hash verification in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                verified = await loop.run_in_executor(
                    self._executor, self.piece_manager.verify_piece, piece_idx
                )
                if verified:
                    self.security.report_successful_piece(peer_key, piece_idx)
                    # Write to disk in thread pool
                    await loop.run_in_executor(
                        self._executor, self._write_piece_sync, piece_idx
                    )
                    done = self.piece_manager.completed_pieces
                    self._log(f"Piece {piece_idx} verified OK ({done}/{self.torrent.num_pieces})")
                    # Clear peer assignment for this piece so peers get new work
                    for pk, pi in list(self._peer_piece.items()):
                        if pi == piece_idx:
                            del self._peer_piece[pk]
                    # Announce to all peers (non-blocking fire-and-forget)
                    asyncio.create_task(self._broadcast_have(piece_idx))
                    if self._on_progress:
                        self._on_progress(self)
                    # Set state immediately on completion so GUI sees it on next poll
                    if self.piece_manager.is_complete:
                        self.state = DownloadState.COMPLETED
                        self.stats.end_time = time.time()
                    # Immediately try to give this peer new work
                    await self._request_from_peer(peer_key, conn)
                else:
                    self._log(f"Piece {piece_idx} HASH FAILED from {peer_key}")
                    self.security.report_hash_failure(peer_key, piece_idx)
                    # Clear peer assignment for the failed piece
                    for pk, pi in list(self._peer_piece.items()):
                        if pi == piece_idx:
                            del self._peer_piece[pk]
                    if self.security.is_peer_banned(peer_key):
                        self._log(f"Banned peer {peer_key} (too many hash failures)")
                        await conn.disconnect()

        elif message.type == MessageType.REQUEST:
            await self._serve_block_request(conn, message)

    async def _serve_block_request(self, conn: PeerConnection, message: PeerMessage):
        """Serve a block to a peer that requested it — the upload path.

        BitTorrent connections are symmetric: a peer we dialed to download
        from can also request pieces from us on the same socket. This is the
        only place send_piece is invoked, so it is what makes us a real
        uploader (and what feeds the seed-mode upload sliding window).
        """
        # Never serve a peer we are choking — that is what choke means.
        if conn.am_choking:
            return

        piece_idx = message.piece_index
        begin = message.block_offset
        length = message.block_length
        if piece_idx is None or begin is None or length is None:
            return

        # Bounds + anti-abuse guards before touching the disk.
        if piece_idx < 0 or piece_idx >= self.torrent.num_pieces:
            return
        if length <= 0 or length > BLOCK_SIZE:
            return
        if self.piece_manager.pieces[piece_idx].status != PieceStatus.COMPLETED:
            return
        if begin < 0 or begin + length > self.torrent.get_piece_length(piece_idx):
            return

        loop = asyncio.get_event_loop()
        block = await loop.run_in_executor(
            self._executor, self._read_block_sync, piece_idx, begin, length
        )
        if not block:
            return
        try:
            await conn.send_piece(piece_idx, begin, block)
            self.stats.bytes_uploaded += len(block)
        except PeerConnectionError:
            pass

    def _peer_has_needed_pieces(self, conn: PeerConnection) -> bool:
        """Check if a peer has pieces we still need."""
        for i in range(self.torrent.num_pieces):
            if not self.piece_manager.has_piece(i) and conn.has_piece(i):
                return True
        return False

    async def _request_pieces(self):
        """Request pieces from unchoked peers using per-peer assignment."""
        for peer_key, conn in list(self._connections.items()):
            if not conn.connected or conn.peer_choking or not conn.am_interested:
                continue
            if not conn.can_request:
                continue
            try:
                await self._request_from_peer(peer_key, conn)
            except Exception as e:
                logger.debug(f"Error requesting from {peer_key}: {e}")

    async def _request_from_peer(self, peer_key: str, conn: PeerConnection):
        """Send block requests to a specific peer.

        Strategy:
        1. If the peer has an assigned piece, continue requesting its blocks
        2. If not (or all blocks requested), assign a new MISSING piece
        3. Fall back to an IN_PROGRESS piece with timed-out blocks (endgame)
        """
        if not conn.connected or conn.peer_choking or not conn.can_request:
            return

        capacity = conn.request_capacity
        if capacity <= 0:
            return

        # Step 1: Continue working on the peer's current piece
        piece_idx = self._peer_piece.get(peer_key)
        if piece_idx is not None:
            piece = self.piece_manager.pieces[piece_idx]
            if piece.status == PieceStatus.IN_PROGRESS:
                blocks = piece.get_requestable_blocks()
                if blocks:
                    sent = await self._send_block_requests(conn, peer_key, blocks, capacity)
                    capacity -= sent
                    if capacity <= 0:
                        return
                # If no requestable blocks left but piece not complete, wait for responses
                if not piece.is_complete and piece.get_pending_blocks():
                    return
            # Piece is complete, failed, or all blocks already requested — clear assignment
            self._peer_piece.pop(peer_key, None)

        # Step 2: Get a new MISSING piece for this peer
        if self.piece_algorithm == AlgorithmType.RAREST_FIRST:
            new_idx = self.piece_manager.select_piece_rarest_first(conn.peer_pieces)
        else:
            new_idx = self.piece_manager.select_piece_random(conn.peer_pieces)

        if new_idx is not None:
            blocks = self.piece_manager.start_piece(new_idx)
            self._peer_piece[peer_key] = new_idx
            sent = await self._send_block_requests(conn, peer_key, blocks, capacity)
            capacity -= sent
            if capacity <= 0:
                return

        # Step 3: Endgame — find an IN_PROGRESS piece with timed-out blocks
        assigned_pieces = set(self._peer_piece.values())
        fallback_idx = self.piece_manager.find_in_progress_piece(
            conn.peer_pieces, exclude=assigned_pieces
        )
        if fallback_idx is not None:
            self._peer_piece[peer_key] = fallback_idx
            blocks = self.piece_manager.pieces[fallback_idx].get_requestable_blocks()
            await self._send_block_requests(conn, peer_key, blocks, capacity)

    async def _send_block_requests(self, conn: PeerConnection, peer_key: str,
                                    blocks: list, max_to_send: int) -> int:
        """Send block requests to a peer, up to max_to_send.

        Returns the number of requests successfully sent.
        """
        sent = 0
        for block in blocks:
            if sent >= max_to_send:
                break
            try:
                await conn.send_request(block.piece_index, block.offset, block.length)
                block.mark_requested(peer_key)
                sent += 1
            except PeerConnectionError:
                break
        return sent

    def _is_seeding(self) -> bool:
        """True iff the download is complete and we are serving the swarm.

        Triggers the seed-mode branch of _tit_for_tat_unchoke, which ranks
        peers by how fast we are uploading to them (bytes_sent_in_window)
        instead of receiving from them — the leech metric is permanently
        zero post-completion.
        """
        return (
            self.piece_manager.is_complete
            and self.state in (DownloadState.COMPLETED, DownloadState.SEEDING)
        )

    def _maybe_enter_seeding(self):
        """Promote a freshly-completed download to the visible SEEDING state.

        Runs once per choke tick. The completion popup and history write key
        off the "Completed" state, which is shown for up to one choke
        interval first; this then flips the label to "Seeding" so the GUI
        reflects that we are serving the swarm. Idempotent.
        """
        if self.state == DownloadState.COMPLETED and self.piece_manager.is_complete:
            self.state = DownloadState.SEEDING
            self._log(f"Now seeding {self.torrent.name} — serving connected peers")

    async def _choke_loop(self):
        """Periodically run choke/unchoke algorithm.

        Runs while we're actively downloading (RUNNING) OR seeding
        (post-completion). In seed mode the algorithm switches metric
        but the cadence stays at CHOKE_INTERVAL.
        """
        while self.state == DownloadState.RUNNING or self._is_seeding():
            await asyncio.sleep(CHOKE_INTERVAL)
            if self.state != DownloadState.RUNNING and not self._is_seeding():
                break

            self._maybe_enter_seeding()

            if self.peer_algorithm == AlgorithmType.TIT_FOR_TAT:
                await self._tit_for_tat_unchoke()
            else:
                await self._round_robin_unchoke()
            self.stats.choke_cycles += 1

    async def _tit_for_tat_unchoke(self):
        """Implement the Tit-for-Tat choke/unchoke algorithm.

        1. Get all interested peers.
        2. Partition into non_snubbed and snubbed (see PeerConnection.is_snubbed).
           A snubbed peer has unchoked us but stopped sending — without this
           split they would keep an unchoke slot forever via their cumulative
           or even windowed contribution.
        3. Sort non_snubbed by sliding-window contribution (bytes received in
           the last TIT_FOR_TAT_WINDOW seconds) — a peer that contributed
           early then went silent does NOT keep a high score forever.
        4. Fill top K from non_snubbed first; only fall back to snubbed peers
           when fewer than K healthy candidates exist.
        5. Optimistic unchoke: pick one random peer not in top K, preferring
           non-snubbed candidates so a freshly-snubbed peer is replaced.
        6. Choke all others.
        """
        interested_peers = [
            (key, conn) for key, conn in self._connections.items()
            if conn.connected and conn.peer_interested
        ]

        if not interested_peers:
            return

        # Seed mode: leech metric (bytes_received_in_window) is permanently
        # zero post-completion, so all peers would tie and the top-K is
        # effectively random. Instead rank by how fast we are uploading
        # to them — prioritize peers that drain our upload bandwidth best
        # so the swarm benefits most from what we serve. Snubbing is not
        # meaningful here: a peer not sending us blocks is the *normal*
        # case (we don't need any).
        if self._is_seeding():
            await self._seed_mode_unchoke(interested_peers)
            return

        # Partition: snubbed peers shouldn't compete on contribution metric
        # with healthy peers — silence isn't contribution.
        non_snubbed = []
        snubbed = []
        for key, conn in interested_peers:
            if conn.is_snubbed():
                snubbed.append((key, conn))
            else:
                non_snubbed.append((key, conn))

        # Log newly-snubbed peers once per snub episode (not per cycle).
        current_snubbed_keys = {key for key, _ in snubbed}
        for key in current_snubbed_keys - self._previously_snubbed:
            logger.info(f"Peer {key} snubbed (unchoked us but no PIECE in >60s); demoting")
        # Drop keys that recovered so a future snub gets logged again.
        self._previously_snubbed = current_snubbed_keys

        # Sort non_snubbed by sliding-window contribution. Cumulative
        # bytes_downloaded would let an early contributor that has since
        # stopped keep its unchoke slot indefinitely; the window punishes
        # silence.
        non_snubbed.sort(
            key=lambda x: x[1].bytes_received_in_window(TIT_FOR_TAT_WINDOW),
            reverse=True
        )

        # Fill top K from healthy peers first; only dip into snubbed when
        # we don't have enough non_snubbed candidates.
        to_unchoke: Set[str] = set()
        for key, _ in non_snubbed[:MAX_UNCHOKED_PEERS]:
            to_unchoke.add(key)
        if len(to_unchoke) < MAX_UNCHOKED_PEERS:
            for key, _ in snubbed[:MAX_UNCHOKED_PEERS - len(to_unchoke)]:
                to_unchoke.add(key)

        # Optimistic unchoke: pick a random *healthy* peer outside the top K.
        # The purpose of optimistic unchoke is discovering new contributors;
        # promoting a snubbed peer here would defeat the demotion above, so
        # we never optimistically unchoke a snubbed peer when a non-snubbed
        # candidate exists. If non_snubbed is already fully in to_unchoke,
        # we skip optimistic unchoke entirely this cycle.
        non_snubbed_remaining = [
            (key, conn) for key, conn in non_snubbed if key not in to_unchoke
        ]
        if non_snubbed_remaining:
            import random
            opt_key, _ = random.choice(non_snubbed_remaining)
            to_unchoke.add(opt_key)

        # Apply choke/unchoke decisions
        for key, conn in self._connections.items():
            if not conn.connected:
                continue
            if key in to_unchoke and conn.am_choking:
                await conn.send_unchoke()
                self.stats.unchoke_count += 1
            elif key not in to_unchoke and not conn.am_choking:
                await conn.send_choke()
                self.stats.choke_count += 1

    async def _seed_mode_unchoke(self, interested_peers):
        """Seeding-mode tit-for-tat: sort by upload window, not download.

        Standard BitTorrent seeding policy (Cohen 2003; libtorrent;
        mainline): once we've finished downloading, the right question
        flips from "who gives me the most?" to "who can I give to the
        fastest?". Prioritize peers with good downstream bandwidth so
        our upload contributes most to the swarm.
        """
        # Sort by bytes_sent_in_window descending — top peers are the
        # ones currently draining our upload fastest.
        interested_peers.sort(
            key=lambda x: x[1].bytes_sent_in_window(TIT_FOR_TAT_WINDOW),
            reverse=True
        )

        to_unchoke: Set[str] = set()
        for key, _ in interested_peers[:MAX_UNCHOKED_PEERS]:
            to_unchoke.add(key)

        # Optimistic unchoke: random peer outside top-K. Useful in seed
        # mode too — it discovers new peers whose upload-window metric is
        # currently zero just because we haven't started serving them yet.
        remaining = [
            (key, conn) for key, conn in interested_peers if key not in to_unchoke
        ]
        if remaining:
            import random
            opt_key, _ = random.choice(remaining)
            to_unchoke.add(opt_key)

        for key, conn in self._connections.items():
            if not conn.connected:
                continue
            if key in to_unchoke and conn.am_choking:
                await conn.send_unchoke()
                self.stats.unchoke_count += 1
            elif key not in to_unchoke and not conn.am_choking:
                await conn.send_choke()
                self.stats.choke_count += 1

    async def _round_robin_unchoke(self):
        """Baseline: distribute unchokes in round-robin fashion."""
        connected = [
            (key, conn) for key, conn in self._connections.items()
            if conn.connected and conn.peer_interested
        ]

        if not connected:
            return

        # Unchoke the next peer in rotation
        for key, conn in self._connections.items():
            if conn.connected and not conn.am_choking:
                await conn.send_choke()
                self.stats.choke_count += 1

        if connected:
            self._rr_index = self._rr_index % len(connected)
            key, conn = connected[self._rr_index]
            await conn.send_unchoke()
            self.stats.unchoke_count += 1
            self._rr_index = (self._rr_index + 1) % len(connected)

    async def _keep_alive_loop(self):
        """Send keep-alive messages periodically.

        Runs while downloading (RUNNING) or seeding, so connections to peers
        we serve don't time out after the download finishes.
        """
        while self.state == DownloadState.RUNNING or self._is_seeding():
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)
            for conn in list(self._connections.values()):
                if conn.connected:
                    try:
                        await conn.send_keep_alive()
                    except PeerConnectionError:
                        pass

    async def _broadcast_have(self, piece_index: int):
        """Announce a completed piece to all connected peers.

        Each send is independent — we don't wait for all to complete sequentially.
        """
        tasks = []
        for conn in list(self._connections.values()):
            if conn.connected:
                tasks.append(self._safe_send_have(conn, piece_index))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send_have(self, conn: PeerConnection, piece_index: int):
        """Send a HAVE message, suppressing errors."""
        try:
            await conn.send_have(piece_index)
        except Exception:
            pass

    def _write_piece_sync(self, piece_index: int):
        """Write a verified piece to the output file(s) — synchronous, for use in executor.

        Handles both single-file and multi-file torrents correctly by
        tracking a cursor through the piece data and writing the right
        slice to each file at the right offset.
        """
        data = self.piece_manager.get_piece_data(piece_index)
        if data is None:
            return

        file_offsets = self.torrent.get_file_offset(piece_index)
        data_cursor = 0

        for file_path, offset_in_file, length in file_offsets:
            full_path = os.path.join(self.download_dir, file_path)
            os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else '.', exist_ok=True)

            # Pre-allocate file if it doesn't exist yet
            if not os.path.exists(full_path):
                file_size = next(
                    f.size for f in self.torrent.files if f.path == file_path
                )
                with open(full_path, 'wb') as f:
                    f.truncate(file_size)

            # Write the correct slice of piece data at the correct file offset
            with open(full_path, 'r+b') as f:
                f.seek(offset_in_file)
                f.write(data[data_cursor:data_cursor + length])

            data_cursor += length

    async def _write_piece(self, piece_index: int):
        """Write a verified piece to disk (async wrapper)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._write_piece_sync, piece_index)

    def _read_block_sync(self, piece_index: int, begin: int,
                         length: int) -> Optional[bytes]:
        """Read a block of a completed piece for serving — synchronous.

        Completed pieces keep their bytes in memory both after a live finish
        and after a restore (_load_state replays disk bytes into the piece),
        so the in-memory copy is always the source of truth here.
        """
        data = self.piece_manager.get_piece_data(piece_index)
        if data is None:
            return None
        block = data[begin:begin + length]
        if len(block) != length:
            return None
        return bytes(block)

    async def _complete_download(self):
        """Handle download completion."""
        if self._completion_handled:
            return
        self._completion_handled = True

        self.state = DownloadState.COMPLETED
        if self.stats.end_time is None:
            self.stats.end_time = time.time()

        download_path = os.path.join(self.download_dir, self.torrent.name)
        self._log(
            f"Download complete! {self.torrent.name} "
            f"saved to {download_path} "
            f"in {self.stats.elapsed_time:.1f}s "
            f"(avg {self.stats.average_speed / 1024:.1f} KB/s)"
        )

        if self._tracker:
            try:
                await self._tracker.completed()
            except Exception:
                pass

        if self._on_complete:
            self._on_complete(self)

    async def _on_tracker_response(self, response: TrackerResponse):
        """Handle periodic tracker response with new peers."""
        for peer in response.peers:
            if peer not in self._known_peers:
                self._known_peers.add(peer)

        self.stats.total_peers_seen = len(self._known_peers)
        await self._connect_to_peers()

    def _update_speed(self):
        """Update download speed calculation."""
        now = time.time()
        self._speed_samples.append((now, self.stats.bytes_downloaded))

        # Keep last 10 seconds of samples
        self._speed_samples = [
            (t, b) for t, b in self._speed_samples if now - t < 10
        ]

        if len(self._speed_samples) >= 2:
            first_time, first_bytes = self._speed_samples[0]
            duration = now - first_time
            if duration > 0:
                self.stats.download_speed = (
                    (self.stats.bytes_downloaded - first_bytes) / duration
                )
                self.stats.peak_speed = max(
                    self.stats.peak_speed, self.stats.download_speed
                )

        self.stats.connected_peers = self.connected_peers

    async def pause(self):
        """Pause the download."""
        if self.state != DownloadState.RUNNING:
            return

        self.state = DownloadState.PAUSED
        logger.info(f"Pausing download: {self.torrent.name}")

        # Cancel tasks
        for task in [self._choke_task, self._keep_alive_task]:
            if task:
                task.cancel()

        # Disconnect peers
        for conn in list(self._connections.values()):
            await conn.disconnect()

        self._save_state()

    async def resume(self):
        """Resume a paused download."""
        if self.state != DownloadState.PAUSED:
            return

        self.state = DownloadState.RUNNING
        logger.info(f"Resuming download: {self.torrent.name}")

        self._main_task = asyncio.create_task(self._download_loop())

    async def cancel(self):
        """Cancel the download."""
        self.state = DownloadState.CANCELLED
        self.stats.end_time = time.time()
        logger.info(f"Cancelling download: {self.torrent.name}")

        # Cancel all tasks
        for task in [self._main_task, self._choke_task, self._keep_alive_task]:
            if task and not task.done():
                task.cancel()

        # Disconnect all peers
        for conn in list(self._connections.values()):
            await conn.disconnect()

        if self._tracker:
            await self._tracker.stop()

        self._save_state()

    def _save_state(self):
        """Save current download state to a JSON file.

        Also writes a sidecar `{id}.torrent` next to the JSON so the download
        can be reconstructed without the original .torrent file being available.
        """
        state_data = {
            "torrentId": self.id,
            "info_hash": self.torrent.info_hash_hex(),
            "file_name": self.torrent.name,
            "file_size": self.torrent.total_size,
            "piece_length": self.torrent.piece_length,
            "piece_status": self.piece_manager.get_status_list(),
            "downloaded": self.stats.bytes_downloaded,
            "uploaded": self.stats.bytes_uploaded,
            "left": self.piece_manager.bytes_remaining,
            "last_peers": [
                {
                    "ip": conn.ip,
                    "port": conn.port,
                    "status": "connected" if conn.connected else "disconnected"
                }
                for conn in self._connections.values()
            ],
            "state": self.state.value,
            "start_time": self.stats.start_time,
            "stop_time": self.stats.end_time,
            "last_saved": time.time(),
            "download_dir": self.download_dir,
            "piece_algorithm": self.piece_algorithm.value,
            "peer_algorithm": self.peer_algorithm.value,
        }

        os.makedirs(self.state_dir, exist_ok=True)
        state_path = os.path.join(self.state_dir, f"{self.id}.json")
        with open(state_path, 'w') as f:
            json.dump(state_data, f, indent=2)

        # Sidecar .torrent for restoration (re-encode the parsed metadata
        # so the bytes are canonical and the info_hash round-trips).
        torrent_path = os.path.join(self.state_dir, f"{self.id}.torrent")
        try:
            with open(torrent_path, 'wb') as f:
                f.write(bencode.encode(self.torrent._metadata))
        except Exception as e:
            logger.warning(f"[{self.id}] failed to write sidecar .torrent: {e}")

    @classmethod
    def from_state_file(cls, state_file, state_dir_override: Optional[str] = None,
                        download_dir_override: Optional[str] = None) -> Optional["Download"]:
        """Reconstruct a paused Download from a saved JSON state file.

        Reads the sidecar `{id}.torrent` next to the JSON to rebuild the
        TorrentMetadata, then re-reads each COMPLETED piece's bytes from
        disk and re-verifies its SHA-1 before marking the piece COMPLETED.
        Pieces that fail re-verification (or whose bytes are unreadable)
        fall back to MISSING.

        Returns None on any unrecoverable error (missing/corrupt JSON,
        missing sidecar, info_hash mismatch). Never raises.
        """
        state_path = Path(state_file)
        try:
            with open(state_path, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logger.warning(f"Cannot read state file {state_path}: {e}")
            return None

        torrent_path = state_path.with_suffix('.torrent')
        if not torrent_path.exists():
            logger.warning(f"Sidecar torrent missing for state {state_path}")
            return None

        try:
            torrent = TorrentMetadata(torrent_path=str(torrent_path))
        except Exception as e:
            logger.warning(f"Cannot parse sidecar torrent {torrent_path}: {e}")
            return None

        expected_hash = data.get("info_hash")
        if expected_hash and expected_hash != torrent.info_hash_hex():
            logger.warning(
                f"info_hash mismatch in {state_path}: "
                f"saved={expected_hash} sidecar={torrent.info_hash_hex()}"
            )
            return None

        download_dir = download_dir_override or data.get("download_dir")
        state_dir = state_dir_override or str(state_path.parent)
        if not download_dir:
            logger.warning(f"No download_dir in {state_path} and no override given")
            return None

        try:
            piece_algo = AlgorithmType(data.get("piece_algorithm", "rarest_first"))
        except ValueError:
            piece_algo = AlgorithmType.RAREST_FIRST
        try:
            peer_algo = AlgorithmType(data.get("peer_algorithm", "tit_for_tat"))
        except ValueError:
            peer_algo = AlgorithmType.TIT_FOR_TAT

        dl = cls(
            torrent=torrent,
            download_dir=download_dir,
            state_dir=state_dir,
            piece_algorithm=piece_algo,
            peer_algorithm=peer_algo,
        )

        # Preserve the original id (don't generate a new one) so the JSON
        # file keeps the same name on the next _save_state.
        saved_id = data.get("torrentId")
        if saved_id:
            dl.id = saved_id

        # Restore stats
        dl.stats.bytes_downloaded = data.get("downloaded", 0)
        dl.stats.bytes_uploaded = data.get("uploaded", 0)
        dl.stats.start_time = data.get("start_time")
        dl.stats.end_time = data.get("stop_time")

        # Walk the piece_status array; re-verify each COMPLETED piece from disk.
        statuses = data.get("piece_status", [])
        for idx, status in enumerate(statuses):
            if status != PieceStatus.COMPLETED.value:
                continue
            if idx >= len(dl.piece_manager.pieces):
                continue
            piece = dl.piece_manager.pieces[idx]
            try:
                buf = bytearray()
                for file_path, offset_in_file, length in torrent.get_file_offset(idx):
                    full_path = os.path.join(download_dir, file_path)
                    with open(full_path, 'rb') as fh:
                        fh.seek(offset_in_file)
                        buf.extend(fh.read(length))
                if len(buf) != piece.length:
                    raise ValueError(
                        f"piece {idx} short read: got {len(buf)} expected {piece.length}"
                    )
                piece._data = buf
                if piece.verify_hash():
                    piece.status = PieceStatus.COMPLETED
                    for blk in piece.blocks:
                        blk.received = True
                else:
                    logger.warning(
                        f"[{dl.id}] piece {idx} bytes on disk failed re-verify; marking MISSING"
                    )
                    piece.reset()
            except (FileNotFoundError, OSError, ValueError) as e:
                logger.warning(
                    f"[{dl.id}] cannot restore piece {idx} from disk: {e}; marking MISSING"
                )
                piece.reset()

        # State policy: force PAUSED unless the saved state was COMPLETED.
        saved_state = data.get("state")
        if saved_state == DownloadState.COMPLETED.value:
            dl.state = DownloadState.COMPLETED
        else:
            dl.state = DownloadState.PAUSED

        return dl

    def get_status(self) -> dict:
        """Get current download status as a dictionary."""
        return {
            "id": self.id,
            "name": self.torrent.name,
            "size": self.torrent.total_size,
            "progress": round(self.progress * 100, 2),
            "download_speed": round(self.stats.download_speed, 2),
            "upload_speed": round(self.stats.upload_speed, 2),
            "connected_peers": self.connected_peers,
            "state": self.state.value,
            "downloaded": self.stats.bytes_downloaded,
            "uploaded": self.stats.bytes_uploaded,
            "elapsed_time": round(self.stats.elapsed_time, 1),
            "piece_algorithm": self.piece_algorithm.value,
            "peer_algorithm": self.peer_algorithm.value,
            "download_path": os.path.join(self.download_dir, self.torrent.name),
        }


class DownloadManager:
    """Manages multiple downloads.

    Central coordinator for all active and historical downloads.
    """

    def __init__(self, download_dir: str = "data/downloads",
                 state_dir: str = "data/state"):
        self.download_dir = download_dir
        self.state_dir = state_dir
        self.downloads: Dict[str, Download] = {}

        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(state_dir, exist_ok=True)

    async def add_torrent(self, torrent: TorrentMetadata,
                          piece_algorithm: AlgorithmType = AlgorithmType.RAREST_FIRST,
                          peer_algorithm: AlgorithmType = AlgorithmType.TIT_FOR_TAT,
                          download_dir: Optional[str] = None
                          ) -> Download:
        """Add a new torrent download.

        Args:
            torrent: Parsed torrent metadata.
            piece_algorithm: Piece selection algorithm to use.
            peer_algorithm: Peer selection algorithm to use.
            download_dir: Override download directory (uses manager default if None).

        Returns:
            The created Download object.
        """
        target_dir = download_dir or self.download_dir
        os.makedirs(target_dir, exist_ok=True)
        download = Download(
            torrent=torrent,
            download_dir=target_dir,
            state_dir=self.state_dir,
            piece_algorithm=piece_algorithm,
            peer_algorithm=peer_algorithm
        )
        self.downloads[download.id] = download
        return download

    async def start_download(self, download_id: str):
        """Start a specific download."""
        if download_id in self.downloads:
            await self.downloads[download_id].start()

    async def pause_download(self, download_id: str):
        """Pause a specific download."""
        if download_id in self.downloads:
            await self.downloads[download_id].pause()

    async def resume_download(self, download_id: str):
        """Resume a specific download."""
        if download_id in self.downloads:
            await self.downloads[download_id].resume()

    async def cancel_download(self, download_id: str):
        """Cancel a specific download."""
        if download_id in self.downloads:
            await self.downloads[download_id].cancel()

    def get_all_status(self) -> List[dict]:
        """Get status of all downloads."""
        return [d.get_status() for d in self.downloads.values()]

    def get_download_status(self, download_id: str) -> Optional[dict]:
        """Get status of a specific download."""
        if download_id in self.downloads:
            return self.downloads[download_id].get_status()
        return None

    def get_download(self, download_id: str) -> Optional[Download]:
        """Get a download by ID."""
        return self.downloads.get(download_id)

    def restore_state(self) -> int:
        """Scan state_dir for `*.json` and reconstruct paused Downloads.

        Each restored download lands in `self.downloads` in PAUSED state
        (or COMPLETED if it finished before the crash). The user explicitly
        resumes via the API; we do not auto-start the network loop.

        Returns the number of downloads successfully restored.
        """
        state_path = Path(self.state_dir)
        if not state_path.exists():
            return 0
        restored = 0
        for state_file in sorted(state_path.glob("*.json")):
            dl = Download.from_state_file(
                state_file,
                state_dir_override=self.state_dir,
                download_dir_override=self.download_dir,
            )
            if dl is None:
                continue
            if dl.id in self.downloads:
                logger.warning(f"Duplicate download id {dl.id} during restore; skipping")
                continue
            self.downloads[dl.id] = dl
            restored += 1
        return restored
