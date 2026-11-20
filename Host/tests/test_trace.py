import numpy as np
import pytest

from scope.board import ADC_MAX
from scope.events import Overrun, SampleBlock
from scope.trace import Trace

NAN = np.nan


def block(*values):
    return SampleBlock(np.array(values, dtype=np.uint16))


def assert_y(trace, expected):
    np.testing.assert_array_equal(
        trace.window_y, np.array(expected, np.float32)
    )


def assert_history_y(trace, expected):
    np.testing.assert_array_equal(
        trace.history_y, np.array(expected, np.float32)
    )


def test_short_block_lands_at_right_end():
    trace = Trace(5, 5, 1.0)
    trace.consume([block(1, 2)])
    assert_y(trace, [NAN, NAN, NAN, 1, 2])


def test_blocks_scroll_oldest_samples_out():
    trace = Trace(4, 4, 1.0)
    trace.consume([block(1, 2, 3, 4), block(5, 6)])
    assert_y(trace, [3, 4, 5, 6])


def test_overrun_inserts_nan_between_blocks():
    trace = Trace(5, 5, 1.0)
    trace.consume([block(1, 2), Overrun(1), block(3, 4)])
    assert_y(trace, [1, 2, NAN, 3, 4])


def test_long_block_keeps_only_newest_samples():
    trace = Trace(3, 3, 1.0)
    trace.consume([block(1, 2, 3, 4, 5)])
    assert_y(trace, [3, 4, 5])


def test_newest_sample_is_at_time_zero():
    assert Trace(100, 100, 1000.0).window_x[-1] == 0.0


def test_x_steps_by_sample_period():
    trace = Trace(100, 100, 1000.0)
    np.testing.assert_allclose(np.diff(trace.window_x), 1e-3, rtol=1e-4)


def test_new_trace_is_all_nan():
    trace = Trace(3, 3, 1.0)
    assert_y(trace, [NAN, NAN, NAN])


def test_empty_block_leaves_trace_unchanged():
    trace = Trace(3, 3, 1.0)
    trace.consume([block(1, 2, 3)])
    trace.consume([block()])
    assert_y(trace, [1, 2, 3])


def test_block_of_screen_size_replaces_screen():
    trace = Trace(3, 3, 1.0)
    trace.consume([block(9)])
    trace.consume([block(1, 2, 3)])
    assert_y(trace, [1, 2, 3])


def test_separate_consume_calls_scroll_like_one():
    trace = Trace(6, 6, 1.0)
    trace.consume([block(1, 2)])
    trace.consume([block(3, 4)])
    assert_y(trace, [NAN, NAN, 1, 2, 3, 4])


def test_short_block_is_converted():
    trace = Trace(4, 4, 1.0, scale=2.0, offset=1.0)
    trace.consume([block(1, 2)])
    assert_y(trace, [NAN, NAN, 3, 5])


def test_long_block_is_converted():
    trace = Trace(3, 3, 1.0, scale=2.0, offset=1.0)
    trace.consume([block(1, 2, 3, 4)])
    assert_y(trace, [5, 7, 9])


def test_gap_stays_nan_after_conversion():
    trace = Trace(3, 3, 1.0, scale=2.0, offset=1.0)
    trace.consume([block(1), Overrun(1), block(2)])
    assert_y(trace, [3, NAN, 5])


def test_x_range_spans_x():
    trace = Trace(100, 100, 1000.0)
    assert trace.window_x_range == (float(trace.window_x[0]), 0.0)


def test_y_range_is_converted_adc_range():
    trace = Trace(3, 3, 1.0, scale=2.0, offset=1.0)
    assert trace.y_range == (1.0, 1.0 + 2.0 * ADC_MAX)


def test_label_and_unit_are_passed_through():
    trace = Trace(3, 3, 1.0, label="Voltage", unit="V")
    assert trace.y_label == "Voltage"
    assert trace.y_unit == "V"


def test_window_larger_than_history_is_rejected():
    with pytest.raises(ValueError):
        Trace(3, 5, 1.0)


def test_empty_window_is_rejected():
    with pytest.raises(ValueError):
        Trace(3, 0, 1.0)


def test_window_shows_newest_samples_of_history():
    trace = Trace(5, 2, 1.0)
    trace.consume([block(1, 2, 3, 4)])
    assert_y(trace, [3, 4])
    assert_history_y(trace, [1, 2, 3, 4])


def test_history_shorter_than_window_is_padded():
    trace = Trace(10, 3, 1.0)
    trace.consume([block(1, 2)])
    assert_history_y(trace, [NAN, 1, 2])


def test_history_holds_only_received_samples():
    trace = Trace(10, 3, 1.0)
    trace.consume([block(1, 2, 3, 4)])
    assert_history_y(trace, [1, 2, 3, 4])


def test_long_block_fills_whole_history():
    trace = Trace(3, 2, 1.0)
    trace.consume([block(1, 2, 3, 4, 5)])
    assert_y(trace, [4, 5])
    assert_history_y(trace, [3, 4, 5])


def test_block_filling_buffer_exactly_is_kept():
    # A block of history_size fills the 2x buffer up to its last slot, so the
    # next sample has to move the history back to the start first.
    trace = Trace(3, 2, 1.0)
    trace.consume([block(1, 2, 3)])
    assert_history_y(trace, [1, 2, 3])
    trace.consume([block(4)])
    assert_history_y(trace, [2, 3, 4])


# Samples 1..n, pushed one at a time into Trace(5, 2). The buffer holds 10
# slots, so pushes 6 and 12 are the first and second to move the history
# back to the start.
@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (6, [2, 3, 4, 5, 6]),
        (12, [8, 9, 10, 11, 12]),
    ],
)
def test_history_survives_moves_to_buffer_start(n, expected):
    trace = Trace(5, 2, 1.0)
    for sample in range(1, n + 1):
        trace.consume([block(sample)])
    assert_history_y(trace, expected)
    assert_y(trace, expected[-2:])


@pytest.mark.parametrize("n", [0, 4, 23])
def test_history_x_matches_history_y(n):
    trace = Trace(10, 3, 1000.0)
    trace.consume([block(*range(n))])
    assert len(trace.history_x) == len(trace.history_y)
    assert trace.history_x[-1] == 0.0
    assert trace.history_x_range == (float(trace.history_x[0]), 0.0)
