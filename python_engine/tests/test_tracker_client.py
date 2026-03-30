"""
Tests for the TrackerClient module.
"""

import pytest
import struct
from python_engine.tracker_client import (
    Peer, TrackerResponse, TrackerClient, generate_peer_id
)


class TestPeerId:
    def test_peer_id_length(self):
        pid = generate_peer_id()
        assert len(pid) == 20

    def test_peer_id_prefix(self):
        pid = generate_peer_id()
        assert pid.startswith(b'-PG0001-')

    def test_peer_id_unique(self):
        pid1 = generate_peer_id()
        pid2 = generate_peer_id()
        assert pid1 != pid2


class TestPeer:
    def test_peer_creation(self):
        p = Peer('192.168.1.1', 6881)
        assert p.ip == '192.168.1.1'
        assert p.port == 6881

    def test_peer_equality(self):
        p1 = Peer('192.168.1.1', 6881)
        p2 = Peer('192.168.1.1', 6881)
        assert p1 == p2

    def test_peer_hash(self):
        p1 = Peer('192.168.1.1', 6881)
        p2 = Peer('192.168.1.1', 6881)
        assert hash(p1) == hash(p2)

    def test_peer_repr(self):
        p = Peer('192.168.1.1', 6881)
        assert '192.168.1.1' in repr(p)


class TestTrackerResponse:
    def test_parse_compact_peers(self):
        # Create compact peer data: 2 peers
        peer1_ip = bytes([192, 168, 1, 1])
        peer1_port = struct.pack('!H', 6881)
        peer2_ip = bytes([10, 0, 0, 1])
        peer2_port = struct.pack('!H', 6882)

        data = {
            b'interval': 1800,
            b'complete': 5,
            b'incomplete': 3,
            b'peers': peer1_ip + peer1_port + peer2_ip + peer2_port,
        }

        response = TrackerResponse(data)
        assert response.interval == 1800
        assert response.complete == 5
        assert response.incomplete == 3
        assert len(response.peers) == 2
        assert response.peers[0].ip == '192.168.1.1'
        assert response.peers[0].port == 6881
        assert response.peers[1].ip == '10.0.0.1'
        assert response.peers[1].port == 6882

    def test_parse_regular_peers(self):
        data = {
            b'interval': 900,
            b'complete': 2,
            b'incomplete': 1,
            b'peers': [
                {b'ip': b'192.168.1.1', b'port': 6881, b'peer id': b'A' * 20},
                {b'ip': b'10.0.0.1', b'port': 6882},
            ],
        }

        response = TrackerResponse(data)
        assert len(response.peers) == 2
        assert response.peers[0].ip == '192.168.1.1'
        assert response.peers[0].peer_id == b'A' * 20
        assert response.peers[1].peer_id is None

    def test_parse_failure_reason(self):
        data = {b'failure reason': b'Torrent not registered'}
        response = TrackerResponse(data)
        assert response.failure_reason == 'Torrent not registered'
        assert response.peers == []

    def test_parse_warning(self):
        data = {
            b'interval': 1800,
            b'warning message': b'Slow down',
            b'peers': b'',
        }
        response = TrackerResponse(data)
        assert response.warning_message == 'Slow down'

    def test_compact_peers_bad_length(self):
        data = {
            b'interval': 1800,
            b'peers': b'\x00\x00\x00',  # Not multiple of 6
        }
        response = TrackerResponse(data)
        assert response.peers == []


class TestTrackerClient:
    def test_url_building(self):
        client = TrackerClient(
            announce_url='http://tracker.example.com/announce',
            info_hash=b'\x01' * 20,
            peer_id=b'\x02' * 20,
            port=6881
        )

        url = client._build_announce_url({
            'info_hash': client.info_hash,
            'peer_id': client.peer_id,
            'port': 6881,
            'uploaded': 0,
            'downloaded': 0,
            'left': 1000,
            'compact': 1,
        })

        assert 'http://tracker.example.com/announce?' in url
        assert 'port=6881' in url
        assert 'uploaded=0' in url
        assert 'left=1000' in url
        assert 'compact=1' in url

    def test_update_stats(self):
        client = TrackerClient(
            announce_url='http://tracker.example.com/announce',
            info_hash=b'\x01' * 20,
            peer_id=b'\x02' * 20,
        )
        client.update_stats(uploaded=100, downloaded=500, left=500)
        assert client.uploaded == 100
        assert client.downloaded == 500
        assert client.left == 500
