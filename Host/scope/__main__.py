"""Entry point: connects the layers and runs the scope on the board."""

import sys

import pyqtgraph as pg

from scope.board import BAUDRATE, SAMPLE_RATE, VID
from scope.controller import Controller
from scope.decoder import AsciiDecoder
from scope.plot import LivePlot
from scope.trace import Trace
from scope.transport import SerialTransport, find_port

# Samples on screen: 4 seconds at 1000 samples per second.
TRACE_SAMPLES = 4000

# Time between plot refreshes, in milliseconds.
REFRESH_MS = 20

# Serial read timeout in seconds. 0 never blocks, so the GUI stays responsive.
TIMEOUT = 0.0


def main() -> int:
    """Run the scope until its window is closed.

    Returns the exit code: 0 when the window was closed normally, 1 when the
    board was not found, its port could not be opened, or reading failed.
    """
    try:
        port = find_port(vid=VID)
    except LookupError as error:
        print(error, file=sys.stderr)
        return 1

    try:
        transport = SerialTransport.open(
            port=port, baudrate=BAUDRATE, timeout=TIMEOUT
        )
    except OSError as error:
        print(error, file=sys.stderr)
        return 1

    # Enter the with block right away, so the port is closed even if building
    # the GUI fails.
    with transport:
        decoder = AsciiDecoder()
        trace = Trace(TRACE_SAMPLES, SAMPLE_RATE, label="ADC Count")

        # The QApplication must exist before any widget is created.
        app = pg.mkQApp(name="Scope")
        plot = LivePlot(
            x_range=trace.x_range,
            y_range=trace.y_range,
            y_label=trace.y_label,
            y_units=trace.y_unit,
        )
        plot.widget.show()

        controller = Controller(
            transport, decoder, trace, plot, refresh_ms=REFRESH_MS
        )
        controller.start()
        app.exec()
        return 0 if controller.error is None else 1


if __name__ == "__main__":
    sys.exit(main())
