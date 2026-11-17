# Host

Python program that reads samples from the board over the ST-LINK virtual COM port and plots them live. It can also record what the board sends and replay the recording later without the board.

## Setup

On Windows, from this folder:

```bash
py -m venv .venv
source .venv/bin/activate        # Linux
.venv\Scripts\Activate.ps1       # Windows PowerShell
pip install -e ".[dev]"
```

## Usage

With the virtual environment active:

```bash
python -m scope                         # find the board and plot live
python -m scope -p COM5                 # use this port instead of searching
python -m scope --record capture.txt    # plot live and record to capture.txt
python -m scope --replay capture.txt    # replay a recording from capture.txt
```

Without `-p`, the board is found by the USB vendor ID of its ST-LINK. On Linux, the port is usually `/dev/ttyACM0` instead of `COM5`, and opening it needs membership in the `dialout` group: run `sudo usermod -aG dialout $USER` and log in again, otherwise opening the port fails with "Permission denied". `-b` overrides the baud rate, which is ignored when replaying. `--replay` can't be combined with `-p` or `--record`. `python -m scope --help` lists all options.

## Wire Format

The board sends ASCII text over USART2 at 115200 baud, one item per line, each ending in `\r\n`:

- `N`: one sample, a decimal ADC count from 0 to 4095, at 1000 samples per second.
- `Overrun: N`: samples were lost at this point. `N` is the board's running total of overruns, a uint16 that wraps from 65535 to 0, not the number of new ones.

Other lines, such as the startup message, are skipped. A recording holds the bytes exactly as they were received, so it is replayed through the same decoder as the live stream.

## Architecture

```
              bytes             events            x, y
 Transport ──────────> Decoder ──────────> Trace ──────────> LivePlot
     ^                    ^                  ^                   ^
     └────────────────────┴───── Controller ─┴───────────────────┘
                              (Qt timer tick)
```

The `Controller` moves the data along this chain on each tick of a Qt timer. The layers don't call each other, and the controller only uses their interfaces, so each layer is tested on its own and the controller with fakes.

- `transport.py`: delivers raw bytes from the serial port (`SerialTransport`) or a file (`FileTransport`). `RecordingTransport` wraps another transport and writes everything it reads to a file.
- `decoder.py`, `events.py`: turn the byte stream into events, `SampleBlock` and `Overrun`. Lines may be split across reads at any point, and input that can't be decoded is skipped, never raised.
- `trace.py`: keeps the newest screen of samples, scrolling from right to left with the newest sample at time 0. Converts ADC counts with a scale and offset, so events keep raw counts. NaN marks empty slots and lost samples.
- `plot.py`: draws the trace with pyqtgraph. NaN breaks the line, so gaps are visible.
- `controller.py`: on each timer tick, reads from the transport, decodes, adds the events to the trace and redraws. Stops at the end of a replay, or shows the error when reading fails.
- `board.py`: constants that mirror the firmware's configuration, such as the sample rate and baud rate.
- `__main__.py`: parses the command line, opens the transport and connects the layers.

## Development

```bash
pytest              # run the tests
ruff format .       # format
ruff check .        # lint
```

The GUI tests run headless: `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen`, so no windows open.
