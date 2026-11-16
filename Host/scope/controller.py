"""Controller: moves bytes from the transport through to the plot."""

from typing import Protocol

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray

from scope.decoder import Decoder
from scope.trace import Trace
from scope.transport import Transport


class Plot(Protocol):
    """What the controller needs from a view, e.g. LivePlot."""

    def plot(self, x: NDArray[np.float32], y: NDArray[np.float32]) -> None:
        """Draw the points (x, y), replacing the previous ones."""
        ...

    def show_error(self, msg: str) -> None:
        """Tell the user about a failure."""
        ...


class Controller:
    """Polls the transport on a timer and redraws the plot.

    Each tick reads the bytes that arrived, decodes them, adds the events to
    the trace and plots it. Does not own the transport: whoever opened it
    closes it.

    When the source ends, the timer stops and the last trace stays on screen.
    When reading fails, the timer stops, the error is shown and error holds
    the exception.
    """

    def __init__(
        self,
        transport: Transport,
        decoder: Decoder,
        trace: Trace,
        plot: Plot,
        refresh_ms: int = 30,
    ):
        """Connect the layers. Nothing is read until start().

        refresh_ms is the time between ticks, in milliseconds.
        """
        self._timer = pg.QtCore.QTimer(interval=refresh_ms)
        self._timer.timeout.connect(self.update)
        self._transport = transport
        self._decoder = decoder
        self._trace = trace
        self._plot = plot
        self.error: Exception | None = None

    def update(self) -> None:
        """Run one tick. Called by the timer, or directly in tests."""
        try:
            raw = self._transport.read()
        except EOFError:
            self._timer.stop()
        except Exception as error:
            self._timer.stop()
            self._plot.show_error(f"{type(error).__name__}: {error}")
            self.error = error
        else:
            events = self._decoder.feed(raw)
            if events:
                self._trace.consume(events)
                self._plot.plot(self._trace.x, self._trace.y)

    def start(self) -> None:
        """Start polling. Needs a running Qt event loop to tick."""
        self._timer.start()
