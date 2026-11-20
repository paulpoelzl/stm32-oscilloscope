import numpy as np

from scope.decoder import AsciiDecoder
from scope.events import SampleBlock
from scope.trace import Trace
from scope.transport import FileTransport

NAN = np.nan


def assert_y(trace, expected):
    np.testing.assert_array_equal(
        trace.window_y, np.array(expected, np.float32)
    )


def test_replayed_capture_decodes_to_samples(tmp_path):
    expected = list(range(0, 4096, 7))
    path = tmp_path / "capture.txt"
    path.write_bytes(b"".join(b"%d\r\n" % value for value in expected))

    decoder = AsciiDecoder()
    samples = []
    with FileTransport(path) as transport:
        try:
            while True:
                for event in decoder.feed(transport.read()):
                    assert isinstance(event, SampleBlock)
                    samples.extend(event.samples.tolist())
        except EOFError:
            pass

    np.testing.assert_array_equal(samples, expected)


def test_replayed_capture_fills_trace(tmp_path):
    path = tmp_path / "capture.txt"
    path.write_bytes(b"1\r\n2\r\nOverrun: 1\r\n3\r\n")

    decoder = AsciiDecoder()
    trace = Trace(5, 5, 1.0)
    with FileTransport(path) as transport:
        try:
            while True:
                trace.consume(decoder.feed(transport.read()))
        except EOFError:
            pass

    assert_y(trace, [NAN, 1, 2, NAN, 3])
