"""
Tests for the PeerConnection module.
"""

import asyncio
import struct
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
