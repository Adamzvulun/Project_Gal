"""
Tests for the PieceManager module.
"""

import hashlib
import pytest
from python_engine.piece_manager import (
    PieceManager, PieceStatus, Piece, Block
)


def make_piece_hashes(num_pieces, piece_length):
    """Create dummy piece hashes for testing."""
    hashes = []
    for i in range(num_pieces):
        data = bytes([i % 256]) * piece_length
        hashes.append(hashlib.sha1(data).digest())
    return hashes


class TestBlock:
    def test_block_creation(self):
        b = Block(piece_index=0, offset=0, length=16384)
        assert b.piece_index == 0
        assert b.offset == 0
        assert b.length == 16384
        assert b.data is None
        assert b.received is False

    def test_block_repr(self):
        b = Block(0, 0, 16384)
        assert 'piece=0' in repr(b)


class TestPiece:
    def test_piece_creation(self):
        h = hashlib.sha1(b'\x00' * 256).digest()
        p = Piece(index=0, length=256, expected_hash=h)
        assert p.index == 0
        assert p.length == 256
        assert p.status == PieceStatus.MISSING
        assert not p.is_complete

    def test_piece_blocks(self):
        h = hashlib.sha1(b'\x00' * 32768).digest()
        p = Piece(index=0, length=32768, expected_hash=h)
        # 32768 / 16384 = 2 blocks
        assert p.num_blocks == 2
        assert p.blocks[0].offset == 0
        assert p.blocks[0].length == 16384
        assert p.blocks[1].offset == 16384
        assert p.blocks[1].length == 16384

    def test_piece_last_block_smaller(self):
        h = hashlib.sha1(b'\x00' * 20000).digest()
        p = Piece(index=0, length=20000, expected_hash=h)
        assert p.num_blocks == 2
        assert p.blocks[0].length == 16384
        assert p.blocks[1].length == 20000 - 16384  # 3616

    def test_submit_block(self):
        data = b'\x00' * 256
        h = hashlib.sha1(data).digest()
        p = Piece(index=0, length=256, expected_hash=h)
        # Only one block for small piece
        result = p.submit_block(0, data)
        assert result is True
        assert p.is_complete

    def test_verify_hash_success(self):
        data = b'hello world' + b'\x00' * 245  # Pad to 256
        h = hashlib.sha1(data).digest()
        p = Piece(index=0, length=256, expected_hash=h)
        p.submit_block(0, data)
        assert p.verify_hash() is True

    def test_verify_hash_failure(self):
        data = b'\x00' * 256
        wrong_hash = b'\xff' * 20
        p = Piece(index=0, length=256, expected_hash=wrong_hash)
        p.submit_block(0, data)
        assert p.verify_hash() is False

    def test_reset_piece(self):
        data = b'\x00' * 256
        h = hashlib.sha1(data).digest()
        p = Piece(index=0, length=256, expected_hash=h)
        p.submit_block(0, data)
        p.status = PieceStatus.COMPLETED
        p.reset()
        assert p.status == PieceStatus.MISSING
        assert not p.is_complete
        assert all(not b.received for b in p.blocks)

    def test_get_pending_blocks(self):
        h = hashlib.sha1(b'\x00' * 32768).digest()
        p = Piece(index=0, length=32768, expected_hash=h)
        pending = p.get_pending_blocks()
        assert len(pending) == 2

        # Submit first block
        p.submit_block(0, b'\x00' * 16384)
        pending = p.get_pending_blocks()
        assert len(pending) == 1
        assert pending[0].offset == 16384


