"""
Download manager module.

The central brain of the download process. Manages peer connections,
implements choke/unchoke (Tit-for-Tat) and piece selection algorithms,
and coordinates the overall download flow.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

from .peer_connection import PeerConnection, PeerMessage, MessageType, PeerConnectionError
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


class DownloadState(Enum):
    """States of a download."""
    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
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

        # Round-robin state
        self._rr_index = 0

        # Event callbacks
        self._on_progress = None
        self._on_complete = None
        self._on_state_change = None

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

        logger.info(f"Starting download: {self.torrent.name} ({self.id})")

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
            response = await self._tracker.announce(event='started',
                                                    left=self.torrent.total_size)
            for peer in response.peers:
                self._known_peers.add(peer)
            self.stats.total_peers_seen = len(self._known_peers)

            # Start choke/unchoke timer
            self._choke_task = asyncio.create_task(self._choke_loop())
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())

            # Start periodic tracker announces
            await self._tracker.start_periodic_announce(
                callback=self._on_tracker_response
            )

            # Connect to peers and download
            await self._connect_to_peers()

            # Main piece request loop
            while not self.piece_manager.is_complete and self.state == DownloadState.RUNNING:
                await self._request_pieces()
                await asyncio.sleep(0.1)

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
            pass
        except Exception as e:
            logger.error(f"Download error: {e}")
            self.state = DownloadState.ERROR
        finally:
            self._save_state()

    async def _connect_to_peers(self):
        """Connect to known peers."""
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

            logger.info(f"Connected to peer {peer_key}")
        except PeerConnectionError as e:
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
            pass  # Can now request pieces from this peer

        elif message.type == MessageType.PIECE:
            piece_idx = message.piece_index
            offset = message.block_offset
            data = message.block_data

            if data is not None:
                is_complete = self.piece_manager.submit_block(piece_idx, offset, data)
                self.stats.bytes_downloaded += len(data)

                if is_complete:
                    if self.piece_manager.verify_piece(piece_idx):
                        self.security.report_successful_piece(peer_key, piece_idx)
                        await self._write_piece(piece_idx)
                        # Announce to all peers
                        await self._broadcast_have(piece_idx)
                        if self._on_progress:
                            self._on_progress(self)
                    else:
                        self.security.report_hash_failure(peer_key, piece_idx)
                        if self.security.is_peer_banned(peer_key):
                            await conn.disconnect()

    def _peer_has_needed_pieces(self, conn: PeerConnection) -> bool:
        """Check if a peer has pieces we still need."""
        for i in range(self.torrent.num_pieces):
            if not self.piece_manager.has_piece(i) and conn.has_piece(i):
                return True
        return False

    async def _request_pieces(self):
        """Request pieces from unchoked peers."""
        for peer_key, conn in list(self._connections.items()):
            if not conn.connected or conn.peer_choking or not conn.am_interested:
                continue

            # Select piece based on algorithm
            if self.piece_algorithm == AlgorithmType.RAREST_FIRST:
                piece_idx = self.piece_manager.select_piece_rarest_first(conn.peer_pieces)
            else:
                piece_idx = self.piece_manager.select_piece_random(conn.peer_pieces)

            if piece_idx is None:
                continue

            blocks = self.piece_manager.start_piece(piece_idx)
            for block in blocks:
                try:
                    await conn.send_request(
                        block.piece_index, block.offset, block.length
                    )
                except PeerConnectionError:
                    break

    async def _choke_loop(self):
        """Periodically run choke/unchoke algorithm."""
        while self.state == DownloadState.RUNNING:
            await asyncio.sleep(CHOKE_INTERVAL)
            if self.state != DownloadState.RUNNING:
                break

            if self.peer_algorithm == AlgorithmType.TIT_FOR_TAT:
                await self._tit_for_tat_unchoke()
            else:
                await self._round_robin_unchoke()

    async def _tit_for_tat_unchoke(self):
        """Implement the Tit-for-Tat choke/unchoke algorithm.

        1. Get all interested peers
        2. Sort by how much they uploaded to us
        3. Unchoke top K peers
        4. Optimistic unchoke: randomly unchoke one additional peer
        5. Choke all others
        """
        interested_peers = [
            (key, conn) for key, conn in self._connections.items()
            if conn.connected and conn.peer_interested
        ]

        if not interested_peers:
            return

        # Sort by download rate from this peer (how much they contribute to us)
        interested_peers.sort(key=lambda x: x[1].bytes_downloaded, reverse=True)

        # Select top K
        to_unchoke = set()
        for i, (key, conn) in enumerate(interested_peers):
            if i < MAX_UNCHOKED_PEERS:
                to_unchoke.add(key)

        # Optimistic unchoke: pick one random peer not in top K
        remaining = [
            (key, conn) for key, conn in interested_peers
            if key not in to_unchoke
        ]
        if remaining:
            import random
            opt_key, _ = random.choice(remaining)
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
        """Send keep-alive messages periodically."""
        while self.state == DownloadState.RUNNING:
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)
            for conn in list(self._connections.values()):
                if conn.connected:
                    try:
                        await conn.send_keep_alive()
                    except PeerConnectionError:
                        pass

    async def _broadcast_have(self, piece_index: int):
        """Announce a completed piece to all connected peers."""
        for conn in list(self._connections.values()):
            if conn.connected:
                try:
                    await conn.send_have(piece_index)
                except PeerConnectionError:
                    pass

    async def _write_piece(self, piece_index: int):
        """Write a verified piece to the output file."""
        data = self.piece_manager.get_piece_data(piece_index)
        if data is None:
            return

        file_offsets = self.torrent.get_file_offset(piece_index)
        for file_path, offset, length in file_offsets:
            full_path = os.path.join(self.download_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Calculate which part of piece data to write
            piece_start = offset - (self.torrent.get_file_offset(piece_index)[0][1]
                                    if file_offsets else 0)

            mode = 'r+b' if os.path.exists(full_path) else 'wb'
            if mode == 'wb':
                # Create file with correct size
                file_size = next(
                    f.size for f in self.torrent.files if f.path == file_path
                )
                with open(full_path, 'wb') as f:
                    f.seek(file_size - 1)
                    f.write(b'\x00')

            with open(full_path, 'r+b') as f:
                f.seek(offset)
                # Write the relevant portion of piece data
                data_offset = sum(
                    length for fp, off, length in file_offsets
                    if fp == file_path and off < offset
                )
                f.write(data[data_offset:data_offset + length])

    async def _complete_download(self):
        """Handle download completion."""
        self.state = DownloadState.COMPLETED
        self.stats.end_time = time.time()

        logger.info(
            f"Download complete: {self.torrent.name} "
            f"({self.stats.elapsed_time:.1f}s)"
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
        """Save current download state to a JSON file."""
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
        }

        os.makedirs(self.state_dir, exist_ok=True)
        state_path = os.path.join(self.state_dir, f"{self.id}.json")
        with open(state_path, 'w') as f:
            json.dump(state_data, f, indent=2)

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
                          peer_algorithm: AlgorithmType = AlgorithmType.TIT_FOR_TAT
                          ) -> Download:
        """Add a new torrent download.

        Args:
            torrent: Parsed torrent metadata.
            piece_algorithm: Piece selection algorithm to use.
            peer_algorithm: Peer selection algorithm to use.

        Returns:
            The created Download object.
        """
        download = Download(
            torrent=torrent,
            download_dir=self.download_dir,
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
