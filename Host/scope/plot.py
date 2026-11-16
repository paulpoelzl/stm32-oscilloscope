"""Plot layer: draws the trace as a scrolling line."""

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray

LINE_COLOR = "#FFE600"
LINE_WIDTH = 2.0


class LivePlot:
    """A pyqtgraph plot that redraws one curve on every call to plot().

    The axes start at the ranges given at construction, so the view does
    not jump while samples scroll through. NaN values break the line, which
    shows gaps and empty slots.
    """

    def __init__(
        self,
        *,
        x_range: tuple[float, float] = (-1.0, 0.0),
        y_range: tuple[float, float] = (0.0, 1.0),
        y_label: str = "",
        y_units: str = "",
    ):
        """Create the plot widget without showing it.

        x_range and y_range are the starting axis ranges as (min, max). y_label
        and y_units name the y axis; the x axis is always time in seconds.
        A QApplication must exist before construction.
        """
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setXRange(*x_range, padding=0)
        self._plot_widget.setYRange(*y_range, padding=0)

        # pyqtgraph picks the SI prefix itself, e.g. ms for a short trace.
        self._plot_widget.setLabel("bottom", "Time", units="s")
        self._plot_widget.setLabel("left", y_label, units=y_units)

        # Look like a scope: a yellow trace on black, with a faint grid.
        pen = pg.mkPen(LINE_COLOR, width=LINE_WIDTH)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # "finite" leaves out NaN points instead of drawing through them.
        self._curve = self._plot_widget.plot(pen=pen, connect="finite")

    @property
    def widget(self) -> pg.PlotWidget:
        """The Qt widget, for placing the plot in a layout."""
        return self._plot_widget

    def plot(self, x: NDArray[np.float32], y: NDArray[np.float32]) -> None:
        """Replace the curve with the points (x, y)."""
        self._curve.setData(x, y)

    def show_error(self, msg: str) -> None:
        """Show msg in a modal error box and wait until it is closed."""
        pg.QtWidgets.QMessageBox.critical(self._plot_widget, "Error", msg)
