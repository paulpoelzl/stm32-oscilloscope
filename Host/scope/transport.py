"""Transport layer: delivers raw bytes from a serial port or a file."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self

import serial
import serial.tools.list_ports


class Transport(ABC):
    """Source of raw bytes.

    Transports are context managers: leaving the with block calls close().
    """

    @abstractmethod
    def read(self) -> bytes:
        """Return the bytes that arrived since the last read.

        Waits at most a short time when nothing has arrived, then returns b"",
        which means "nothing yet", not the end of the data. Raises EOFError
        once the source has ended for good. Any other exception means the
        source failed, e.g. the cable was pulled.
        """

    @abstractmethod
    def close(self) -> None:
        """Release the underlying port or file."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class SerialTransport(Transport):
    """Serial port, e.g. the ST-LINK virtual COM port.

    Takes ownership of an open pyserial port: close() closes it. Discards
    bytes buffered before construction. read() waits at most the port's
    timeout when nothing has arrived.
    """

    def __init__(self, port: serial.SerialBase):
        self._serial = port
        self._serial.reset_input_buffer()

    @classmethod
    def open(cls, port: str, baudrate: int, timeout: float) -> Self:
        """Open a port by name, e.g. "COM5", or by pyserial URL."""
        return cls(
            serial.serial_for_url(port, baudrate=baudrate, timeout=timeout)
        )

    def read(self) -> bytes:
        # read(0) returns at once, so ask for at least 1 byte to wait for the
        # timeout. Asking for in_waiting returns everything already buffered.
        return self._serial.read(max(1, self._serial.in_waiting))

    def close(self) -> None:
        self._serial.close()


class FileTransport(Transport):
    """Replays a file in chunks of batchsize bytes, as fast as it is read."""

    def __init__(self, file: str | Path, batchsize: int = 4096):
        self._batchsize = batchsize
        self._file = open(file, "rb")

    def read(self) -> bytes:
        out = self._file.read(self._batchsize)
        if not out:
            raise EOFError("EOF reached.")
        return out

    def close(self) -> None:
        self._file.close()


class RecordingTransport(Transport):
    """Records every byte read from an inner transport to a file.

    Takes ownership of inner: close() closes it, too.
    """

    def __init__(self, inner: Transport, file: str | Path):
        self._inner = inner
        try:
            self._file = open(file, "wb")
        except:
            self._inner.close()
            raise

    def read(self) -> bytes:
        out = self._inner.read()
        self._file.write(out)
        return out

    def close(self) -> None:
        try:
            self._inner.close()
        finally:
            self._file.close()


def find_port(
    description: str | None = None,
    vid: int | None = None,
    pid: int | None = None,
) -> str:
    """Return the first serial port matching a description or USB VID/PID.

    The description matches as a case-insensitive substring. Raises
    LookupError if no port matches.
    """
    for port in serial.tools.list_ports.comports():
        if description and description.lower() in port.description.lower():
            return port.device
        if vid and port.vid == vid and (pid is None or port.pid == pid):
            return port.device
    criteria = []
    if description:
        criteria.append(f'description "{description}"')
    if vid:
        criteria.append(f"VID {vid:#06x}")
    if pid is not None:
        criteria.append(f"PID {pid:#06x}")
    raise LookupError(f"No serial port matches {', '.join(criteria)}.")
