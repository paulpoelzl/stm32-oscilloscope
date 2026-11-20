import numpy as np
import pytest

from scope.controller import Controller
from scope.decoder import AsciiDecoder
from scope.trace import Trace
from scope.transport import Transport


class FakeTransport(Transport):
    """Returns the given chunks in order, raising those that are exceptions.

    Returns b"" once the chunks run out.
    """

    def __init__(self, *chunks):
        self._chunks = list(chunks)
        self.reads = 0

    def read(self) -> bytes:
        self.reads += 1
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        if isinstance(chunk, Exception):
            raise chunk
        return chunk

    def close(self) -> None:
        pass


class FakePlot:
    """Records what the controller asks the view to do."""

    def __init__(self):
        self.y = None
        self.errors = []
        self.views = []

    def plot(self, x, y):
        self.y = y.copy()

    def show_error(self, msg):
        self.errors.append(msg)

    def show_live(self, x_range):
        self.views.append("live")

    def show_history(self, x_range):
        self.views.append("history")


def make_controller(transport, history_size=3, window_size=3):
    plot = FakePlot()
    trace = Trace(history_size, window_size, 1.0)
    controller = Controller(
        transport, AsciiDecoder(), trace, plot, refresh_ms=1
    )
    return controller, plot


def test_update_plots_decoded_samples():
    controller, plot = make_controller(FakeTransport(b"1\r\n2\r\n"))
    controller.update()
    np.testing.assert_array_equal(plot.y, [np.nan, 1, 2])


def test_incomplete_line_does_not_redraw():
    controller, plot = make_controller(FakeTransport(b"1"))
    controller.update()
    assert plot.y is None


def test_end_of_source_is_not_an_error():
    controller, plot = make_controller(FakeTransport(EOFError()))
    controller.update()
    assert controller.error is None
    assert plot.errors == []


def test_read_failure_is_shown():
    error = OSError("port lost")
    controller, plot = make_controller(FakeTransport(error))
    controller.update()
    assert controller.error is error
    assert plot.errors == ["OSError: port lost"]


def test_timer_polls_after_start(qtbot):
    transport = FakeTransport(b"1\r\n")
    controller, plot = make_controller(transport)
    controller.start()
    qtbot.waitUntil(lambda: plot.y is not None)
    assert plot.y[-1] == 1


@pytest.mark.parametrize("error", [EOFError(), OSError("port lost")])
def test_timer_stops_after_read_ends(qtbot, error):
    transport = FakeTransport(error)
    controller, _ = make_controller(transport)
    controller.start()
    qtbot.waitUntil(lambda: transport.reads >= 1)
    qtbot.wait(50)
    assert transport.reads == 1


def test_events_while_stopped_are_dropped():
    transport = FakeTransport(b"1\r\n2\r\n", b"3\r\n4\r\n")
    controller, plot = make_controller(transport)
    controller.update()
    controller.toggle_running()
    controller.update()
    controller.toggle_running()
    np.testing.assert_array_equal(plot.y, [np.nan, 1, 2])


def test_stop_plots_history():
    transport = FakeTransport(b"1\r\n2\r\n3\r\n4\r\n")
    controller, plot = make_controller(transport, history_size=5, window_size=3)
    controller.update()
    np.testing.assert_array_equal(plot.y, [2, 3, 4])
    controller.toggle_running()
    assert plot.views == ["history"]
    np.testing.assert_array_equal(plot.y, [1, 2, 3, 4])


def test_second_toggle_shows_window_again():
    transport = FakeTransport(b"1\r\n2\r\n", b"3\r\n4\r\n")
    controller, plot = make_controller(transport)
    controller.update()
    controller.toggle_running()
    controller.toggle_running()
    controller.update()
    assert plot.views == ["history", "live"]
    np.testing.assert_array_equal(plot.y, [2, 3, 4])
