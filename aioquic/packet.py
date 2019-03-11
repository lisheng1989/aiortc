from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum

from .rangeset import RangeSet
from .tls import (BufferReadError, pull_bytes, pull_uint8, pull_uint16,
                  pull_uint32, pull_uint64, push_bytes, push_uint8,
                  push_uint16, push_uint32, push_uint64)

PACKET_LONG_HEADER = 0x80
PACKET_FIXED_BIT = 0x40

PACKET_TYPE_INITIAL = PACKET_LONG_HEADER | PACKET_FIXED_BIT | 0x00
PACKET_TYPE_0RTT = PACKET_LONG_HEADER | PACKET_FIXED_BIT | 0x10
PACKET_TYPE_HANDSHAKE = PACKET_LONG_HEADER | PACKET_FIXED_BIT | 0x20
PACKET_TYPE_RETRY = PACKET_LONG_HEADER | PACKET_FIXED_BIT | 0x30
PACKET_TYPE_MASK = 0xf0

PROTOCOL_VERSION_DRAFT_17 = 0xff000011  # draft 17

UINT_VAR_FORMATS = [
    (pull_uint8, push_uint8, 0x3f),
    (pull_uint16, push_uint16, 0x3fff),
    (pull_uint32, push_uint32, 0x3fffffff),
    (pull_uint64, push_uint64, 0x3fffffffffffffff),
]


@dataclass
class QuicHeader:
    version: int
    packet_type: int
    destination_cid: bytes
    source_cid: bytes
    token: bytes = b''
    rest_length: int = 0


def decode_cid_length(length):
    return length + 3 if length else 0


def encode_cid_length(length):
    return length - 3 if length else 0


def is_long_header(first_byte):
    return bool(first_byte & PACKET_LONG_HEADER)


def pull_uint_var(buf):
    """
    Pull a QUIC variable-length unsigned integer.
    """
    try:
        kind = buf._data[buf._pos] // 64
    except IndexError:
        raise BufferReadError
    pull, push, mask = UINT_VAR_FORMATS[kind]
    return pull(buf) & mask


def push_uint_var(buf, value):
    """
    Push a QUIC variable-length unsigned integer.
    """
    for i, (pull, push, mask) in enumerate(UINT_VAR_FORMATS):
        if value <= mask:
            start = buf._pos
            push(buf, value)
            buf._data[start] |= i * 64
            return
    raise ValueError('Integer is too big for a variable-length integer')


def pull_quic_header(buf, host_cid_length=None):
    first_byte = pull_uint8(buf)
    if not (first_byte & PACKET_FIXED_BIT):
        raise ValueError('Packet fixed bit is zero')

    token = b''
    if is_long_header(first_byte):
        version = pull_uint32(buf)
        cid_lengths = pull_uint8(buf)

        destination_cid_length = decode_cid_length(cid_lengths // 16)
        destination_cid = pull_bytes(buf, destination_cid_length)

        source_cid_length = decode_cid_length(cid_lengths % 16)
        source_cid = pull_bytes(buf, source_cid_length)

        packet_type = first_byte & PACKET_TYPE_MASK
        if packet_type == PACKET_TYPE_INITIAL:
            token_length = pull_uint_var(buf)
            token = pull_bytes(buf, token_length)
        rest_length = pull_uint_var(buf)

        return QuicHeader(
            version=version,
            packet_type=packet_type,
            destination_cid=destination_cid,
            source_cid=source_cid,
            token=token,
            rest_length=rest_length)
    else:
        # short header packet
        packet_type = first_byte & PACKET_TYPE_MASK
        destination_cid = pull_bytes(buf, host_cid_length)
        return QuicHeader(
            version=0,
            packet_type=packet_type,
            destination_cid=destination_cid,
            source_cid=b'',
            token=b'',
            rest_length=buf.capacity - buf.tell())


def push_quic_header(buf, header):
    push_uint8(buf, header.packet_type)
    push_uint32(buf, header.version)
    push_uint8(buf,
               (encode_cid_length(len(header.destination_cid)) << 4) |
               encode_cid_length(len(header.source_cid)))
    push_bytes(buf, header.destination_cid)
    push_bytes(buf, header.source_cid)
    if (header.packet_type & PACKET_TYPE_MASK) == PACKET_TYPE_INITIAL:
        push_uint_var(buf, len(header.token))
        push_bytes(buf, header.token)
    push_uint16(buf, 0)  # length
    push_uint16(buf, 0)  # pn


# FRAMES


class QuicFrameType(IntEnum):
    PADDING = 0
    PING = 1
    ACK = 2
    ACK_WITH_ECN = 3
    RESET_STREAM = 4
    STOP_SENDING = 5
    CRYPTO = 6
    NEW_CONNECTION_ID = 0x18


def pull_ack_frame(buf):
    rangeset = RangeSet()
    end = pull_uint_var(buf)  # largest acknowledged
    delay = pull_uint_var(buf)
    ack_range_count = pull_uint_var(buf)
    ack_count = pull_uint_var(buf)  # first ack range
    rangeset.add(end - ack_count, end + 1)
    end -= ack_count
    for _ in range(ack_range_count):
        end -= pull_uint_var(buf)
        ack_count = pull_uint_var(buf)
        rangeset.add(end - ack_count, end + 1)
        end -= ack_count
    return rangeset, delay


def push_ack_frame(buf, rangeset: RangeSet, delay: int):
    index = len(rangeset) - 1
    r = rangeset[index]
    push_uint_var(buf, r.stop - 1)
    push_uint_var(buf, delay)
    push_uint_var(buf, index)
    push_uint_var(buf, r.stop - 1 - r.start)
    start = r.start
    while index > 0:
        index -= 1
        r = rangeset[index]
        push_uint_var(buf, start - r.stop + 1)
        push_uint_var(buf, r.stop - r.start - 1)
        start = r.start


@dataclass
class QuicStreamFrame:
    data: bytes = b''
    offset: int = 0


def pull_crypto_frame(buf):
    offset = pull_uint_var(buf)
    length = pull_uint_var(buf)
    return QuicStreamFrame(offset=offset, data=pull_bytes(buf, length))


@contextmanager
def push_crypto_frame(buf, offset=0):
    push_uint_var(buf, offset)
    push_uint16(buf, 0)
    start = buf.tell()
    yield
    end = buf.tell()
    buf.seek(start - 2)
    push_uint16(buf, (end - start) | 0x4000)
    buf.seek(end)


def pull_new_connection_id_frame(buf):
    sequence_number = pull_uint_var(buf)
    length = pull_uint8(buf)
    connection_id = pull_bytes(buf, length)
    stateless_reset_token = pull_bytes(buf, 16)
    return (sequence_number, connection_id, stateless_reset_token)


def push_new_connection_id_frame(buf, sequence_number, connection_id, stateless_reset_token):
    assert len(stateless_reset_token) == 16
    push_uint_var(buf, sequence_number)
    push_uint8(buf, len(connection_id))
    push_bytes(buf, connection_id)
    push_bytes(buf, stateless_reset_token)