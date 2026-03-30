"""
Tests for the Bencode encoder/decoder module.
"""

import pytest
from python_engine.bencode import (
    encode, decode, decode_partial,
    BencodeDecodeError, BencodeEncodeError
)


class TestEncodeIntegers:
    def test_encode_zero(self):
        assert encode(0) == b'i0e'

    def test_encode_positive(self):
        assert encode(42) == b'i42e'

    def test_encode_negative(self):
        assert encode(-42) == b'i-42e'

    def test_encode_large_number(self):
        assert encode(1234567890) == b'i1234567890e'


class TestEncodeStrings:
    def test_encode_empty_bytes(self):
        assert encode(b'') == b'0:'

    def test_encode_bytes(self):
        assert encode(b'hello') == b'5:hello'

    def test_encode_string(self):
        assert encode('hello') == b'5:hello'

    def test_encode_unicode_string(self):
        result = encode('café')
        # 'café' is 5 bytes in UTF-8
        assert result == b'5:caf\xc3\xa9'


class TestEncodeLists:
    def test_encode_empty_list(self):
        assert encode([]) == b'le'

    def test_encode_simple_list(self):
        assert encode([b'hello', 42]) == b'l5:helloi42ee'

    def test_encode_nested_list(self):
        assert encode([[1, 2], [3]]) == b'lli1ei2eeli3eee'


class TestEncodeDicts:
    def test_encode_empty_dict(self):
        assert encode({}) == b'de'

    def test_encode_simple_dict(self):
        result = encode({b'key': b'value'})
        assert result == b'd3:key5:valuee'

    def test_encode_sorted_keys(self):
        result = encode({b'b': 2, b'a': 1})
        assert result == b'd1:ai1e1:bi2ee'

    def test_encode_string_keys(self):
        result = encode({'key': 'value'})
        assert result == b'd3:key5:valuee'

    def test_encode_nested_dict(self):
        result = encode({b'info': {b'name': b'test'}})
        assert result == b'd4:infod4:name4:testee'


class TestDecodeIntegers:
    def test_decode_zero(self):
        assert decode(b'i0e') == 0

    def test_decode_positive(self):
        assert decode(b'i42e') == 42

    def test_decode_negative(self):
        assert decode(b'i-42e') == -42

    def test_decode_leading_zero_rejected(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'i042e')

    def test_decode_negative_zero_rejected(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'i-0e')

    def test_decode_empty_integer(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'ie')


class TestDecodeStrings:
    def test_decode_empty_string(self):
        assert decode(b'0:') == b''

    def test_decode_simple_string(self):
        assert decode(b'5:hello') == b'hello'

    def test_decode_binary_data(self):
        assert decode(b'4:\x00\x01\x02\x03') == b'\x00\x01\x02\x03'

    def test_decode_truncated_string(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'10:hello')


class TestDecodeLists:
    def test_decode_empty_list(self):
        assert decode(b'le') == []

    def test_decode_simple_list(self):
        assert decode(b'l5:helloi42ee') == [b'hello', 42]

    def test_decode_nested_list(self):
        result = decode(b'lli1ei2eeli3eee')
        assert result == [[1, 2], [3]]


class TestDecodeDicts:
    def test_decode_empty_dict(self):
        assert decode(b'de') == {}

    def test_decode_simple_dict(self):
        result = decode(b'd3:key5:valuee')
        assert result == {b'key': b'value'}

    def test_decode_nested_dict(self):
        result = decode(b'd4:infod4:name4:testee')
        assert result == {b'info': {b'name': b'test'}}

    def test_decode_unsorted_keys_rejected(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'd1:bi2e1:ai1ee')


class TestRoundTrip:
    """Test that encode(decode(x)) == x and decode(encode(x)) == x."""

    def test_roundtrip_integer(self):
        assert decode(encode(42)) == 42

    def test_roundtrip_string(self):
        assert decode(encode(b'hello')) == b'hello'

    def test_roundtrip_list(self):
        data = [b'hello', 42, [b'nested']]
        assert decode(encode(data)) == data

    def test_roundtrip_dict(self):
        data = {b'a': 1, b'b': [2, 3], b'c': {b'd': b'e'}}
        assert decode(encode(data)) == data

    def test_roundtrip_complex(self):
        data = {
            b'announce': b'http://tracker.example.com/announce',
            b'info': {
                b'length': 1024,
                b'name': b'test.txt',
                b'piece length': 256,
                b'pieces': b'\x00' * 80,  # 4 pieces
            }
        }
        assert decode(encode(data)) == data


class TestDecodePartial:
    def test_partial_decode(self):
        data = b'i42e5:hello'
        value, remaining = decode_partial(data)
        assert value == 42
        assert remaining == b'5:hello'


class TestEdgeCases:
    def test_encode_unsupported_type(self):
        with pytest.raises(BencodeEncodeError):
            encode(3.14)

    def test_decode_empty(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'')

    def test_decode_non_bytes(self):
        with pytest.raises(BencodeDecodeError):
            decode("not bytes")

    def test_decode_trailing_data(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'i42eextra')

    def test_decode_invalid_prefix(self):
        with pytest.raises(BencodeDecodeError):
            decode(b'x')
