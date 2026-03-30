"""
Tests for the DownloadManager module.
"""

import hashlib
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from python_engine.bencode import encode
from python_engine.torrent_metadata import TorrentMetadata
from python_engine.download_manager import (
    Download, DownloadManager, DownloadState, DownloadStats,
    AlgorithmType
)


def make_torrent():
    """Create a test TorrentMetadata object."""
    info = {
        b'length': 1024,
        b'name': b'test.txt',
        b'piece length': 256,
        b'pieces': b'\x00' * 80,  # 4 pieces
    }
    torrent = {
        b'announce': b'http://tracker.example.com/announce',
        b'info': info,
    }
    return TorrentMetadata(torrent_data=encode(torrent))


class TestDownloadStats:
    def test_initial_stats(self):
        stats = DownloadStats()
        assert stats.bytes_downloaded == 0
        assert stats.bytes_uploaded == 0
        assert stats.download_speed == 0.0
        assert stats.elapsed_time == 0

    def test_average_speed(self):
        stats = DownloadStats()
        stats.start_time = 0
        stats.end_time = 10
        stats.bytes_downloaded = 10000
        assert stats.average_speed == 1000.0


class TestDownload:
    def test_download_creation(self):
        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        assert dl.state == DownloadState.QUEUED
        assert dl.file_name == 'test.txt'
        assert dl.file_size == 1024
        assert dl.progress == 0.0
        assert dl.connected_peers == 0

    def test_download_algorithms(self):
        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            piece_algorithm=AlgorithmType.RANDOM,
            peer_algorithm=AlgorithmType.ROUND_ROBIN
        )
        assert dl.piece_algorithm == AlgorithmType.RANDOM
        assert dl.peer_algorithm == AlgorithmType.ROUND_ROBIN

    def test_get_status(self):
        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        status = dl.get_status()
        assert status['name'] == 'test.txt'
        assert status['size'] == 1024
        assert status['progress'] == 0.0
        assert status['state'] == 'Queued'
        assert 'download_speed' in status
        assert 'connected_peers' in status

    def test_peer_id_generated(self):
        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        assert len(dl.peer_id) == 20
        assert dl.peer_id.startswith(b'-PG0001-')


class TestDownloadManager:
    @pytest.mark.asyncio
    async def test_add_torrent(self):
        manager = DownloadManager(
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        torrent = make_torrent()
        dl = await manager.add_torrent(torrent)
        assert dl.id in manager.downloads
        assert dl.state == DownloadState.QUEUED

    @pytest.mark.asyncio
    async def test_get_all_status(self):
        manager = DownloadManager(
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        torrent = make_torrent()
        await manager.add_torrent(torrent)
        statuses = manager.get_all_status()
        assert len(statuses) == 1
        assert statuses[0]['name'] == 'test.txt'

    @pytest.mark.asyncio
    async def test_get_download_status(self):
        manager = DownloadManager(
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        torrent = make_torrent()
        dl = await manager.add_torrent(torrent)
        status = manager.get_download_status(dl.id)
        assert status is not None
        assert status['id'] == dl.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_download(self):
        manager = DownloadManager(
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        assert manager.get_download_status("nonexistent") is None

    @pytest.mark.asyncio
    async def test_multiple_downloads(self):
        manager = DownloadManager(
            download_dir='/tmp/downloads',
            state_dir='/tmp/state'
        )
        torrent = make_torrent()
        dl1 = await manager.add_torrent(torrent)
        dl2 = await manager.add_torrent(torrent)
        assert len(manager.downloads) == 2
        assert dl1.id != dl2.id


class TestAlgorithmType:
    def test_algorithm_values(self):
        assert AlgorithmType.RAREST_FIRST.value == "rarest_first"
        assert AlgorithmType.RANDOM.value == "random"
        assert AlgorithmType.TIT_FOR_TAT.value == "tit_for_tat"
        assert AlgorithmType.ROUND_ROBIN.value == "round_robin"


class TestDownloadState:
    def test_state_values(self):
        assert DownloadState.QUEUED.value == "Queued"
        assert DownloadState.RUNNING.value == "Running"
        assert DownloadState.PAUSED.value == "Paused"
        assert DownloadState.COMPLETED.value == "Completed"
        assert DownloadState.CANCELLED.value == "Cancelled"
        assert DownloadState.ERROR.value == "Error"
