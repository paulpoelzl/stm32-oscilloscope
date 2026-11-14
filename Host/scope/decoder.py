"""Decoder layer: turns raw bytes into sample and overrun events."""

from abc import ABC, abstractmethod

import numpy as np

from scope.events import Event, Overrun, SampleBlock

# Largest sample value: the ADC samples with 12 bits.
ADC_MAX = 4095

# Largest overrun total: the firmware counts overruns in a uint16.
OVERRUN_MAX = 65535
OVERRUN_PREFIX = b"Overrun: "


class Decoder(ABC):
    """Turns a byte stream into events.

    The stream arrives in chunks that can be cut anywhere, even inside a line
    or a separator. Decoders keep incomplete data between calls to feed().
    """

    @abstractmethod
    def feed(self, data: bytes) -> list[Event]:
        """Return the events completed by data, in stream order.

        Returns [] when data completes nothing. Input that cannot be decoded
        is skipped, never raised.
        """


class AsciiDecoder(Decoder):
    """Decodes the firmware's text format.

    Each line holds one decimal sample from 0 to ADC_MAX, or "Overrun: N".
    Other lines, e.g. the startup message, are skipped.
    """

    def __init__(self, separator: bytes = b"\r\n"):
        self._separator = separator
        self._tail = b""

    def _flush(self, events: list[Event], values: list[int]) -> None:
        """Move values, if there are any, into a new SampleBlock."""
        if values:
            events.append(SampleBlock(np.array(values, dtype=np.uint16)))
            values.clear()

    def _parse_line(self, line: bytes) -> int | Overrun | None:
        """Return the sample or overrun in line, or None to skip it."""
        if line.startswith(OVERRUN_PREFIX):
            try:
                total = int(line.removeprefix(OVERRUN_PREFIX))
            except ValueError:
                return None
            if 0 <= total <= OVERRUN_MAX:
                return Overrun(total)
            return None
        try:
            value = int(line)
        except ValueError:
            return None
        if 0 <= value <= ADC_MAX:
            return value
        return None

    def feed(self, data: bytes) -> list[Event]:
        lines = (self._tail + data).split(self._separator)

        # The last element is the incomplete line after the last separator,
        # or b"" if data ends with one.
        self._tail = lines.pop()

        events: list[Event] = []
        values: list[int] = []
        for line in lines:
            parsed = self._parse_line(line)
            if isinstance(parsed, Overrun):
                self._flush(events, values)
                events.append(parsed)
            elif isinstance(parsed, int):
                values.append(parsed)
        self._flush(events, values)
        return events
