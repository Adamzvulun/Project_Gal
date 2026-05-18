"""
Tests for the PeerConnection module.
"""

import asyncio
import struct
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from python_engine.peer_connection import (
    PeerConnection, PeerMessage, MessageType, PeerConnectionError,
    PROTOCOL_STRING, PROTOCOL_STRING_LEN, HANDSHAKE_LEN, BLOCK_SIZE
)


class TestPeerMessage:
    def test_keep_alive(self):
        msg = PeerMessage(MessageType.KEEP_ALIVE)
        assert msg.type == MessageType.KEEP_ALIVE
        assert msg.payload == b''

    def test_have_piece_index(self):
        payload = struct.pack('!I', 42)
        msg = PeerMessage(MessageType.HAVE, payload)
        assert msg.piece_index == 42

    def test_request_fields(self):
        payload = struct.pack('!III', 5, 0, 16384)
        msg = PeerMessage(MessageType.REQUEST, payload)
        assert msg.piece_index == 5
        assert msg.block_offset == 0
        assert msg.block_length == 16384

    def test_piece_fields(self):
        block_data = b'\x00' * 100
        payload = struct.pack('!II', 3, 0) + block_data
        msg = PeerMessage(MessageType.PIECE, payload)
        assert msg.piece_index == 3
        assert msg.block_offset == 0
        assert msg.block_data == block_data

    def test_bitfield_data(self):
        bf = b'\xff\x00'
        msg = PeerMessage(MessageType.BITFIELD, bf)
        assert msg.bitfield_data == b'\xff\x00'

    def test_repr(self):
        msg = PeerMessage(MessageType.CHOKE)
        assert 'CHOKE' in repr(msg)


