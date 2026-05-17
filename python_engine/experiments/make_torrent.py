"""
Tiny helper to build a single-file .torrent from a payload on disk.

The output bencoded structure mirrors BEP-3:
    {
        b'announce': <tracker_url>,
        b'info': {
            b'name': <filename>,
            b'piece length': <piece_length>,
            b'length': <total_size>,
            b'pieces': <concatenated SHA-1 of each piece>,
        }
    }

The same `python_engine.bencode` module the engine uses for parsing
also performs the encoding here, so info_hash recomputed from the
parsed metadata matches by construction (canonical key order).
"""

from __future__ import annotations

import hashlib
import os
from typing import Tuple

from .. import bencode


def make_torrent_bytes(
    payload_path: str,
    announce_url: str,
    piece_length: int = 256 * 1024,
    name: str | None = None,
) -> Tuple[bytes, bytes]:
    """Build a .torrent file for ``payload_path``.

    Args:
        payload_path: Path to the data file the .torrent describes.
        announce_url: HTTP tracker announce URL to embed.
        piece_length: Size in bytes of each piece. Default 256 KB.
        name: Optional override for the in-torrent file name.

    Returns:
        Tuple of (torrent_bytes, info_hash). ``info_hash`` is 20 bytes
        (SHA-1 of the bencoded info dict).
    """
    if not os.path.isfile(payload_path):
        raise FileNotFoundError(payload_path)

    file_size = os.path.getsize(payload_path)
    if file_size == 0:
        raise ValueError("Payload is empty; cannot build a torrent for 0-byte file")

    piece_hashes = bytearray()
    with open(payload_path, "rb") as f:
        while True:
            chunk = f.read(piece_length)
            if not chunk:
                break
            piece_hashes.extend(hashlib.sha1(chunk).digest())

    info = {
        b"name": (name or os.path.basename(payload_path)).encode("utf-8"),
        b"piece length": piece_length,
        b"length": file_size,
        b"pieces": bytes(piece_hashes),
    }
    info_encoded = bencode.encode(info)
    info_hash = hashlib.sha1(info_encoded).digest()

    torrent_dict = {
        b"announce": announce_url.encode("utf-8"),
        b"info": info,
    }
    return bencode.encode(torrent_dict), info_hash
