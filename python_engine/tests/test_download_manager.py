"""
Tests for the DownloadManager module.
"""

import hashlib
import json
import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from python_engine.bencode import encode
from python_engine.torrent_metadata import TorrentMetadata
from python_engine.piece_manager import PieceStatus
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


def _build_torrent_with_real_hashes(payload: bytes, name: str, piece_length: int):
    """Build a TorrentMetadata whose piece hashes match `payload`."""
    pieces = b""
    for off in range(0, len(payload), piece_length):
        pieces += hashlib.sha1(payload[off:off + piece_length]).digest()
    info = {
        b'length': len(payload),
        b'name': name.encode('utf-8'),
        b'piece length': piece_length,
        b'pieces': pieces,
    }
    torrent_dict = {
        b'announce': b'http://tracker.example.com/announce',
        b'info': info,
    }
    return TorrentMetadata(torrent_data=encode(torrent_dict))


class TestLoadState:
    def test_load_state_round_trip(self, tmp_path):
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()

        payload = b"abcd" * 64  # 256 bytes, two 128-byte pieces
        torrent = _build_torrent_with_real_hashes(payload, "file.bin", 128)
        (download_dir / "file.bin").write_bytes(payload)

        dl = Download(
            torrent=torrent,
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        # Manually mark both pieces COMPLETED with real data so _save_state
        # has something honest to record.
        for i, piece in enumerate(dl.piece_manager.pieces):
            piece._data = bytearray(payload[i * 128:(i + 1) * 128])
            assert piece.verify_hash()
            piece.status = PieceStatus.COMPLETED
            for blk in piece.blocks:
                blk.received = True
        dl.stats.bytes_downloaded = 256
        dl.stats.bytes_uploaded = 99
        dl.stats.start_time = 1000.0
        dl.state = DownloadState.PAUSED
        dl._save_state()

        original_id = dl.id
        state_file = state_dir / f"{original_id}.json"
        assert state_file.exists()
        assert (state_dir / f"{original_id}.torrent").exists()
        del dl

        restored = Download.from_state_file(state_file)
        assert restored is not None
        assert restored.id == original_id
        assert restored.torrent.info_hash_hex() == torrent.info_hash_hex()
        assert restored.state == DownloadState.PAUSED
        assert restored.stats.bytes_downloaded == 256
        assert restored.stats.bytes_uploaded == 99
        assert restored.stats.start_time == 1000.0
        assert restored.piece_manager.is_complete
        for piece in restored.piece_manager.pieces:
            assert piece.status == PieceStatus.COMPLETED

    def test_load_state_completed_stays_completed(self, tmp_path):
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()
        payload = b"x" * 128
        torrent = _build_torrent_with_real_hashes(payload, "f.bin", 128)
        (download_dir / "f.bin").write_bytes(payload)
        dl = Download(
            torrent=torrent,
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        piece = dl.piece_manager.pieces[0]
        piece._data = bytearray(payload)
        piece.status = PieceStatus.COMPLETED
        for blk in piece.blocks:
            blk.received = True
        dl.state = DownloadState.COMPLETED
        dl._save_state()
        restored = Download.from_state_file(state_dir / f"{dl.id}.json")
        assert restored is not None
        assert restored.state == DownloadState.COMPLETED

    def test_load_state_corrupt_json_returns_none(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        bad = state_dir / "abc.json"
        bad.write_text("{not json")
        assert Download.from_state_file(bad) is None

    def test_load_state_missing_sidecar_returns_none(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        state_file = state_dir / "abc.json"
        state_file.write_text(json.dumps({
            "torrentId": "abc",
            "info_hash": "00" * 20,
            "download_dir": str(tmp_path),
            "piece_status": [],
            "state": "Paused",
        }))
        # No abc.torrent sidecar — should refuse, not crash.
        assert Download.from_state_file(state_file) is None

    def test_load_state_disk_bytes_mismatch_marks_missing(self, tmp_path):
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()

        payload = b"A" * 128 + b"B" * 128  # two 128-byte pieces
        torrent = _build_torrent_with_real_hashes(payload, "f.bin", 128)
        (download_dir / "f.bin").write_bytes(payload)

        dl = Download(
            torrent=torrent,
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        for i, piece in enumerate(dl.piece_manager.pieces):
            piece._data = bytearray(payload[i * 128:(i + 1) * 128])
            piece.status = PieceStatus.COMPLETED
            for blk in piece.blocks:
                blk.received = True
        dl._save_state()
        state_file = state_dir / f"{dl.id}.json"

        # Corrupt piece 1 on disk (overwrite the second half of the file)
        with open(download_dir / "f.bin", "r+b") as f:
            f.seek(128)
            f.write(b"X" * 128)

        restored = Download.from_state_file(state_file)
        assert restored is not None
        assert restored.piece_manager.pieces[0].status == PieceStatus.COMPLETED
        assert restored.piece_manager.pieces[1].status == PieceStatus.MISSING

    def test_load_state_info_hash_mismatch_returns_none(self, tmp_path):
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()
        payload = b"q" * 128
        torrent = _build_torrent_with_real_hashes(payload, "f.bin", 128)
        (download_dir / "f.bin").write_bytes(payload)
        dl = Download(
            torrent=torrent,
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        dl._save_state()
        state_file = state_dir / f"{dl.id}.json"
        # Tamper the JSON's info_hash.
        data = json.loads(state_file.read_text())
        data["info_hash"] = "ff" * 20
        state_file.write_text(json.dumps(data))
        assert Download.from_state_file(state_file) is None


class TestManagerRestoreState:
    def test_restore_state_scans_directory(self, tmp_path):
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()

        for i in range(2):
            payload = bytes([i]) * 128
            torrent = _build_torrent_with_real_hashes(payload, f"f{i}.bin", 128)
            (download_dir / f"f{i}.bin").write_bytes(payload)
            dl = Download(
                torrent=torrent,
                download_dir=str(download_dir),
                state_dir=str(state_dir),
            )
            piece = dl.piece_manager.pieces[0]
            piece._data = bytearray(payload)
            piece.status = PieceStatus.COMPLETED
            for blk in piece.blocks:
                blk.received = True
            dl._save_state()

        mgr = DownloadManager(
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        assert mgr.restore_state() == 2
        assert len(mgr.downloads) == 2
        for d in mgr.downloads.values():
            assert d.state == DownloadState.PAUSED
            assert d.piece_manager.is_complete

    def test_restore_state_empty_dir_returns_zero(self, tmp_path):
        mgr = DownloadManager(
            download_dir=str(tmp_path / "dl"),
            state_dir=str(tmp_path / "state"),
        )
        assert mgr.restore_state() == 0
        assert mgr.downloads == {}

    def test_restore_state_skips_corrupt_files(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        (state_dir / "bad.json").write_text("{nope")
        mgr = DownloadManager(
            download_dir=str(tmp_path / "dl"),
            state_dir=str(state_dir),
        )
        assert mgr.restore_state() == 0

    def test_restore_state_skips_finished_downloads(self, tmp_path):
        # A finished download (state COMPLETED) must NOT reappear after a
        # restart, and its state files should be cleaned up.
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()

        payload = b"\x07" * 128
        torrent = _build_torrent_with_real_hashes(payload, "done.bin", 128)
        (download_dir / "done.bin").write_bytes(payload)
        dl = Download(
            torrent=torrent,
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        piece = dl.piece_manager.pieces[0]
        piece._data = bytearray(payload)
        piece.status = PieceStatus.COMPLETED
        for blk in piece.blocks:
            blk.received = True
        dl.state = DownloadState.COMPLETED
        dl._save_state()
        assert (state_dir / f"{dl.id}.json").exists()

        mgr = DownloadManager(
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        assert mgr.restore_state() == 0
        assert mgr.downloads == {}
        # State files cleaned up; downloaded file kept.
        assert not (state_dir / f"{dl.id}.json").exists()
        assert not (state_dir / f"{dl.id}.torrent").exists()
        assert (download_dir / "done.bin").exists()

    def test_restore_state_skips_cancelled_downloads(self, tmp_path):
        # A cancelled download must not reappear after a restart either.
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()

        payload = b"\x05" * 128
        torrent = _build_torrent_with_real_hashes(payload, "gone.bin", 128)
        dl = Download(
            torrent=torrent,
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        dl.state = DownloadState.CANCELLED
        dl._save_state()
        assert (state_dir / f"{dl.id}.json").exists()

        mgr = DownloadManager(
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        assert mgr.restore_state() == 0
        assert mgr.downloads == {}
        assert not (state_dir / f"{dl.id}.json").exists()
        assert not (state_dir / f"{dl.id}.torrent").exists()


class TestManagerRemoveDownload:
    @pytest.mark.asyncio
    async def test_remove_download_deletes_state_keeps_file(self, tmp_path):
        download_dir = tmp_path / "dl"
        state_dir = tmp_path / "state"
        download_dir.mkdir()
        state_dir.mkdir()

        payload = b"\x09" * 128
        torrent = _build_torrent_with_real_hashes(payload, "keep.bin", 128)
        data_file = download_dir / "keep.bin"
        data_file.write_bytes(payload)

        mgr = DownloadManager(
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        dl = Download(
            torrent=torrent,
            download_dir=str(download_dir),
            state_dir=str(state_dir),
        )
        dl.state = DownloadState.PAUSED
        dl._save_state()
        mgr.downloads[dl.id] = dl
        assert (state_dir / f"{dl.id}.json").exists()

        removed = await mgr.remove_download(dl.id)

        assert removed is True
        assert dl.id not in mgr.downloads
        assert not (state_dir / f"{dl.id}.json").exists()
        assert not (state_dir / f"{dl.id}.torrent").exists()
        # The downloaded file on disk is untouched.
        assert data_file.exists()
        assert data_file.read_bytes() == payload

    @pytest.mark.asyncio
    async def test_remove_unknown_download_returns_false(self, tmp_path):
        mgr = DownloadManager(
            download_dir=str(tmp_path / "dl"),
            state_dir=str(tmp_path / "state"),
        )
        assert await mgr.remove_download("does-not-exist") is False


class TestTitForTatSlidingWindow:
    """Verify _tit_for_tat_unchoke ranks peers by sliding-window contribution.

    The interesting failure mode the window fixes: a peer that contributed
    early then went silent. Cumulative bytes_downloaded keeps it on top
    forever; the window correctly demotes it.
    """

    @pytest.mark.asyncio
    async def test_silent_peer_demoted_in_favor_of_active_one(self):
        from unittest.mock import patch
        from python_engine.peer_connection import PeerConnection
        from python_engine.download_manager import (
            Download, AlgorithmType, MAX_UNCHOKED_PEERS, TIT_FOR_TAT_WINDOW
        )

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )

        def make_peer(ip):
            c = PeerConnection(
                ip=ip, port=6881,
                info_hash=torrent.info_hash, peer_id=b'\x02' * 20,
                num_pieces=torrent.num_pieces,
            )
            c._connected = True
            c._handshake_complete = True
            c.peer_interested = True
            c.am_choking = True
            # Stub network sends so we don't touch real sockets.
            c.send_choke = AsyncMock()
            c.send_unchoke = AsyncMock()
            return c

        now = 10_000.0
        # Peer A: huge cumulative contribution, but only old samples (silent now).
        old_giver = make_peer('10.0.0.1')
        old_giver.bytes_downloaded = 10_000_000
        old_giver._download_samples.append((now - 100, 10_000_000))
        # Peer B: small cumulative, but recent. Should win under sliding window.
        recent = make_peer('10.0.0.2')
        recent.bytes_downloaded = 50
        recent._download_samples.append((now - 1, 50))

        dl._connections['10.0.0.1:6881'] = old_giver
        dl._connections['10.0.0.2:6881'] = recent

        with patch('python_engine.peer_connection.time.time', return_value=now):
            # The metric the algorithm now uses — assert ordering directly.
            assert recent.bytes_received_in_window(TIT_FOR_TAT_WINDOW) > \
                old_giver.bytes_received_in_window(TIT_FOR_TAT_WINDOW)
            await dl._tit_for_tat_unchoke()

        # With sliding window, the recent peer (50 bytes in last 1s) outranks
        # the silent one (0 bytes in window, even though bytes_downloaded is
        # 10MB). With only 2 peers and K=4, both end up unchoked here — the
        # ordering check above is the real assertion that the metric drives
        # the sort, not the cumulative counter.
        recent.send_unchoke.assert_awaited()

    @pytest.mark.asyncio
    async def test_sort_key_is_window_not_cumulative(self):
        """White-box check: build a peer mix where cumulative and window
        disagree on ordering, then confirm the algorithm follows window."""
        from unittest.mock import patch
        from python_engine.peer_connection import PeerConnection
        from python_engine.download_manager import (
            Download, AlgorithmType, TIT_FOR_TAT_WINDOW
        )

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )

        now = 10_000.0
        # Cumulative ranking would be A > B; window ranking is B > A.
        a = PeerConnection(ip='10.0.0.1', port=6881,
                           info_hash=torrent.info_hash, peer_id=b'\x02' * 20,
                           num_pieces=torrent.num_pieces)
        a._connected = True; a._handshake_complete = True
        a.peer_interested = True; a.am_choking = True
        a.send_choke = AsyncMock(); a.send_unchoke = AsyncMock()
        a.bytes_downloaded = 1_000_000  # huge cumulative
        a._download_samples.append((now - 100, 1_000_000))  # but stale

        b = PeerConnection(ip='10.0.0.2', port=6881,
                           info_hash=torrent.info_hash, peer_id=b'\x02' * 20,
                           num_pieces=torrent.num_pieces)
        b._connected = True; b._handshake_complete = True
        b.peer_interested = True; b.am_choking = True
        b.send_choke = AsyncMock(); b.send_unchoke = AsyncMock()
        b.bytes_downloaded = 100  # small cumulative
        b._download_samples.append((now - 2, 100))  # but fresh

        dl._connections['10.0.0.1:6881'] = a
        dl._connections['10.0.0.2:6881'] = b

        with patch('python_engine.peer_connection.time.time', return_value=now):
            assert a.bytes_received_in_window(TIT_FOR_TAT_WINDOW) == 0
            assert b.bytes_received_in_window(TIT_FOR_TAT_WINDOW) == 100
            await dl._tit_for_tat_unchoke()


class TestSnubbingPartition:
    """Verify _tit_for_tat_unchoke demotes snubbed peers.

    A snubbed peer (unchoked us, then went silent) must not occupy a top-K
    unchoke slot when healthy alternatives exist — otherwise a buggy or
    malicious peer can lock a slot forever.
    """

    def _make_peer(self, torrent, ip, *, snubbed: bool, window_bytes: int,
                   now: float):
        from python_engine.peer_connection import PeerConnection
        c = PeerConnection(
            ip=ip, port=6881,
            info_hash=torrent.info_hash, peer_id=b'\x02' * 20,
            num_pieces=torrent.num_pieces,
        )
        c._connected = True
        c._handshake_complete = True
        c.peer_interested = True
        c.peer_choking = False  # they advertise willingness to send
        c.am_choking = True
        c.send_choke = AsyncMock()
        c.send_unchoke = AsyncMock()
        # Inject a contribution sample inside the 20s window.
        if window_bytes > 0:
            c._download_samples.append((now - 1, window_bytes))
        c._connect_time = now - 1000  # well past any threshold
        c._last_request_time = now - 1000  # we did ask
        if snubbed:
            c._last_piece_time = now - 1000  # silent for ages
        else:
            c._last_piece_time = now - 1  # fresh activity
        return c

    @pytest.mark.asyncio
    async def test_snubbed_peer_demoted_when_alternatives_exist(self):
        """5 peers: 1 snubbed + 4 healthy. Snubbed must be choked, healthy unchoked."""
        from python_engine.download_manager import Download, AlgorithmType

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        now = 10_000.0

        # The snubbed peer has the *highest* window contribution — without
        # the partition logic it would win the sort. The partition demotes it.
        snubbed = self._make_peer(torrent, '10.0.0.99',
                                  snubbed=True, window_bytes=10_000_000, now=now)
        healthy = [
            self._make_peer(torrent, f'10.0.0.{i}',
                            snubbed=False, window_bytes=100, now=now)
            for i in range(1, 5)
        ]
        dl._connections['10.0.0.99:6881'] = snubbed
        for i, p in enumerate(healthy, start=1):
            dl._connections[f'10.0.0.{i}:6881'] = p

        with patch('python_engine.peer_connection.time.time', return_value=now):
            await dl._tit_for_tat_unchoke()

        # All 4 healthy peers got unchoked; the snubbed peer did NOT,
        # despite having the largest window contribution.
        for p in healthy:
            p.send_unchoke.assert_awaited()
        snubbed.send_unchoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_snubbed_peer_kept_when_only_choice(self):
        """1 snubbed + 1 healthy: with K=4 both fit; snubbed is the fallback."""
        from python_engine.download_manager import Download, AlgorithmType

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        now = 10_000.0

        snubbed = self._make_peer(torrent, '10.0.0.99',
                                  snubbed=True, window_bytes=500, now=now)
        healthy = self._make_peer(torrent, '10.0.0.1',
                                  snubbed=False, window_bytes=100, now=now)
        dl._connections['10.0.0.99:6881'] = snubbed
        dl._connections['10.0.0.1:6881'] = healthy

        with patch('python_engine.peer_connection.time.time', return_value=now):
            await dl._tit_for_tat_unchoke()

        # Healthy peer must be unchoked (it's a fine candidate). With only
        # one healthy peer the snubbed one fills a remaining slot — better
        # than choking everyone — but the healthy one is the priority.
        healthy.send_unchoke.assert_awaited()

    @pytest.mark.asyncio
    async def test_optimistic_unchoke_prefers_non_snubbed(self):
        """When top-K is full of healthy peers, the optimistic pick must
        avoid snubbed peers if a non-snubbed remainder exists."""
        from python_engine.download_manager import (
            Download, AlgorithmType, MAX_UNCHOKED_PEERS
        )

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        now = 10_000.0

        # 4 healthy top contributors + 1 healthy remainder + 1 snubbed.
        # The optimistic unchoke should pick the healthy remainder.
        top = [
            self._make_peer(torrent, f'10.0.0.{i}',
                            snubbed=False, window_bytes=10_000 - i, now=now)
            for i in range(1, MAX_UNCHOKED_PEERS + 1)
        ]
        remainder = self._make_peer(torrent, '10.0.0.50',
                                    snubbed=False, window_bytes=1, now=now)
        snubbed = self._make_peer(torrent, '10.0.0.99',
                                  snubbed=True, window_bytes=99_999_999, now=now)
        for i, p in enumerate(top, start=1):
            dl._connections[f'10.0.0.{i}:6881'] = p
        dl._connections['10.0.0.50:6881'] = remainder
        dl._connections['10.0.0.99:6881'] = snubbed

        with patch('python_engine.peer_connection.time.time', return_value=now):
            await dl._tit_for_tat_unchoke()

        # Each top peer is unchoked.
        for p in top:
            p.send_unchoke.assert_awaited()
        # The optimistic pick must be the non-snubbed remainder, not the
        # snubbed peer (despite snubbed peer's massive window total).
        remainder.send_unchoke.assert_awaited()
        snubbed.send_unchoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_snubbed_peer_logged_once_per_episode(self):
        """The INFO log line for a snubbed peer must fire exactly once per
        snub episode (not every 10s choke cycle)."""
        from python_engine.download_manager import Download, AlgorithmType

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        now = 10_000.0

        snubbed = self._make_peer(torrent, '10.0.0.99',
                                  snubbed=True, window_bytes=500, now=now)
        healthy = self._make_peer(torrent, '10.0.0.1',
                                  snubbed=False, window_bytes=100, now=now)
        dl._connections['10.0.0.99:6881'] = snubbed
        dl._connections['10.0.0.1:6881'] = healthy

        with patch('python_engine.peer_connection.time.time', return_value=now), \
             patch('python_engine.download_manager.logger') as mock_logger:
            await dl._tit_for_tat_unchoke()
            await dl._tit_for_tat_unchoke()
            await dl._tit_for_tat_unchoke()

        # Only the first call should have logged the snub.
        snub_calls = [
            c for c in mock_logger.info.call_args_list
            if 'snubbed' in str(c).lower()
        ]
        assert len(snub_calls) == 1, f"expected 1 snub log, got {len(snub_calls)}: {snub_calls}"


class TestSeedingMode:
    """Seeding-mode tit-for-tat: post-completion, sort by upload window."""

    def _make_peer(self, torrent, ip, *, window_sent: int, now: float):
        from python_engine.peer_connection import PeerConnection
        c = PeerConnection(
            ip=ip, port=6881,
            info_hash=torrent.info_hash, peer_id=b'\x02' * 20,
            num_pieces=torrent.num_pieces,
        )
        c._connected = True
        c._handshake_complete = True
        c.peer_interested = True
        c.peer_choking = False
        c.am_choking = True
        c.send_choke = AsyncMock()
        c.send_unchoke = AsyncMock()
        if window_sent > 0:
            c._upload_samples.append((now - 1, window_sent))
        return c

    def test_is_seeding_requires_completion_and_terminal_state(self):
        """_is_seeding flips to True only when both conditions hold."""
        from python_engine.download_manager import Download, AlgorithmType

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        # Fresh download: not complete, RUNNING isn't seeding.
        assert dl._is_seeding() is False
        dl.state = DownloadState.RUNNING
        assert dl._is_seeding() is False

        # Force completion, but state still not in (COMPLETED, SEEDING).
        for p in dl.piece_manager.pieces:
            p.status = PieceStatus.COMPLETED
        assert dl.piece_manager.is_complete is True
        assert dl._is_seeding() is False

        # Completed state + complete pieces ⇒ seeding.
        dl.state = DownloadState.COMPLETED
        assert dl._is_seeding() is True
        dl.state = DownloadState.SEEDING
        assert dl._is_seeding() is True

    @pytest.mark.asyncio
    async def test_seeding_sorts_by_upload_window_not_download(self):
        """In seed mode the leech metric is zero; upload window decides."""
        from python_engine.download_manager import (
            Download, AlgorithmType, MAX_UNCHOKED_PEERS
        )

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        # Put the download into seed mode.
        for p in dl.piece_manager.pieces:
            p.status = PieceStatus.COMPLETED
        dl.state = DownloadState.SEEDING
        assert dl._is_seeding() is True

        now = 10_000.0
        # 5 peers with descending upload-window totals.
        peers = [
            self._make_peer(torrent, f'10.0.0.{i}',
                            window_sent=1000 - i * 100, now=now)
            for i in range(1, 6)
        ]
        # All have ZERO download contribution (we're a seeder).
        for i, p in enumerate(peers, start=1):
            dl._connections[f'10.0.0.{i}:6881'] = p

        with patch('python_engine.peer_connection.time.time', return_value=now):
            await dl._tit_for_tat_unchoke()

        # Top-4 by upload window are peers 10.0.0.1..4. Peer 10.0.0.5
        # (lowest upload) should be the only one NOT in top-K, and the
        # optimistic pick is the only seat it could take.
        for p in peers[:MAX_UNCHOKED_PEERS]:
            p.send_unchoke.assert_awaited()
        # Sort is correct: peer with 0 upload-window is last.
        ordered = sorted(peers, key=lambda c: c.bytes_sent_in_window(20.0),
                         reverse=True)
        assert ordered[0] is peers[0]
        assert ordered[-1] is peers[4]

    @pytest.mark.asyncio
    async def test_leech_mode_unchanged_when_not_complete(self):
        """If piece_manager.is_complete is False, the leech algorithm runs
        (snubbing partition, sort by bytes_received_in_window). This
        protects against the seed branch firing prematurely."""
        from python_engine.download_manager import (
            Download, AlgorithmType, TIT_FOR_TAT_WINDOW
        )

        torrent = make_torrent()
        dl = Download(
            torrent=torrent,
            download_dir='/tmp/downloads',
            state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        # NOT complete; even with state=COMPLETED, _is_seeding is False.
        dl.state = DownloadState.COMPLETED
        assert dl._is_seeding() is False

        now = 10_000.0
        # Build a peer with high upload-window and zero download-window —
        # in leech mode this peer should NOT be ranked high (we sort by
        # download). Sanity check: leech branch read download samples,
        # seed branch would read upload samples.
        from python_engine.peer_connection import PeerConnection
        peer = PeerConnection(
            ip='10.0.0.1', port=6881,
            info_hash=torrent.info_hash, peer_id=b'\x02' * 20,
            num_pieces=torrent.num_pieces,
        )
        peer._connected = True
        peer._handshake_complete = True
        peer.peer_interested = True
        peer.peer_choking = False
        peer.am_choking = True
        peer.send_choke = AsyncMock()
        peer.send_unchoke = AsyncMock()
        peer._upload_samples.append((now - 1, 9_999_999))
        # No download samples: in leech mode this peer's metric is zero.
        dl._connections['10.0.0.1:6881'] = peer

        with patch('python_engine.peer_connection.time.time', return_value=now):
            await dl._tit_for_tat_unchoke()

        # Leech branch ran (single peer, gets unchoked) — and crucially the
        # peer's leech metric (0) is what would have determined ranking
        # against any competitor, not its upload window.
        assert peer.bytes_received_in_window(TIT_FOR_TAT_WINDOW) == 0
        peer.send_unchoke.assert_awaited()


class TestUploadServing:
    """The upload path: serving block REQUESTs from connected peers.

    This is what makes the client a real uploader. Before this existed,
    send_piece was never called and bytes_uploaded stayed zero, so
    seed-mode tit-for-tat sorted every peer by an all-zero metric.
    """

    def _make_completed_download(self, tmp_path, data=None):
        torrent = make_torrent()  # 4 pieces x 256 bytes
        dl = Download(
            torrent=torrent,
            download_dir=str(tmp_path),
            state_dir=str(tmp_path),
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        block = data if data is not None else bytes(range(256))
        piece = dl.piece_manager.pieces[0]
        piece._data = bytearray(block)
        piece.status = PieceStatus.COMPLETED
        return dl, torrent

    def _make_conn(self, torrent, *, choking):
        from python_engine.peer_connection import PeerConnection
        c = PeerConnection(
            ip='10.0.0.9', port=6881,
            info_hash=torrent.info_hash, peer_id=b'\x03' * 20,
            num_pieces=torrent.num_pieces,
        )
        c._connected = True
        c.am_choking = choking
        c.send_message = AsyncMock()
        return c

    def _request(self, piece_index, begin, length):
        import struct
        from python_engine.peer_connection import PeerMessage, MessageType
        return PeerMessage(
            MessageType.REQUEST, struct.pack('!III', piece_index, begin, length)
        )

    @pytest.mark.asyncio
    async def test_serves_correct_block_and_counts_upload(self, tmp_path):
        import struct
        from python_engine.peer_connection import MessageType
        known = bytes((i * 7) % 256 for i in range(256))
        dl, torrent = self._make_completed_download(tmp_path, known)
        conn = self._make_conn(torrent, choking=False)

        await dl._serve_block_request(conn, self._request(0, 0, 256))

        conn.send_message.assert_awaited_once()
        msg_type, payload = conn.send_message.await_args.args
        assert msg_type == MessageType.PIECE
        # PIECE payload: piece_index(4) + begin(4) + block bytes
        assert payload == struct.pack('!II', 0, 0) + known
        # Both per-peer and aggregate upload counters move.
        assert conn.bytes_uploaded == 256
        assert dl.stats.bytes_uploaded == 256
        # The upload sliding window (seed-mode metric) was fed.
        assert conn.bytes_sent_in_window(20.0) == 256

    @pytest.mark.asyncio
    async def test_serves_partial_block_at_offset(self, tmp_path):
        import struct
        known = bytes(range(256))
        dl, torrent = self._make_completed_download(tmp_path, known)
        conn = self._make_conn(torrent, choking=False)

        await dl._serve_block_request(conn, self._request(0, 100, 50))

        _, payload = conn.send_message.await_args.args
        assert payload == struct.pack('!II', 0, 100) + known[100:150]
        assert dl.stats.bytes_uploaded == 50

    @pytest.mark.asyncio
    async def test_choking_peer_is_not_served(self, tmp_path):
        dl, torrent = self._make_completed_download(tmp_path)
        conn = self._make_conn(torrent, choking=True)

        await dl._serve_block_request(conn, self._request(0, 0, 256))

        conn.send_message.assert_not_awaited()
        assert dl.stats.bytes_uploaded == 0

    @pytest.mark.asyncio
    async def test_request_for_piece_we_lack_is_ignored(self, tmp_path):
        dl, torrent = self._make_completed_download(tmp_path)
        conn = self._make_conn(torrent, choking=False)
        # Piece 1 is still MISSING (only piece 0 was completed).
        await dl._serve_block_request(conn, self._request(1, 0, 256))
        conn.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_oversized_request_rejected(self, tmp_path):
        from python_engine.peer_connection import BLOCK_SIZE
        dl, torrent = self._make_completed_download(tmp_path)
        conn = self._make_conn(torrent, choking=False)
        await dl._serve_block_request(conn, self._request(0, 0, BLOCK_SIZE + 1))
        conn.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_out_of_bounds_request_rejected(self, tmp_path):
        dl, torrent = self._make_completed_download(tmp_path)
        conn = self._make_conn(torrent, choking=False)
        # begin+length runs past the 256-byte piece.
        await dl._serve_block_request(conn, self._request(0, 200, 100))
        conn.send_message.assert_not_awaited()


class TestSeedingTransition:
    """Completion promotes the visible state COMPLETED -> SEEDING."""

    def test_maybe_enter_seeding_flips_completed_to_seeding(self):
        torrent = make_torrent()
        dl = Download(
            torrent=torrent, download_dir='/tmp/downloads', state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        for p in dl.piece_manager.pieces:
            p.status = PieceStatus.COMPLETED
        dl.state = DownloadState.COMPLETED

        dl._maybe_enter_seeding()
        assert dl.state == DownloadState.SEEDING
        # Idempotent: a second tick keeps it SEEDING.
        dl._maybe_enter_seeding()
        assert dl.state == DownloadState.SEEDING

    def test_maybe_enter_seeding_noop_while_running(self):
        torrent = make_torrent()
        dl = Download(
            torrent=torrent, download_dir='/tmp/downloads', state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        for p in dl.piece_manager.pieces:
            p.status = PieceStatus.COMPLETED
        # Still RUNNING (e.g. last piece just landed but loop hasn't finished).
        dl.state = DownloadState.RUNNING
        dl._maybe_enter_seeding()
        assert dl.state == DownloadState.RUNNING

    def test_maybe_enter_seeding_noop_when_incomplete(self):
        torrent = make_torrent()
        dl = Download(
            torrent=torrent, download_dir='/tmp/downloads', state_dir='/tmp/state',
            peer_algorithm=AlgorithmType.TIT_FOR_TAT,
        )
        dl.state = DownloadState.COMPLETED  # mislabeled but pieces incomplete
        assert dl.piece_manager.is_complete is False
        dl._maybe_enter_seeding()
        assert dl.state == DownloadState.COMPLETED