class TestPeerConnectionInit:
    def test_initial_state(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        assert conn.am_choking is True
        assert conn.am_interested is False
        assert conn.peer_choking is True
        assert conn.peer_interested is False
        assert conn.connected is False
        assert len(conn.peer_pieces) == 10
        assert all(p is False for p in conn.peer_pieces)

    def test_has_piece(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        assert conn.has_piece(0) is False
        conn.peer_pieces[5] = True
        assert conn.has_piece(5) is True

    def test_has_piece_out_of_range(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        assert conn.has_piece(100) is False


class TestBitfieldParsing:
    def test_parse_bitfield(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=16
        )
        # 0xFF = all 8 pieces, 0x00 = none
        conn._parse_bitfield(b'\xff\x00')
        assert all(conn.peer_pieces[i] is True for i in range(8))
        assert all(conn.peer_pieces[i] is False for i in range(8, 16))

    def test_parse_bitfield_partial_byte(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=3
        )
        # 0b11100000 = 0xE0 -> first 3 bits set
        conn._parse_bitfield(b'\xe0')
        assert conn.peer_pieces == [True, True, True]


class TestHandshake:
    def test_handshake_format(self):
        """Verify handshake message format is correct."""
        info_hash = b'\x01' * 20
        peer_id = b'\x02' * 20

        # Build expected handshake
        expected = (
            bytes([PROTOCOL_STRING_LEN]) +
            PROTOCOL_STRING +
            b'\x00' * 8 +
            info_hash +
            peer_id
        )
        assert len(expected) == HANDSHAKE_LEN  # 68 bytes
        assert expected[0] == 19
        assert expected[1:20] == b'BitTorrent protocol'


class TestMessageTypes:
    def test_message_type_values(self):
        assert MessageType.CHOKE == 0
        assert MessageType.UNCHOKE == 1
        assert MessageType.INTERESTED == 2
        assert MessageType.NOT_INTERESTED == 3
        assert MessageType.HAVE == 4
        assert MessageType.BITFIELD == 5
        assert MessageType.REQUEST == 6
        assert MessageType.PIECE == 7
        assert MessageType.CANCEL == 8

    def test_keep_alive_special(self):
        assert MessageType.KEEP_ALIVE == -1


class TestMessageHandling:
    @pytest.mark.asyncio
    async def test_handle_choke(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        conn.peer_choking = False
        msg = PeerMessage(MessageType.CHOKE)
        await conn._handle_message(msg)
        assert conn.peer_choking is True

    @pytest.mark.asyncio
    async def test_handle_unchoke(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        msg = PeerMessage(MessageType.UNCHOKE)
        await conn._handle_message(msg)
        assert conn.peer_choking is False

    @pytest.mark.asyncio
    async def test_handle_interested(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        msg = PeerMessage(MessageType.INTERESTED)
        await conn._handle_message(msg)
        assert conn.peer_interested is True

    @pytest.mark.asyncio
    async def test_handle_not_interested(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        conn.peer_interested = True
        msg = PeerMessage(MessageType.NOT_INTERESTED)
        await conn._handle_message(msg)
        assert conn.peer_interested is False

    @pytest.mark.asyncio
    async def test_handle_have(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        payload = struct.pack('!I', 5)
        msg = PeerMessage(MessageType.HAVE, payload)
        await conn._handle_message(msg)
        assert conn.peer_pieces[5] is True

    @pytest.mark.asyncio
    async def test_handle_have_invalid_index(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        payload = struct.pack('!I', 100)  # Out of range
        msg = PeerMessage(MessageType.HAVE, payload)
        with pytest.raises(PeerConnectionError):
            await conn._handle_message(msg)

    @pytest.mark.asyncio
    async def test_handle_piece_updates_stats(self):
        conn = PeerConnection(
            ip='192.168.1.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=10
        )
        block_data = b'\x00' * 1000
        payload = struct.pack('!II', 0, 0) + block_data
        msg = PeerMessage(MessageType.PIECE, payload)
        await conn._handle_message(msg)
        assert conn.bytes_downloaded == 1000


class TestSlidingWindow:
    """Sliding-window contribution metric used by tit-for-tat."""

    def _make_conn(self):
        return PeerConnection(
            ip='10.0.0.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=4
        )

    def test_empty_returns_zero(self):
        conn = self._make_conn()
        assert conn.bytes_received_in_window(20.0) == 0
        assert conn.bytes_received_in_window(0.001) == 0

    def test_sums_recent_samples(self):
        conn = self._make_conn()
        now = 1000.0
        conn._download_samples.extend([
            (now - 1, 100),
            (now - 5, 200),
            (now - 10, 300),
        ])
        with patch('python_engine.peer_connection.time.time', return_value=now):
            assert conn.bytes_received_in_window(20.0) == 600
            assert conn.bytes_received_in_window(6.0) == 300
            assert conn.bytes_received_in_window(0.5) == 0

    def test_window_excludes_old_samples(self):
        conn = self._make_conn()
        now = 1000.0
        # 100 bytes at t=now-30 is outside a 20s window
        conn._download_samples.extend([
            (now - 30, 100),
            (now - 25, 200),
            (now - 19, 300),
            (now - 1, 400),
        ])
        with patch('python_engine.peer_connection.time.time', return_value=now):
            assert conn.bytes_received_in_window(20.0) == 700

    def test_does_not_mutate_samples(self):
        conn = self._make_conn()
        now = 1000.0
        conn._download_samples.extend([
            (now - 30, 100),
            (now - 1, 400),
        ])
        original_len = len(conn._download_samples)
        with patch('python_engine.peer_connection.time.time', return_value=now):
            conn.bytes_received_in_window(5.0)
        assert len(conn._download_samples) == original_len

    @pytest.mark.asyncio
    async def test_piece_handler_appends_and_evicts(self):
        conn = self._make_conn()
        # Seed with an old sample that should get evicted.
        conn._download_samples.append((time.time() - 100, 999))
        block_data = b'\x00' * 1234
        payload = struct.pack('!II', 0, 0) + block_data
        msg = PeerMessage(MessageType.PIECE, payload)
        await conn._handle_message(msg)
        # The stale sample is gone; only the just-received one remains.
        assert len(conn._download_samples) == 1
        assert conn._download_samples[0][1] == 1234
        # Sliding-window metric agrees with the cumulative bytes_downloaded.
        assert conn.bytes_received_in_window(20.0) == 1234
        assert conn.bytes_downloaded == 1234

    def test_cumulative_bytes_downloaded_unchanged(self):
        """Adding the sliding-window metric must not break cumulative stats."""
        conn = self._make_conn()
        assert conn.bytes_downloaded == 0  # public field still exists, defaults to 0


class TestSnubbing:
    """is_snubbed: detect peers that unchoke us then stop sending blocks."""

    def _make_conn(self):
        return PeerConnection(
            ip='10.0.0.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=4
        )

    def test_not_snubbed_when_peer_choking_us(self):
        # A choking peer can't be snubbing us by definition — they've
        # advertised "don't send me requests, I won't send you blocks".
        conn = self._make_conn()
        conn.peer_choking = True
        conn._last_request_time = 100.0
        conn._last_piece_time = 100.0
        conn._connect_time = 100.0
        with patch('python_engine.peer_connection.time.time', return_value=1_000.0):
            assert conn.is_snubbed() is False

    def test_not_snubbed_when_no_requests_sent(self):
        # We've never asked this peer for anything. Their silence is normal.
        conn = self._make_conn()
        conn.peer_choking = False
        conn._last_request_time = 0
        conn._connect_time = 100.0
        with patch('python_engine.peer_connection.time.time', return_value=1_000.0):
            assert conn.is_snubbed() is False

    def test_snubbed_after_threshold_silence(self):
        # Unchoking us + we asked + no piece in >60s ⇒ snubbed.
        conn = self._make_conn()
        conn.peer_choking = False
        conn._last_request_time = 100.0
        conn._last_piece_time = 100.0  # 900s ago
        conn._connect_time = 100.0
        with patch('python_engine.peer_connection.time.time', return_value=1_000.0):
            assert conn.is_snubbed() is True

    def test_recent_piece_clears_snub(self):
        # A piece arrived 5 seconds ago — peer is feeding us, not snubbing.
        conn = self._make_conn()
        conn.peer_choking = False
        conn._last_request_time = 900.0
        conn._last_piece_time = 995.0
        conn._connect_time = 100.0
        with patch('python_engine.peer_connection.time.time', return_value=1_000.0):
            assert conn.is_snubbed() is False

    def test_threshold_is_configurable(self):
        # Boundary check: with threshold=10, 11s silence ⇒ snubbed,
        # 9s silence ⇒ not snubbed.
        conn = self._make_conn()
        conn.peer_choking = False
        conn._last_request_time = 100.0
        conn._connect_time = 100.0
        with patch('python_engine.peer_connection.time.time', return_value=1_000.0):
            conn._last_piece_time = 989.0  # 11s ago
            assert conn.is_snubbed(threshold=10.0) is True
            conn._last_piece_time = 991.0  # 9s ago
            assert conn.is_snubbed(threshold=10.0) is False

    def test_connect_time_fallback_protects_fresh_peer(self):
        # A peer who just connected and hasn't sent a piece yet should not be
        # snubbed until the threshold has elapsed since handshake.
        conn = self._make_conn()
        conn.peer_choking = False
        conn._last_request_time = 990.0
        conn._last_piece_time = 0  # never received a piece yet
        conn._connect_time = 990.0  # connected 10s ago
        with patch('python_engine.peer_connection.time.time', return_value=1_000.0):
            assert conn.is_snubbed(threshold=60.0) is False
            # But after the threshold, the same peer becomes snubbed.
        with patch('python_engine.peer_connection.time.time', return_value=1_100.0):
            assert conn.is_snubbed(threshold=60.0) is True


class TestUploadSlidingWindow:
    """bytes_sent_in_window: symmetric to bytes_received_in_window.

    Drives seeding-mode tit-for-tat (sort peers by who drains our
    upload fastest, not by what they send us — which is zero in
    seed mode).
    """

    def _make_conn(self):
        return PeerConnection(
            ip='10.0.0.1', port=6881,
            info_hash=b'\x01' * 20, peer_id=b'\x02' * 20,
            num_pieces=4
        )

    def test_empty_returns_zero(self):
        conn = self._make_conn()
        assert conn.bytes_sent_in_window() == 0

    def test_sums_recent_uploads(self):
        conn = self._make_conn()
        now = 1000.0
        conn._upload_samples.extend([
            (now - 5, 100),
            (now - 2, 250),
            (now - 1, 50),
        ])
        with patch('python_engine.peer_connection.time.time', return_value=now):
            assert conn.bytes_sent_in_window(window=10.0) == 400

    def test_window_excludes_old_samples(self):
        conn = self._make_conn()
        now = 1000.0
        conn._upload_samples.extend([
            (now - 25, 99999),  # outside 20s window
            (now - 5, 200),
            (now - 1, 100),
        ])
        with patch('python_engine.peer_connection.time.time', return_value=now):
            assert conn.bytes_sent_in_window(window=20.0) == 300

    def test_does_not_mutate_samples(self):
        conn = self._make_conn()
        now = 1000.0
        conn._upload_samples.extend([
            (now - 30, 100),
            (now - 1, 400),
        ])
        original_len = len(conn._upload_samples)
        with patch('python_engine.peer_connection.time.time', return_value=now):
            conn.bytes_sent_in_window(5.0)
        assert len(conn._upload_samples) == original_len

    @pytest.mark.asyncio
    async def test_send_piece_appends_and_evicts(self):
        """send_piece must append a sample and drop stale ones."""
        conn = self._make_conn()
        # Stub the write side so we don't touch real sockets.
        conn.send_message = AsyncMock()
        # Seed with a stale sample that should get evicted.
        conn._upload_samples.append((time.time() - 100, 999))
        block_data = b'\xab' * 512
        await conn.send_piece(piece_index=0, begin=0, data=block_data)
        # Stale sample dropped; new one appended.
        assert len(conn._upload_samples) == 1
        assert conn._upload_samples[0][1] == 512
        # Window read agrees with cumulative bytes_uploaded.
        assert conn.bytes_sent_in_window(20.0) == 512
        assert conn.bytes_uploaded == 512

    def test_cumulative_bytes_uploaded_unchanged(self):
        """The new window metric doesn't replace the cumulative counter."""
        conn = self._make_conn()
        assert conn.bytes_uploaded == 0
