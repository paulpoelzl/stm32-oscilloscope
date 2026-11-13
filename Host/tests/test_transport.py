import pytest
import serial

from scope.transport import (
    FileTransport,
    RecordingTransport,
    SerialTransport,
)


def read_all(transport):
    data = bytearray()
    try:
        while True:
            data.extend(transport.read())
    except EOFError:
        return data


@pytest.fixture
def loop_port():
    """pyserial loopback port: bytes written to it come back on read."""
    port = serial.serial_for_url("loop://", timeout=0.05)
    yield port
    port.close()


# SerialTransport


def test_serial_discards_bytes_buffered_before_construction(loop_port):
    loop_port.write(bytes(range(256)))
    with SerialTransport(loop_port) as transport:
        assert transport.read() == b""


def test_serial_returns_all_buffered_bytes_in_one_read(loop_port):
    content = bytes(range(256))
    with SerialTransport(loop_port) as transport:
        loop_port.write(content)
        assert transport.read() == content


def test_serial_closes_injected_port(loop_port):
    with SerialTransport(loop_port):
        pass
    assert not loop_port.is_open


def test_serial_open_accepts_pyserial_url():
    with SerialTransport.open("loop://", 115200, 0.05) as transport:
        assert transport.read() == b""


# FileTransport


def test_file_replays_whole_file(tmp_path):
    path = tmp_path / "capture.bin"
    content = bytes(range(256)) * 100
    path.write_bytes(content)
    with FileTransport(path) as transport:
        assert read_all(transport) == content


def test_file_keeps_raising_eof_at_end(tmp_path):
    path = tmp_path / "capture.bin"
    path.write_bytes(b"abc")
    with FileTransport(path) as transport:
        read_all(transport)
        with pytest.raises(EOFError):
            transport.read()
        with pytest.raises(EOFError):
            transport.read()


def test_file_raises_eof_on_first_read_when_empty(tmp_path):
    path = tmp_path / "capture.bin"
    path.write_bytes(b"")
    with FileTransport(path) as transport, pytest.raises(EOFError):
        transport.read()


# RecordingTransport


def test_recording_returns_and_records_every_chunk(loop_port, tmp_path):
    path = tmp_path / "recording.bin"
    with RecordingTransport(SerialTransport(loop_port), path) as transport:
        loop_port.write(b"12\r\n")
        assert transport.read() == b"12\r\n"
        assert transport.read() == b""
        loop_port.write(b"34\r\n")
        assert transport.read() == b"34\r\n"
    assert path.read_bytes() == b"12\r\n34\r\n"


def test_recording_passes_eof_through(tmp_path):
    source = tmp_path / "capture.bin"
    source.write_bytes(b"abc")
    inner = FileTransport(source)
    with RecordingTransport(inner, tmp_path / "recording.bin") as transport:
        assert transport.read() == b"abc"
        with pytest.raises(EOFError):
            transport.read()


def test_recording_closes_inner_transport(loop_port, tmp_path):
    inner = SerialTransport(loop_port)
    with RecordingTransport(inner, tmp_path / "recording.bin"):
        pass
    assert not loop_port.is_open


def test_recording_closes_inner_transport_when_file_cannot_open(
    loop_port, tmp_path
):
    inner = SerialTransport(loop_port)
    with pytest.raises(FileNotFoundError):
        RecordingTransport(inner, tmp_path / "missing" / "recording.bin")
    assert not loop_port.is_open


def test_recording_closes_file_when_inner_close_fails(
    loop_port, tmp_path, monkeypatch
):
    def close_fails():
        raise OSError("cable pulled")

    path = tmp_path / "recording.bin"
    inner = SerialTransport(loop_port)
    monkeypatch.setattr(inner, "close", close_fails)
    transport = RecordingTransport(inner, path)
    loop_port.write(b"abc")
    transport.read()
    with pytest.raises(OSError):
        transport.close()
    # Only a closed file is guaranteed to be flushed to disk.
    assert path.read_bytes() == b"abc"


def test_recording_of_file_replay_is_byte_identical(tmp_path):
    source = tmp_path / "capture.bin"
    copy = tmp_path / "copy.bin"
    source.write_bytes(bytes(range(256)) * 100)
    with RecordingTransport(FileTransport(source), copy) as transport:
        read_all(transport)
    assert copy.read_bytes() == source.read_bytes()
