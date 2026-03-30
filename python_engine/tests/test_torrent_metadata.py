"""
Tests for the TorrentMetadata module.
"""

import hashlib
import pytest
from python_engine.bencode import encode
from python_engine.torrent_metadata import TorrentMetadata, TorrentMetadataError


def make_torrent_data(name=b'test.txt', length=1024, piece_length=256,
                      announce=b'http://tracker.example.com/announce'):
    """Helper to create valid torrent metadata bytes."""
    num_pieces = (length + piece_length - 1) // piece_length
    pieces = b'\x00' * (num_pieces * 20)  # Dummy SHA-1 hashes

    info = {
        b'length': length,
        b'name': name,
        b'piece length': piece_length,
        b'pieces': pieces,
    }

    torrent = {
        b'announce': announce,
        b'info': info,
    }

    return encode(torrent), info


class TestTorrentMetadata:
    def test_parse_single_file(self):
        data, info = make_torrent_data()
        tm = TorrentMetadata(torrent_data=data)

        assert tm.announce == 'http://tracker.example.com/announce'
        assert tm.name == 'test.txt'
        assert tm.total_size == 1024
        assert tm.piece_length == 256
        assert tm.num_pieces == 4
        assert len(tm.pieces) == 4
        assert len(tm.files) == 1
        assert tm.files[0].path == 'test.txt'
        assert tm.files[0].size == 1024

    def test_info_hash_computed(self):
        data, info = make_torrent_data()
        tm = TorrentMetadata(torrent_data=data)

        expected_hash = hashlib.sha1(encode(info)).digest()
        assert tm.info_hash == expected_hash
        assert len(tm.info_hash) == 20

    def test_info_hash_hex(self):
        data, _ = make_torrent_data()
        tm = TorrentMetadata(torrent_data=data)
        assert len(tm.info_hash_hex()) == 40

    def test_multi_file_torrent(self):
        info = {
            b'name': b'my_folder',
            b'piece length': 256,
            b'pieces': b'\x00' * 40,  # 2 pieces
            b'files': [
                {b'length': 300, b'path': [b'file1.txt']},
                {b'length': 200, b'path': [b'subdir', b'file2.txt']},
            ]
        }
        torrent = {
            b'announce': b'http://tracker.example.com/announce',
            b'info': info,
        }
        data = encode(torrent)
        tm = TorrentMetadata(torrent_data=data)

        assert tm.name == 'my_folder'
        assert tm.total_size == 500
        assert len(tm.files) == 2
        assert tm.files[1].path == 'my_folder/subdir/file2.txt'

    def test_get_piece_length_last_piece(self):
        data, _ = make_torrent_data(length=1000, piece_length=256)
        tm = TorrentMetadata(torrent_data=data)

        # 1000 / 256 = 3 full pieces + 1 partial (232 bytes)
        assert tm.num_pieces == 4
        assert tm.get_piece_length(0) == 256
        assert tm.get_piece_length(3) == 1000 - 3 * 256  # 232

    def test_get_piece_hash(self):
        data, _ = make_torrent_data()
        tm = TorrentMetadata(torrent_data=data)

        h = tm.get_piece_hash(0)
        assert len(h) == 20

    def test_get_piece_hash_out_of_range(self):
        data, _ = make_torrent_data()
        tm = TorrentMetadata(torrent_data=data)

        with pytest.raises(IndexError):
            tm.get_piece_hash(100)

    def test_missing_announce(self):
        info = {
            b'length': 100,
            b'name': b'test',
            b'piece length': 100,
            b'pieces': b'\x00' * 20,
        }
        data = encode({b'info': info})
        with pytest.raises(TorrentMetadataError, match="announce"):
            TorrentMetadata(torrent_data=data)

    def test_missing_info(self):
        data = encode({b'announce': b'http://example.com'})
        with pytest.raises(TorrentMetadataError, match="info"):
            TorrentMetadata(torrent_data=data)

    def test_invalid_bencode(self):
        with pytest.raises(TorrentMetadataError):
            TorrentMetadata(torrent_data=b'not valid bencode')

    def test_file_not_found(self):
        with pytest.raises(TorrentMetadataError, match="not found"):
            TorrentMetadata(torrent_path='/nonexistent/file.torrent')

    def test_no_arguments(self):
        with pytest.raises(TorrentMetadataError):
            TorrentMetadata()

    def test_optional_fields(self):
        info = {
            b'length': 100,
            b'name': b'test',
            b'piece length': 100,
            b'pieces': b'\x00' * 20,
        }
        torrent = {
            b'announce': b'http://example.com',
            b'comment': b'A test torrent',
            b'created by': b'TestSuite',
            b'creation date': 1234567890,
            b'info': info,
        }
        data = encode(torrent)
        tm = TorrentMetadata(torrent_data=data)

        assert tm.comment == 'A test torrent'
        assert tm.created_by == 'TestSuite'
        assert tm.creation_date == 1234567890

    def test_repr(self):
        data, _ = make_torrent_data()
        tm = TorrentMetadata(torrent_data=data)
        r = repr(tm)
        assert 'test.txt' in r
        assert '1024' in r
