"""Entry point: connects the layers and runs the scope on the board.

Can also replay a recording instead of reading the board, or record what the
board sends.
"""

import argparse
import sys
from pathlib import Path

import pyqtgraph as pg

from scope.board import BAUDRATE, SAMPLE_RATE, VID
from scope.controller import Controller
from scope.decoder import AsciiDecoder
from scope.plot import LivePlot
from scope.trace import Trace
from scope.transport import (
    FileTransport,
    RecordingTransport,
    SerialTransport,
    Transport,
    find_port,
)

# Samples on screen while running: 4 seconds at 1000 samples per second.
WINDOW_SAMPLES = 4000

# Samples kept to scroll back through while stopped: 16 seconds.
HISTORY_SAMPLES = 4 * WINDOW_SAMPLES

# Time between plot refreshes, in milliseconds.
REFRESH_MS = 20

# Serial read timeout in seconds. 0 never blocks, so the GUI stays responsive.
TIMEOUT = 0.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line, or argv if given.

    Exits with a usage message when the arguments are invalid.
    """
    parser = argparse.ArgumentParser(description=__doc__)

    # The bytes come either from the board or from a recording, never both.
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "-p",
        "--port",
        default=None,
        help="serial port of the board, e.g. COM5 "
        "(default: find the board by its USB vendor ID)",
    )
    source.add_argument(
        "--replay",
        type=Path,
        default=None,
        metavar="FILE",
        help="replay a recording from FILE instead of reading the board",
    )

    parser.add_argument(
        "--record",
        type=Path,
        default=None,
        metavar="FILE",
        help="record the raw bytes from the board to FILE",
    )
    parser.add_argument(
        "-b",
        "--baud",
        type=int,
        default=BAUDRATE,
        help="baud rate of the serial port "
        "(default: %(default)s; ignored with --replay)",
    )
    args = parser.parse_args(argv)

    # An option can join only one exclusive group, so check this pair by hand.
    # Recording a replay to the same file would truncate it before it is read.
    if args.replay is not None and args.record is not None:
        parser.error("argument --record: not allowed with argument --replay")
    return args


def open_transport(args: argparse.Namespace) -> Transport:
    """Open the source of bytes that args asks for.

    That is the replay file if given, else the board's serial port. Wraps it
    in a RecordingTransport when recording. Raises LookupError if no board is
    found, OSError if the port or a file cannot be opened.
    """
    if args.replay is None:
        if args.port is None:
            # No port given: look for the board by its USB vendor ID.
            port = find_port(vid=VID)
        else:
            port = args.port

        transport = SerialTransport.open(
            port=port, baudrate=args.baud, timeout=TIMEOUT
        )
    else:
        transport = FileTransport(file=args.replay)

    if args.record is not None:
        # Takes ownership: closes the inner transport, too, even on failure.
        transport = RecordingTransport(inner=transport, file=args.record)

    return transport


def main() -> int:
    """Run the scope until its window is closed.

    Returns the exit code: 0 when the window was closed normally, 1 when the
    board was not found, its port or a file could not be opened, or reading
    failed. Invalid arguments exit with 2 before anything is opened.
    """
    args = parse_args()

    try:
        transport = open_transport(args)
    except (OSError, LookupError) as error:
        print(error, file=sys.stderr)
        return 1

    # Enter the with block right away, so the port is closed even if building
    # the GUI fails.
    with transport:
        decoder = AsciiDecoder()
        trace = Trace(
            HISTORY_SAMPLES, WINDOW_SAMPLES, SAMPLE_RATE, label="ADC Count"
        )

        # The QApplication must exist before any widget is created.
        app = pg.mkQApp(name="Scope")
        plot = LivePlot(
            x_range=trace.window_x_range,
            y_range=trace.y_range,
            y_label=trace.y_label,
            y_units=trace.y_unit,
        )
        plot.widget.show()

        controller = Controller(
            transport, decoder, trace, plot, refresh_ms=REFRESH_MS
        )

        shortcut = pg.QtGui.QShortcut(
            pg.QtGui.QKeySequence("Space"), plot.widget
        )
        shortcut.activated.connect(controller.toggle_running)

        controller.start()
        app.exec()
        return 0 if controller.error is None else 1


if __name__ == "__main__":
    sys.exit(main())
