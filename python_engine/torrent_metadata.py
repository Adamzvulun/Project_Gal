"""
Torrent metadata module.

Reads .torrent files, decodes the Bencode content, and provides access
to torrent metadata including the info_hash, piece hashes, file names, and sizes.
"""

import hashlib
import os
from typing import List, Optional, Tuple

from . import bencode


class TorrentMetadataError(Exception):
    """Raised when there is an error reading or parsing torrent metadata."""
    pass


class FileInfo:
    """Information about a single file in a torrent."""

    def __init__(self, path: str, size: int):
        self.path = path
        self.size = size

    def __repr__(self):
        return f"FileInfo(path={self.path!r}, size={self.size})"


class TorrentMetadata:
    """Parses and stores metadata from a .torrent file.

    Attributes:
        announce: The tracker URL.
        announce_list: Optional list of backup tracker URLs.
        piece_length: The size of each piece in bytes.
        pieces: List of SHA-1 hashes (20 bytes each), one per piece.
        files: List of FileInfo objects describing the files.
        name: The suggested name for the file or directory.
        info_hash: SHA-1 hash of the bencoded info dictionary (20 bytes).
        total_size: Total size of all files combined.
        num_pieces: Number of pieces in the torrent.
        comment: Optional comment from the torrent creator.
        created_by: Optional creator string.
        creation_date: Optional creation timestamp.
    """

    def __init__(self, torrent_path: Optional[str] = None, torrent_data: Optional[bytes] = None):
        """Initialize TorrentMetadata from a file path or raw bytes.

        Args:
            torrent_path: Path to a .torrent file.
            torrent_data: Raw bytes of a .torrent file.

        Raises:
            TorrentMetadataError: If the torrent data is invalid.
        """
        if torrent_path is not None:
            if not os.path.exists(torrent_path):
                raise TorrentMetadataError(f"File not found: {torrent_path}")
            with open(torrent_path, 'rb') as f:
                raw_data = f.read()
        elif torrent_data is not None:
            raw_data = torrent_data
        else:
            raise TorrentMetadataError("Must provide either torrent_path or torrent_data")

        try:
            self._metadata = bencode.decode(raw_data)
        except bencode.BencodeDecodeError as e:
            raise TorrentMetadataError(f"Failed to decode torrent file: {e}")

        if not isinstance(self._metadata, dict):
            raise TorrentMetadataError("Torrent file must contain a dictionary")

        self._parse_metadata()

    def _parse_metadata(self):
        """Parse the decoded torrent metadata dictionary."""
        # Announce URL (required)
        if b'announce' not in self._metadata:
            raise TorrentMetadataError("Missing 'announce' field")
        self.announce = self._metadata[b'announce'].decode('utf-8')

        # Announce list (optional)
        self.announce_list = []
        if b'announce-list' in self._metadata:
            for tier in self._metadata[b'announce-list']:
                tier_urls = [url.decode('utf-8') for url in tier]
                self.announce_list.append(tier_urls)

        # Info dictionary (required)
        if b'info' not in self._metadata:
            raise TorrentMetadataError("Missing 'info' dictionary")
        info = self._metadata[b'info']
        if not isinstance(info, dict):
            raise TorrentMetadataError("'info' must be a dictionary")

        # Compute info_hash: SHA-1 of the re-encoded info dictionary
        info_encoded = bencode.encode(info)
        self.info_hash = hashlib.sha1(info_encoded).digest()

        # Piece length (required)
        if b'piece length' not in info:
            raise TorrentMetadataError("Missing 'piece length' in info")
        self.piece_length = info[b'piece length']

        # Pieces - concatenated SHA-1 hashes (required)
        if b'pieces' not in info:
            raise TorrentMetadataError("Missing 'pieces' in info")
        pieces_data = info[b'pieces']
        if len(pieces_data) % 20 != 0:
            raise TorrentMetadataError(
                f"Pieces data length ({len(pieces_data)}) is not a multiple of 20"
            )
        self.pieces = [pieces_data[i:i + 20] for i in range(0, len(pieces_data), 20)]
        self.num_pieces = len(self.pieces)

        # Name (required)
        if b'name' not in info:
            raise TorrentMetadataError("Missing 'name' in info")
        self.name = info[b'name'].decode('utf-8')

        # Parse files
        self.files = []
        if b'files' in info:
            # Multi-file mode
            for file_dict in info[b'files']:
                path_parts = [p.decode('utf-8') for p in file_dict[b'path']]
                file_path = os.path.join(self.name, *path_parts)
                file_size = file_dict[b'length']
                self.files.append(FileInfo(file_path, file_size))
        else:
            # Single-file mode
            if b'length' not in info:
                raise TorrentMetadataError("Missing 'length' in single-file info")
            self.files.append(FileInfo(self.name, info[b'length']))

        self.total_size = sum(f.size for f in self.files)

        # Optional fields
        self.comment = None
        if b'comment' in self._metadata:
            self.comment = self._metadata[b'comment'].decode('utf-8', errors='replace')

        self.created_by = None
        if b'created by' in self._metadata:
            self.created_by = self._metadata[b'created by'].decode('utf-8', errors='replace')

        self.creation_date = None
        if b'creation date' in self._metadata:
            self.creation_date = self._metadata[b'creation date']

    def info_hash_hex(self) -> str:
        """Return the info_hash as a hex string."""
        return self.info_hash.hex()

    def info_hash_urlencoded(self) -> str:
        """Return the info_hash URL-encoded for tracker requests."""
        from urllib.parse import quote
        return quote(self.info_hash, safe='')

    def get_piece_hash(self, piece_index: int) -> bytes:
        """Get the expected SHA-1 hash for a given piece index.

        Args:
            piece_index: Zero-based index of the piece.

        Returns:
            20-byte SHA-1 hash.

        Raises:
            IndexError: If piece_index is out of range.
        """
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range (0-{self.num_pieces - 1})")
        return self.pieces[piece_index]

    def get_piece_length(self, piece_index: int) -> int:
        """Get the actual length of a specific piece.

        The last piece may be shorter than piece_length.

        Args:
            piece_index: Zero-based index of the piece.

        Returns:
            Length in bytes.
        """
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range (0-{self.num_pieces - 1})")
        if piece_index == self.num_pieces - 1:
            # Last piece may be shorter
            remainder = self.total_size % self.piece_length
            return remainder if remainder != 0 else self.piece_length
        return self.piece_length

    def get_file_offset(self, piece_index: int) -> List[Tuple[str, int, int]]:
        """Get the file(s) and offsets that a piece maps to.

        Args:
            piece_index: Zero-based index of the piece.

        Returns:
            List of (file_path, offset_in_file, length) tuples.
        """
        piece_start = piece_index * self.piece_length
        piece_len = self.get_piece_length(piece_index)
        piece_end = piece_start + piece_len

        result = []
        file_offset = 0
        for f in self.files:
            file_start = file_offset
            file_end = file_offset + f.size

            if file_start >= piece_end:
                break
            if file_end <= piece_start:
                file_offset = file_end
                continue

            # Overlap
            overlap_start = max(piece_start, file_start)
            overlap_end = min(piece_end, file_end)
            offset_in_file = overlap_start - file_start
            length = overlap_end - overlap_start

            result.append((f.path, offset_in_file, length))
            file_offset = file_end

        return result

    def __repr__(self):
        return (
            f"TorrentMetadata(name={self.name!r}, "
            f"size={self.total_size}, "
            f"pieces={self.num_pieces}, "
            f"info_hash={self.info_hash_hex()})"
        )
