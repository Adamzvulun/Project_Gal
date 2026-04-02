"""
Piece manager module.

Tracks piece download status, peer frequency counts, and implements
piece selection algorithms (rarest-first and random baseline).
"""

import hashlib
import logging
import random
import threading
import time
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PieceStatus(Enum):
    """Status of a piece."""
    MISSING = "missing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Block:
    """Represents a block within a piece."""

    def __init__(self, piece_index: int, offset: int, length: int):
        self.piece_index = piece_index
        self.offset = offset
        self.length = length
        self.data: Optional[bytes] = None
        self.received = False

    def __repr__(self):
        return f"Block(piece={self.piece_index}, offset={self.offset}, len={self.length})"


class Piece:
    """Represents a piece of the torrent file."""

    BLOCK_SIZE = 16384  # 16 KB

    def __init__(self, index: int, length: int, expected_hash: bytes):
        self.index = index
        self.length = length
        self.expected_hash = expected_hash
        self.status = PieceStatus.MISSING
        self.blocks: List[Block] = []
        self._data = bytearray(length)

        # Create blocks
        offset = 0
        while offset < length:
            block_len = min(self.BLOCK_SIZE, length - offset)
            self.blocks.append(Block(index, offset, block_len))
            offset += block_len

    @property
    def num_blocks(self) -> int:
        return len(self.blocks)

    @property
    def is_complete(self) -> bool:
        return all(b.received for b in self.blocks)

    def submit_block(self, offset: int, data: bytes) -> bool:
        """Submit a received block.

        Args:
            offset: Byte offset within the piece.
            data: Block data.

        Returns:
            True if the piece is now complete.
        """
        for block in self.blocks:
            if block.offset == offset:
                block.data = data
                block.received = True
                self._data[offset:offset + len(data)] = data
                break

        return self.is_complete

    def verify_hash(self) -> bool:
        """Verify the piece data matches the expected SHA-1 hash."""
        actual_hash = hashlib.sha1(bytes(self._data)).digest()
        return actual_hash == self.expected_hash

    @property
    def data(self) -> bytes:
        """Get the complete piece data."""
        return bytes(self._data)

    def get_pending_blocks(self) -> List[Block]:
        """Get blocks that haven't been received yet."""
        return [b for b in self.blocks if not b.received]

    def reset(self):
        """Reset the piece to missing state (e.g., after hash failure)."""
        self.status = PieceStatus.MISSING
        self._data = bytearray(self.length)
        for block in self.blocks:
            block.data = None
            block.received = False


