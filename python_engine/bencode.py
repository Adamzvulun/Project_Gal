"""
Bencode encoder/decoder module.

Bencode is the encoding format used in .torrent files and tracker communication.
Supported types:
  - Integers:     i<number>e       (e.g., i42e)
  - Strings:      <length>:<data>  (e.g., 5:hello)
  - Lists:        l<items>e        (e.g., l5:helloi42ee)
  - Dictionaries: d<key><value>e   (keys must be byte strings in sorted order)
"""

from typing import Any, Tuple


class BencodeDecodeError(Exception):
    """Raised when decoding invalid bencode data."""
    pass


class BencodeEncodeError(Exception):
    """Raised when encoding unsupported types."""
    pass


def encode(data: Any) -> bytes:
    """Encode a Python object into bencode format.

    Args:
        data: Python object to encode (int, bytes, str, list, dict).

    Returns:
        Bencoded bytes.

    Raises:
        BencodeEncodeError: If the data type is not supported.
    """
    if isinstance(data, int) and not isinstance(data, bool):
        return _encode_int(data)
    elif isinstance(data, bytes):
        return _encode_bytes(data)
    elif isinstance(data, str):
        return _encode_bytes(data.encode('utf-8'))
    elif isinstance(data, list):
        return _encode_list(data)
    elif isinstance(data, dict):
        return _encode_dict(data)
    else:
        raise BencodeEncodeError(f"Unsupported type: {type(data)}")


def decode(data: bytes) -> Any:
    """Decode bencoded data into a Python object.

    Args:
        data: Bencoded bytes to decode.

    Returns:
        Decoded Python object.

    Raises:
        BencodeDecodeError: If the data is not valid bencode.
    """
    if not isinstance(data, bytes):
        raise BencodeDecodeError("Input must be bytes")
    if len(data) == 0:
        raise BencodeDecodeError("Empty input")

    result, remaining = _decode_next(data)
    if remaining:
        raise BencodeDecodeError(f"Unexpected data after decoded value: {remaining!r}")
    return result


def decode_partial(data: bytes) -> Tuple[Any, bytes]:
    """Decode the first bencoded value and return remaining bytes.

    Useful for parsing streams of bencoded data.

    Args:
        data: Bencoded bytes.

    Returns:
        Tuple of (decoded value, remaining bytes).
    """
    if not isinstance(data, bytes):
        raise BencodeDecodeError("Input must be bytes")
    if len(data) == 0:
        raise BencodeDecodeError("Empty input")
    return _decode_next(data)


# -- Encoding helpers --

def _encode_int(value: int) -> bytes:
    return b'i' + str(value).encode('ascii') + b'e'


def _encode_bytes(value: bytes) -> bytes:
    return str(len(value)).encode('ascii') + b':' + value


def _encode_list(value: list) -> bytes:
    result = b'l'
    for item in value:
        result += encode(item)
    result += b'e'
    return result


def _encode_dict(value: dict) -> bytes:
    result = b'd'
    # Keys must be byte strings, sorted lexicographically
    sorted_keys = sorted(value.keys(), key=lambda k: k if isinstance(k, bytes) else k.encode('utf-8'))
    for key in sorted_keys:
        if isinstance(key, str):
            result += _encode_bytes(key.encode('utf-8'))
        elif isinstance(key, bytes):
            result += _encode_bytes(key)
        else:
            raise BencodeEncodeError(f"Dictionary keys must be strings or bytes, got {type(key)}")
        result += encode(value[key])
    result += b'e'
    return result


# -- Decoding helpers --

def _decode_next(data: bytes) -> Tuple[Any, bytes]:
    if len(data) == 0:
        raise BencodeDecodeError("Unexpected end of data")

    first_byte = data[0:1]

    if first_byte == b'i':
        return _decode_int(data)
    elif first_byte == b'l':
        return _decode_list(data)
    elif first_byte == b'd':
        return _decode_dict(data)
    elif first_byte.isdigit():
        return _decode_bytes(data)
    else:
        raise BencodeDecodeError(f"Invalid bencode prefix: {first_byte!r}")


def _decode_int(data: bytes) -> Tuple[int, bytes]:
    # Format: i<number>e
    end_idx = data.index(b'e')
    if end_idx == -1:
        raise BencodeDecodeError("Unterminated integer")

    num_str = data[1:end_idx]
    if not num_str:
        raise BencodeDecodeError("Empty integer value")

    # Validate: no leading zeros (except i0e)
    if len(num_str) > 1 and num_str[0:1] == b'0':
        raise BencodeDecodeError(f"Leading zeros in integer: {num_str!r}")
    if num_str == b'-0':
        raise BencodeDecodeError("Negative zero is not allowed")
    if len(num_str) > 1 and num_str[0:1] == b'-' and num_str[1:2] == b'0':
        raise BencodeDecodeError(f"Leading zeros in negative integer: {num_str!r}")

    try:
        value = int(num_str)
    except ValueError:
        raise BencodeDecodeError(f"Invalid integer: {num_str!r}")

    return value, data[end_idx + 1:]


def _decode_bytes(data: bytes) -> Tuple[bytes, bytes]:
    # Format: <length>:<data>
    colon_idx = data.index(b':')
    if colon_idx == -1:
        raise BencodeDecodeError("Missing colon in byte string")

    try:
        length = int(data[:colon_idx])
    except ValueError:
        raise BencodeDecodeError(f"Invalid string length: {data[:colon_idx]!r}")

    if length < 0:
        raise BencodeDecodeError(f"Negative string length: {length}")

    start = colon_idx + 1
    end = start + length

    if end > len(data):
        raise BencodeDecodeError(f"String length {length} exceeds available data")

    return data[start:end], data[end:]


def _decode_list(data: bytes) -> Tuple[list, bytes]:
    # Format: l<items>e
    result = []
    data = data[1:]  # skip 'l'

    while data and data[0:1] != b'e':
        item, data = _decode_next(data)
        result.append(item)

    if not data:
        raise BencodeDecodeError("Unterminated list")

    return result, data[1:]  # skip 'e'


def _decode_dict(data: bytes) -> Tuple[dict, bytes]:
    # Format: d<key><value>...e
    result = {}
    data = data[1:]  # skip 'd'
    prev_key = None

    while data and data[0:1] != b'e':
        # Keys must be byte strings
        key, data = _decode_bytes(data)
        value, data = _decode_next(data)

        # Verify sorted order
        if prev_key is not None and key <= prev_key:
            raise BencodeDecodeError(f"Dictionary keys not in sorted order: {prev_key!r} >= {key!r}")
        prev_key = key

        result[key] = value

    if not data:
        raise BencodeDecodeError("Unterminated dictionary")

    return result, data[1:]  # skip 'e'
