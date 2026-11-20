"""Trace layer: turns events into (x, y) coordinates."""

import numpy as np
from numpy.typing import NDArray

from scope.board import ADC_MAX
from scope.events import Event, Overrun, SampleBlock

# Pushed for each overrun, so that the plot breaks the line at the gap.
_GAP = np.full(1, np.nan, dtype=np.float32)


class Trace:
    """The newest samples, scrolling from right to left.

    Keeps a history of the newest samples, of which the newest few form the
    window shown while running. New samples enter on the right and push the
    oldest ones out on the left. Slots without a sample yet are NaN, and each
    overrun adds one NaN to mark where samples were lost. The number of lost
    samples is unknown, so times left of a gap are only approximate.

    Samples are converted from ADC counts with offset + scale * count, e.g.
    into volts. The defaults keep raw counts.
    """

    def __init__(
        self,
        history_size: int,
        window_size: int,
        sample_rate: float,
        scale: float = 1.0,
        offset: float = 0.0,
        label: str = "ADC count",
        unit: str = "",
    ):
        """Create an empty trace.

        history_size is the number of samples kept, window_size the number
        of newest samples on screen while running. sample_rate is the rate of
        samples in the stream, in samples per second. scale and offset convert
        ADC counts into y values. label and unit name the converted values,
        e.g. "Voltage" and "V", and are only passed on to the plot.
        """
        if window_size < 1:
            raise ValueError("window_size must be at least 1.")
        if history_size < window_size:
            raise ValueError("window_size must not exceed history_size.")

        self._history_size = history_size
        self._window_size = window_size
        self._scale = scale
        self._offset = offset
        self._label = label
        self._unit = unit
        self._write_index = history_size
        self._valid_samples = 0

        # Twice the history, so that the newest samples are moved back to the
        # start only once every history_size samples, not on every push.
        self._y = np.full(2 * history_size, np.nan, dtype=np.float32)
        self._x = np.linspace(
            start=-(history_size - 1) / sample_rate,
            stop=0.0,
            num=history_size,
            dtype=np.float32,
        )

    def _push(self, data: NDArray) -> None:
        """Append data after the newest sample.

        When the buffer is full, first moves the samples that stay in the
        history to its start.
        """
        data_len = len(data)
        if data_len == 0:
            return

        self._valid_samples = min(
            self._valid_samples + data_len, self._history_size
        )

        if data_len > self._history_size:
            self._y[: self._history_size] = data[-self._history_size :]
            self._write_index = self._history_size
            return

        if self._write_index + data_len > 2 * self._history_size:
            self._y[: self._history_size - data_len] = self._y[
                self._write_index
                - self._history_size
                + data_len : self._write_index
            ]
            self._write_index = self._history_size - data_len

        self._y[self._write_index : self._write_index + data_len] = data
        self._write_index += data_len

    def consume(self, events: list[Event]) -> None:
        """Add events, in stream order, to the right end of the trace."""
        for event in events:
            if isinstance(event, Overrun):
                self._push(_GAP)
            elif isinstance(event, SampleBlock):
                self._push(self._offset + self._scale * event.samples)

    def _history_len(self) -> int:
        """Number of slots in the history views, at least one window."""
        return max(self._valid_samples, self._window_size)

    @property
    def window_x(self) -> NDArray[np.float32]:
        """Time of each slot in the window in seconds, newest at 0.

        Runs from about -window_size/sample_rate to 0. The values never
        change, as the newest sample is always at 0.
        """
        return self._x[-self._window_size :]

    @property
    def history_x(self) -> NDArray[np.float32]:
        """Time of each slot in the history in seconds, newest at 0.

        Covers only the samples received so far, at most history_size. Its
        last window_size values are window_x.
        """
        return self._x[-self._history_len() :]

    @property
    def window_y(self) -> NDArray[np.float32]:
        """Converted samples in the window, NaN at gaps and empty slots.

        Each value is offset + scale * count, in y_unit. The array is a view
        into the buffer that the next consume() may change or move, so read
        it again after each consume().
        """
        return self._y[
            self._write_index - self._window_size : self._write_index
        ]

    @property
    def history_y(self) -> NDArray[np.float32]:
        """Converted samples in the history, NaN at gaps and empty slots.

        Like window_y, but as long as history_x. Only valid until the next
        consume().
        """
        return self._y[
            self._write_index - self._history_len() : self._write_index
        ]

    @property
    def window_x_range(self) -> tuple[float, float]:
        """First and last time of window_x in seconds, as (oldest, newest)."""
        return (float(self._x[-self._window_size]), float(self._x[-1]))

    @property
    def history_x_range(self) -> tuple[float, float]:
        """First and last time of history_x in seconds, as (oldest, newest)."""
        return (float(self._x[-self._history_len()]), float(self._x[-1]))

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