class PieceManager:
    """Manages piece download status and implements piece selection algorithms.

    Tracks which pieces are downloaded, how many peers hold each piece,
    and provides piece selection via rarest-first or random algorithms.
    """

    def __init__(self, num_pieces: int, piece_length: int, total_size: int,
                 piece_hashes: List[bytes]):
        """Initialize the piece manager.

        Args:
            num_pieces: Total number of pieces.
            piece_length: Standard piece length in bytes.
            total_size: Total file size in bytes.
            piece_hashes: List of expected SHA-1 hashes, one per piece.
        """
        self.num_pieces = num_pieces
        self.piece_length = piece_length
        self.total_size = total_size

        # Create piece objects
        self.pieces: List[Piece] = []
        for i in range(num_pieces):
            if i == num_pieces - 1:
                remainder = total_size % piece_length
                length = remainder if remainder != 0 else piece_length
            else:
                length = piece_length
            self.pieces.append(Piece(i, length, piece_hashes[i]))

        # Peer frequency tracking: piece_index -> count of peers that have it
        self._peer_frequency: Dict[int, int] = {i: 0 for i in range(num_pieces)}

        # Track which peers have which pieces
        self._peer_pieces: Dict[str, Set[int]] = {}  # peer_key -> set of piece indices

        # Statistics
        self.rarest_selections: Dict[int, int] = {i: 0 for i in range(num_pieces)}

        # Track when pieces entered IN_PROGRESS state for timeout detection
        self._piece_start_times: Dict[int, float] = {}

        self._lock = threading.Lock()

    @property
    def completed_pieces(self) -> int:
        """Number of completed pieces."""
        return sum(1 for p in self.pieces if p.status == PieceStatus.COMPLETED)

    @property
    def bytes_downloaded(self) -> int:
        """Total bytes of completed pieces."""
        return sum(p.length for p in self.pieces if p.status == PieceStatus.COMPLETED)

    @property
    def bytes_remaining(self) -> int:
        """Total bytes remaining to download."""
        return self.total_size - self.bytes_downloaded

    @property
    def progress(self) -> float:
        """Download progress as a fraction (0.0 to 1.0)."""
        if self.total_size == 0:
            return 1.0
        return self.bytes_downloaded / self.total_size

    @property
    def is_complete(self) -> bool:
        """Check if all pieces are downloaded."""
        return self.completed_pieces == self.num_pieces

    def update_peer_pieces(self, peer_key: str, pieces: List[bool]):
        """Update the frequency table when we learn what pieces a peer has.

        Called when receiving a bitfield message from a peer.

        Args:
            peer_key: Unique identifier for the peer (e.g., "ip:port").
            pieces: List of booleans indicating which pieces the peer has.
        """
        with self._lock:
            # Remove old data for this peer if it existed
            if peer_key in self._peer_pieces:
                for piece_idx in self._peer_pieces[peer_key]:
                    self._peer_frequency[piece_idx] = max(
                        0, self._peer_frequency[piece_idx] - 1
                    )

            # Add new data
            peer_set = set()
            for i, has_piece in enumerate(pieces):
                if has_piece and i < self.num_pieces:
                    peer_set.add(i)
                    self._peer_frequency[i] = self._peer_frequency.get(i, 0) + 1

            self._peer_pieces[peer_key] = peer_set

    def update_peer_have(self, peer_key: str, piece_index: int):
        """Update frequency when a peer announces they have a new piece.

        Called when receiving a HAVE message. O(1) operation.

        Args:
            peer_key: Unique identifier for the peer.
            piece_index: Index of the piece the peer now has.
        """
        with self._lock:
            if peer_key not in self._peer_pieces:
                self._peer_pieces[peer_key] = set()

            if piece_index not in self._peer_pieces[peer_key]:
                self._peer_pieces[peer_key].add(piece_index)
                self._peer_frequency[piece_index] = (
                    self._peer_frequency.get(piece_index, 0) + 1
                )

    def remove_peer(self, peer_key: str):
        """Remove a peer and update frequency counts.

        Args:
            peer_key: Unique identifier for the peer.
        """
        with self._lock:
            if peer_key in self._peer_pieces:
                for piece_idx in self._peer_pieces[peer_key]:
                    self._peer_frequency[piece_idx] = max(
                        0, self._peer_frequency[piece_idx] - 1
                    )
                del self._peer_pieces[peer_key]

    def select_piece_rarest_first(self, peer_pieces: List[bool]) -> Optional[int]:
        """Select a piece using the rarest-first algorithm.

        1. Consider only pieces that are missing AND the peer has
        2. Find the minimum frequency among those pieces
        3. Build a rarest set (all pieces with that frequency)
        4. Choose one at random from the rarest set

        Args:
            peer_pieces: List of booleans indicating which pieces the peer has.

        Returns:
            Piece index to download, or None if no piece is available.
        """
        with self._lock:
            candidates = []
            min_freq = float('inf')

            for i in range(self.num_pieces):
                if self.pieces[i].status != PieceStatus.MISSING:
                    continue
                if i >= len(peer_pieces) or not peer_pieces[i]:
                    continue

                freq = self._peer_frequency.get(i, 0)
                if freq < min_freq:
                    min_freq = freq
                    candidates = [i]
                elif freq == min_freq:
                    candidates.append(i)

            if not candidates:
                return None

            selected = random.choice(candidates)
            self.rarest_selections[selected] = (
                self.rarest_selections.get(selected, 0) + 1
            )
            return selected

    def select_piece_random(self, peer_pieces: List[bool]) -> Optional[int]:
        """Select a random piece from available missing pieces.

        Baseline algorithm for comparison with rarest-first.

        Args:
            peer_pieces: List of booleans indicating which pieces the peer has.

        Returns:
            Piece index to download, or None if no piece is available.
        """
        candidates = []
        for i in range(self.num_pieces):
            if self.pieces[i].status != PieceStatus.MISSING:
                continue
            if i >= len(peer_pieces) or not peer_pieces[i]:
                continue
            candidates.append(i)

        if not candidates:
            return None

        return random.choice(candidates)

    def start_piece(self, piece_index: int) -> List[Block]:
        """Mark a piece as in-progress and return its pending blocks.

        Args:
            piece_index: Index of the piece to start downloading.

        Returns:
            List of blocks to request.
        """
        piece = self.pieces[piece_index]
        piece.status = PieceStatus.IN_PROGRESS
        self._piece_start_times[piece_index] = time.time()
        return piece.get_pending_blocks()

    def reset_stale_pieces(self, timeout: float):
        """Reset pieces that have been IN_PROGRESS longer than timeout.

        This prevents pieces from getting stuck when a peer dies mid-transfer.

        Args:
            timeout: Seconds after which an IN_PROGRESS piece is considered stale.
        """
        now = time.time()
        stale = []
        for idx, start_time in list(self._piece_start_times.items()):
            if idx < len(self.pieces) and self.pieces[idx].status == PieceStatus.IN_PROGRESS:
                if now - start_time > timeout:
                    stale.append(idx)

        for idx in stale:
            self.pieces[idx].reset()
            del self._piece_start_times[idx]
            logger.debug(f"Reset stale piece {idx} after {timeout}s timeout")

    def submit_block(self, piece_index: int, offset: int, data: bytes) -> bool:
        """Submit a received block to a piece.

        Args:
            piece_index: Index of the piece.
            offset: Byte offset within the piece.
            data: Block data.

        Returns:
            True if the piece is now complete (all blocks received).
        """
        if piece_index < 0 or piece_index >= self.num_pieces:
            logger.warning(f"Invalid piece index: {piece_index}")
            return False

        piece = self.pieces[piece_index]
        return piece.submit_block(offset, data)

    def verify_piece(self, piece_index: int) -> bool:
        """Verify a completed piece's hash.

        Args:
            piece_index: Index of the piece to verify.

        Returns:
            True if the hash matches.
        """
        piece = self.pieces[piece_index]
        if piece.verify_hash():
            piece.status = PieceStatus.COMPLETED
            logger.info(f"Piece {piece_index} verified successfully")
            return True
        else:
            piece.reset()
            logger.warning(f"Piece {piece_index} failed hash verification")
            return False

    def get_piece_data(self, piece_index: int) -> Optional[bytes]:
        """Get the data for a completed piece.

        Args:
            piece_index: Index of the piece.

        Returns:
            Piece data bytes, or None if piece is not completed.
        """
        piece = self.pieces[piece_index]
        if piece.status == PieceStatus.COMPLETED:
            return piece.data
        return None

    def get_status_list(self) -> List[str]:
        """Get a list of piece statuses as strings."""
        return [p.status.value for p in self.pieces]

    def get_frequency(self, piece_index: int) -> int:
        """Get the number of peers that have a specific piece."""
        return self._peer_frequency.get(piece_index, 0)

    def has_piece(self, piece_index: int) -> bool:
        """Check if we have completed a piece."""
        return self.pieces[piece_index].status == PieceStatus.COMPLETED

    def get_our_bitfield(self) -> List[bool]:
        """Get our current bitfield as a list of booleans."""
        return [p.status == PieceStatus.COMPLETED for p in self.pieces]
