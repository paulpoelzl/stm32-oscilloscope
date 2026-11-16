"""Trace layer: turns events into (x, y) coordinates."""

import numpy as np
from numpy.typing import NDArray

from scope.board import ADC_MAX
from scope.events import Event, Overrun, SampleBlock

# Pushed for each overrun, so that the plot breaks the line at the gap.
_GAP = np.full(1, np.nan, dtype=np.float32)


class Trace:
    """The newest samples, one screen wide, scrolling from right to left.

    New samples enter on the right and push the oldest ones out on the left.
    Slots without a sample yet are NaN, and each overrun adds one NaN to mark
    where samples were lost. The number of lost samples is unknown, so times
    left of a gap are only approximate.

    Samples are converted from ADC counts with offset + scale * count, e.g.
    into volts. The defaults keep raw counts.
    """

    def __init__(
        self,
        size: int,
        sample_rate: float,
        scale: float = 1.0,
        offset: float = 0.0,
        label: str = "ADC count",
        unit: str = "",
    ):
        """Create an empty trace.

        size is the number of samples on screen. sample_rate is the rate of
        samples in the stream, in samples per second. scale and offset convert
        ADC counts into y values. label and unit name the converted values,
        e.g. "Voltage" and "V", and are only passed on to the plot.
        """
        self._size = size
        self._scale = scale
        self._offset = offset
        self._label = label
        self._unit = unit
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
                self._push(self._offset + self._scale * event.samples)

    @property
    def x(self) -> NDArray[np.float32]:
        """Time of each slot in seconds, from about -size/sample_rate to 0.

        The newest sample is at 0. x never changes, so it can be handed to the
        plot once.
        """
        return self._x

    @property
    def y(self) -> NDArray[np.float32]:
        """Converted samples, NaN at gaps and empty slots.

        Each value is offset + scale * count, in y_unit. The array is updated
        in place, so references to it stay valid.
        """
        return self._y

    @property
    def x_range(self) -> tuple[float, float]:
        """First and last time of x in seconds, as (oldest, newest)."""
        return (float(self._x[0]), float(self._x[-1]))

    @property
    def y_range(self) -> tuple[float, float]:
        """Converted values of the ADC's full range, from count 0 to ADC_MAX.

        With a negative scale, the first value is the larger one.
        """
        return (self._offset, self._offset + self._scale * ADC_MAX)

    @property
    def y_label(self) -> str:
        """Name of the y values, e.g. "Voltage"."""
        return self._label

    @property
    def y_unit(self) -> str:
        """Unit of the y values, e.g. "V", or "" for raw counts."""
        return self._unit