class TestPieceManager:
    def setup_method(self):
        self.num_pieces = 10
        self.piece_length = 256
        self.total_size = self.num_pieces * self.piece_length
        self.hashes = make_piece_hashes(self.num_pieces, self.piece_length)
        self.pm = PieceManager(
            self.num_pieces, self.piece_length,
            self.total_size, self.hashes
        )

    def test_initial_state(self):
        assert self.pm.num_pieces == 10
        assert self.pm.completed_pieces == 0
        assert self.pm.bytes_downloaded == 0
        assert self.pm.bytes_remaining == self.total_size
        assert self.pm.progress == 0.0
        assert not self.pm.is_complete

    def test_update_peer_pieces(self):
        pieces = [True, False, True, False, True,
                  False, True, False, True, False]
        self.pm.update_peer_pieces("peer1", pieces)
        assert self.pm.get_frequency(0) == 1
        assert self.pm.get_frequency(1) == 0
        assert self.pm.get_frequency(2) == 1

    def test_update_peer_have(self):
        self.pm.update_peer_have("peer1", 3)
        assert self.pm.get_frequency(3) == 1
        # Duplicate should not double-count
        self.pm.update_peer_have("peer1", 3)
        assert self.pm.get_frequency(3) == 1

    def test_remove_peer(self):
        pieces = [True] * 10
        self.pm.update_peer_pieces("peer1", pieces)
        assert self.pm.get_frequency(0) == 1
        self.pm.remove_peer("peer1")
        assert self.pm.get_frequency(0) == 0

    def test_select_piece_rarest_first(self):
        # peer1 has all pieces
        self.pm.update_peer_pieces("peer1", [True] * 10)
        # peer2 has only piece 5
        pieces2 = [False] * 10
        pieces2[5] = True
        self.pm.update_peer_pieces("peer2", pieces2)

        # Piece 5 has frequency 2, all others have 1
        # Rarest-first should pick from pieces with freq 1
        peer_has = [True] * 10
        selected = self.pm.select_piece_rarest_first(peer_has)
        assert selected is not None
        assert selected != 5  # 5 has higher frequency

    def test_select_piece_rarest_first_no_candidates(self):
        # Mark all pieces as completed
        for p in self.pm.pieces:
            p.status = PieceStatus.COMPLETED
        result = self.pm.select_piece_rarest_first([True] * 10)
        assert result is None

    def test_select_piece_rarest_first_peer_missing(self):
        # Peer has no pieces
        result = self.pm.select_piece_rarest_first([False] * 10)
        assert result is None

    def test_select_piece_random(self):
        peer_has = [True] * 10
        selected = self.pm.select_piece_random(peer_has)
        assert selected is not None
        assert 0 <= selected < 10

    def test_select_piece_random_no_candidates(self):
        for p in self.pm.pieces:
            p.status = PieceStatus.COMPLETED
        result = self.pm.select_piece_random([True] * 10)
        assert result is None

    def test_start_piece(self):
        blocks = self.pm.start_piece(0)
        assert len(blocks) > 0
        assert self.pm.pieces[0].status == PieceStatus.IN_PROGRESS

    def test_submit_and_verify(self):
        data = bytes([0]) * self.piece_length
        expected_hash = hashlib.sha1(data).digest()
        # Replace the hash in our manager
        self.pm.pieces[0] = Piece(0, self.piece_length, expected_hash)

        self.pm.start_piece(0)
        complete = self.pm.submit_block(0, 0, data)
        assert complete is True
        assert self.pm.verify_piece(0) is True
        assert self.pm.pieces[0].status == PieceStatus.COMPLETED
        assert self.pm.completed_pieces == 1

    def test_submit_bad_hash(self):
        bad_hash = b'\xff' * 20
        self.pm.pieces[0] = Piece(0, self.piece_length, bad_hash)
        self.pm.start_piece(0)
        self.pm.submit_block(0, 0, b'\x00' * self.piece_length)
        assert self.pm.verify_piece(0) is False
        assert self.pm.pieces[0].status == PieceStatus.MISSING

    def test_get_status_list(self):
        statuses = self.pm.get_status_list()
        assert len(statuses) == 10
        assert all(s == "missing" for s in statuses)

    def test_get_our_bitfield(self):
        bf = self.pm.get_our_bitfield()
        assert len(bf) == 10
        assert all(b is False for b in bf)

    def test_has_piece(self):
        assert self.pm.has_piece(0) is False
        self.pm.pieces[0].status = PieceStatus.COMPLETED
        assert self.pm.has_piece(0) is True

    def test_progress_after_completion(self):
        for p in self.pm.pieces:
            p.status = PieceStatus.COMPLETED
        assert self.pm.progress == 1.0
        assert self.pm.is_complete

    def test_frequency_multiple_peers(self):
        self.pm.update_peer_pieces("peer1", [True, True, False] + [False] * 7)
        self.pm.update_peer_pieces("peer2", [True, False, True] + [False] * 7)
        self.pm.update_peer_pieces("peer3", [True, False, False] + [False] * 7)

        assert self.pm.get_frequency(0) == 3  # All 3 peers
        assert self.pm.get_frequency(1) == 1  # Only peer1
        assert self.pm.get_frequency(2) == 1  # Only peer2

        # Rarest first should pick piece 1 or 2 (both freq 1)
        peer_has = [True, True, True] + [False] * 7
        selected = self.pm.select_piece_rarest_first(peer_has)
        assert selected in (1, 2)
