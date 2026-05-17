"""
A controlled localhost swarm: a mock HTTP tracker and one or more mock
BitTorrent peers, both speaking just enough of BEP-3 to exercise the
engine end-to-end without touching the wider internet.

Used by:
  * run_comparison.py — the A/B experiment (rarest-first vs random).
  * tests/test_e2e_peer.py — the end-to-end peer-wire-protocol test.

The implementations are intentionally minimal: we do NOT cover the
entire spec, only the messages the engine exercises during a small
download. Anything outside that (extensions, KEEP_ALIVE behavior under
load, etc.) is ignored.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from aiohttp import web

from .. import bencode

logger = logging.getLogger(__name__)


# ── Mock peer ─────────────────────────────────────────────────────────────

PROTOCOL_STRING = b"BitTorrent protocol"
HANDSHAKE_LEN = 1 + len(PROTOCOL_STRING) + 8 + 20 + 20  # 68 bytes


class MsgId:
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8


def _bitfield_bytes(piece_set: Sequence[int], num_pieces: int) -> bytes:
    """Encode a list of piece indices as a BEP-3 bitfield."""
    num_bytes = (num_pieces + 7) // 8
    bf = bytearray(num_bytes)
    have = set(piece_set)
    for i in range(num_pieces):
        if i in have:
            bf[i // 8] |= 1 << (7 - (i % 8))
    return bytes(bf)


@dataclass
class MockPeer:
    """A single mock BitTorrent peer running on an asyncio TCP server.

    Owns a fixed subset of pieces from a known payload file. Accepts
    incoming engine connections, serves PIECE messages in response to
    REQUESTs. Always unchokes immediately after the leecher sends
    INTERESTED — we are not modeling tit-for-tat on this side.
    """

    name: str
    info_hash: bytes
    payload_path: str
    piece_length: int
    num_pieces: int
    total_size: int
    owned_pieces: List[int]
    host: str = "127.0.0.1"
    port: int = 0  # 0 → kernel picks
    peer_id: bytes = field(
        default_factory=lambda: b"-MK0001-" + b"\x00" * 12
    )

    # Populated after start()
    server: Optional[asyncio.AbstractServer] = None
    upload_bytes: int = 0
    connections_handled: int = 0

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._handle, host=self.host, port=self.port
        )
        # Resolve the real port if we asked for 0
        sock = self.server.sockets[0]
        self.port = sock.getsockname()[1]
        logger.info("MockPeer %s listening on %s:%d (owns %d pieces)",
                    self.name, self.host, self.port, len(self.owned_pieces))

    async def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            try:
                await self.server.wait_closed()
            except Exception:
                pass
            self.server = None

    async def _handle(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        self.connections_handled += 1
        peer_addr = writer.get_extra_info("peername")
        logger.debug("MockPeer %s: connection from %s", self.name, peer_addr)
        try:
            # Read incoming handshake (68 bytes)
            data = await asyncio.wait_for(
                reader.readexactly(HANDSHAKE_LEN), timeout=10
            )
            if data[0] != len(PROTOCOL_STRING):
                logger.warning("MockPeer %s: bad pstrlen", self.name)
                return
            if data[1:1 + len(PROTOCOL_STRING)] != PROTOCOL_STRING:
                logger.warning("MockPeer %s: bad pstr", self.name)
                return
            info_hash_offset = 1 + len(PROTOCOL_STRING) + 8
            received_ih = data[info_hash_offset:info_hash_offset + 20]
            if received_ih != self.info_hash:
                logger.warning("MockPeer %s: info_hash mismatch", self.name)
                return

            # Send our handshake back
            writer.write(
                bytes([len(PROTOCOL_STRING)])
                + PROTOCOL_STRING
                + b"\x00" * 8
                + self.info_hash
                + self.peer_id
            )
            await writer.drain()

            # Send our BITFIELD immediately so the leecher can decide
            # whether to be interested.
            bf = _bitfield_bytes(self.owned_pieces, self.num_pieces)
            await self._send_message(writer, MsgId.BITFIELD, bf)

            # Conversation loop: read length-prefixed messages.
            unchoked_them = False
            with open(self.payload_path, "rb") as payload_fp:
                while not reader.at_eof():
                    try:
                        length_bytes = await asyncio.wait_for(
                            reader.readexactly(4), timeout=60
                        )
                    except asyncio.IncompleteReadError:
                        break
                    except asyncio.TimeoutError:
                        break
                    length = struct.unpack("!I", length_bytes)[0]
                    if length == 0:
                        # keep-alive
                        continue
                    if length > 2 * 1024 * 1024:
                        logger.warning("MockPeer %s: oversize length %d",
                                       self.name, length)
                        break
                    try:
                        payload = await asyncio.wait_for(
                            reader.readexactly(length), timeout=60
                        )
                    except asyncio.IncompleteReadError:
                        break
                    msg_id = payload[0]
                    body = payload[1:]

                    if msg_id == MsgId.INTERESTED and not unchoked_them:
                        await self._send_message(writer, MsgId.UNCHOKE)
                        unchoked_them = True

                    elif msg_id == MsgId.NOT_INTERESTED:
                        # Ignored; we don't care.
                        pass

                    elif msg_id == MsgId.REQUEST:
                        if len(body) != 12:
                            continue
                        piece_idx, begin, block_len = struct.unpack("!III", body)
                        if piece_idx not in self.owned_pieces:
                            # The engine should never ask for what our
                            # bitfield said we don't have. Stay silent.
                            continue
                        if block_len > 2 * 1024 * 1024:
                            continue
                        await self._serve_block(
                            writer, payload_fp, piece_idx, begin, block_len
                        )

                    elif msg_id == MsgId.HAVE:
                        # Leecher announcing they got a piece — ignore.
                        pass

                    elif msg_id == MsgId.BITFIELD:
                        # Their bitfield (likely zero) — ignore.
                        pass

                    elif msg_id == MsgId.CANCEL:
                        # We don't track requests; ignore.
                        pass

                    elif msg_id in (MsgId.CHOKE, MsgId.UNCHOKE):
                        # We are a one-sided seeder; we don't request, so
                        # their choke/unchoke is irrelevant.
                        pass

                    else:
                        logger.debug("MockPeer %s: unknown msg_id %d",
                                     self.name, msg_id)

        except asyncio.TimeoutError:
            logger.debug("MockPeer %s: handshake timeout", self.name)
        except asyncio.IncompleteReadError:
            logger.debug("MockPeer %s: client disconnected mid-handshake",
                         self.name)
        except Exception as e:
            logger.warning("MockPeer %s: unexpected error: %s", self.name, e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _serve_block(self, writer: asyncio.StreamWriter,
                           payload_fp, piece_idx: int, begin: int,
                           block_len: int) -> None:
        # Compute the actual length of the requested piece (last piece may
        # be short) and clamp the request to it.
        if piece_idx == self.num_pieces - 1:
            tail = self.total_size % self.piece_length
            piece_actual_len = tail if tail != 0 else self.piece_length
        else:
            piece_actual_len = self.piece_length
        if begin >= piece_actual_len:
            return
        max_len = piece_actual_len - begin
        if block_len > max_len:
            block_len = max_len

        offset_in_file = piece_idx * self.piece_length + begin
        payload_fp.seek(offset_in_file)
        block_data = payload_fp.read(block_len)
        if not block_data:
            return

        body = struct.pack("!II", piece_idx, begin) + block_data
        await self._send_message(writer, MsgId.PIECE, body)
        self.upload_bytes += len(block_data)

    @staticmethod
    async def _send_message(writer: asyncio.StreamWriter,
                            msg_id: int, body: bytes = b"") -> None:
        full = bytes([msg_id]) + body
        writer.write(struct.pack("!I", len(full)) + full)
        await writer.drain()


# ── Mock tracker ──────────────────────────────────────────────────────────

class MockTracker:
    """A minimal HTTP tracker: returns a bencoded compact peer list.

    Does not enforce info_hash, peer_id, port, or stat fields — we only
    care about handing back the swarm. Always returns the full list,
    every time. Listens on a random local port until ``stop()`` is
    awaited.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0,
                 interval: int = 1800) -> None:
        self.host = host
        self.port = port
        self.interval = interval
        self._peers: List[tuple[str, int]] = []
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self.requests_handled = 0

    def set_peers(self, peers: List[tuple[str, int]]) -> None:
        self._peers = list(peers)

    @property
    def announce_url(self) -> str:
        return f"http://{self.host}:{self.port}/announce"

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/announce", self._announce)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host=self.host, port=self.port)
        await self._site.start()
        # Resolve actual port if 0 was passed
        sockets = list(self._site._server.sockets) if self._site._server else []
        if sockets:
            self.port = sockets[0].getsockname()[1]
        logger.info("MockTracker listening on %s", self.announce_url)

    async def stop(self) -> None:
        if self._site is not None:
            await self._site.stop()
            self._site = None
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _announce(self, request: web.Request) -> web.Response:
        self.requests_handled += 1
        compact = bytearray()
        for ip, port in self._peers:
            parts = ip.split(".")
            if len(parts) != 4:
                continue
            compact.extend(bytes(int(p) for p in parts))
            compact.extend(struct.pack("!H", port))
        body = bencode.encode({
            b"interval": self.interval,
            b"complete": len(self._peers),
            b"incomplete": 0,
            b"peers": bytes(compact),
        })
        return web.Response(body=body, content_type="text/plain")


# ── Swarm aggregator ──────────────────────────────────────────────────────

@dataclass
class MockSwarm:
    """A self-contained tracker + N peers wired together."""

    tracker: MockTracker
    peers: List[MockPeer]

    async def start(self) -> None:
        await self.tracker.start()
        for p in self.peers:
            await p.start()
        self.tracker.set_peers([(p.host, p.port) for p in self.peers])

    async def stop(self) -> None:
        for p in self.peers:
            await p.stop()
        await self.tracker.stop()

    def total_upload_bytes(self) -> Dict[str, int]:
        return {p.name: p.upload_bytes for p in self.peers}
