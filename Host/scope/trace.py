"""Trace layer: turns events into (x, y) coordinates."""

import numpy as np
from numpy.typing import NDArray

from scope.events import Event, Overrun, SampleBlock

# Pushed for each overrun, so that the plot breaks the line at the gap.
_GAP = np.full(1, np.nan, dtype=np.float32)


class Trace:
    """The newest samples, one screen wide, scrolling from right to left.

    New samples enter on the right and push the oldest ones out on the left.
    Slots without a sample yet are NaN, and each overrun adds one NaN to mark
    where samples were lost. The number of lost samples is unknown, so times
    left of a gap are only approximate.
    """

    def __init__(self, size: int, sample_rate: float):
        """Create an empty trace.

        size is the number of samples on screen. sample_rate is the rate of
        samples in the stream, in samples per second.
        """
        self._size = size
        self._y = np.full(size, np.nan, dtype=np.float32)
        self._x = np.linspace(
            start=-(size - 1) / sample_rate,
            stop=0.0,
            num=size,
            dtype=np.float32,
        )

    def _push(self, data: NDArray) -> None:
        """Shift y left by len(data) and write data into the freed slots."""
        data_len = len(data)
        if data_len == 0:
            return
        if data_len < self._size:
            self._y[:-data_len] = self._y[data_len:]
            self._y[-data_len:] = data
        else:
            self._y[:] = data[-self._size :]

    def consume(self, events: list[Event]) -> None:
        """Add events, in stream order, to the right end of the trace."""
        for event in events:
            if isinstance(event, Overrun):
                self._push(_GAP)
            elif isinstance(event, SampleBlock):
                self._push(event.samples)

    @property
    def x(self) -> NDArray[np.float32]:
        """Time of each slot in seconds, from about -size/sample_rate to 0.

        The newest sample is at 0. x never changes, so it can be handed to the
        plot once.
        """
        return self._x

    @property
    def y(self) -> NDArray[np.float32]:
        """Raw ADC counts from 0 to 4095, NaN at gaps and empty slots.

        The array is updated in place, so references to it stay valid.
        """
        return self._y
