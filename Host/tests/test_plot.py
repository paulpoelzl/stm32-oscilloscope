import numpy as np
import pytest
from pyqtgraph.Qt import QtWidgets

from scope.plot import LivePlot


@pytest.fixture
def plot(qtbot):
    plot = LivePlot(
        x_range=(-4.0, 0.0), y_range=(0.0, 3.3), y_label="Voltage", y_units="V"
    )
    qtbot.addWidget(plot.widget)
    return plot


def test_axes_use_given_ranges(plot):
    x_range, y_range = plot.widget.getPlotItem().viewRange()
    np.testing.assert_allclose(x_range, [-4.0, 0.0])
    np.testing.assert_allclose(y_range, [0.0, 3.3])


def test_axes_are_labelled(plot):
    bottom = plot.widget.getPlotItem().getAxis("bottom")
    left = plot.widget.getPlotItem().getAxis("left")
    assert (bottom.labelText, bottom.labelUnits) == ("Time", "s")
    assert (left.labelText, left.labelUnits) == ("Voltage", "V")


def test_plot_replaces_curve_data(plot):
    plot.plot(np.array([0.0, 1.0]), np.array([5.0, 6.0]))
    plot.plot(np.array([0.0, 1.0]), np.array([7.0, np.nan]))
    (curve,) = plot.widget.getPlotItem().listDataItems()
    _, y = curve.getData()
    np.testing.assert_array_equal(y, [7.0, np.nan])


def test_show_error_opens_error_box(plot, monkeypatch):
    # The real box is modal and would block the test until clicked.
    shown = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "critical",
        lambda parent, title, msg: shown.append(msg),
    )
    plot.show_error("port lost")
    assert shown == ["port lost"]


def test_x_axis_ignores_mouse_while_live(plot):
    assert plot.widget.getViewBox().state["mouseEnabled"] == [False, True]


def test_show_history_widens_x_range_past_live_limits(plot):
    plot.show_history((-16.0, 0.0))
    x_range, _ = plot.widget.getPlotItem().viewRange()
    np.testing.assert_allclose(x_range, [-16.0, 0.0])
    assert plot.widget.getViewBox().state["mouseEnabled"] == [True, True]


def test_show_live_returns_to_window(plot):
    plot.show_history((-16.0, 0.0))
    plot.show_live((-4.0, 0.0))
    x_range, _ = plot.widget.getPlotItem().viewRange()
    np.testing.assert_allclose(x_range, [-4.0, 0.0])
    assert plot.widget.getViewBox().state["mouseEnabled"] == [False, True]
