import numpy as np

from scope.decoder import AsciiDecoder
from scope.events import Overrun, SampleBlock


def assert_samples(event, expected):
    assert isinstance(event, SampleBlock)
    assert event.samples.dtype == np.uint16
    np.testing.assert_array_equal(event.samples, expected)


def test_empty_chunk_gives_no_events():
    assert AsciiDecoder().feed(b"") == []


def test_lines_in_one_chunk_become_one_block():
    events = AsciiDecoder().feed(b"1\r\n2\r\n4095\r\n")
    assert len(events) == 1
    assert_samples(events[0], [1, 2, 4095])


def test_incomplete_line_waits_for_next_chunk():
    decoder = AsciiDecoder()
    first = decoder.feed(b"12\r\n34")
    second = decoder.feed(b"56\r\n")
    assert len(first) == 1
    assert_samples(first[0], [12])
    assert len(second) == 1
    assert_samples(second[0], [3456])


def test_chunk_split_between_cr_and_lf():
    decoder = AsciiDecoder()
    assert decoder.feed(b"7\r") == []
    events = decoder.feed(b"\n")
    assert len(events) == 1
    assert_samples(events[0], [7])


def test_overrun_splits_blocks_in_order():
    events = AsciiDecoder().feed(b"1\r\n2\r\nOverrun: 3\r\n4\r\n")
    assert len(events) == 3
    assert_samples(events[0], [1, 2])
    assert events[1] == Overrun(3)
    assert_samples(events[2], [4])


def test_startup_message_is_skipped():
    events = AsciiDecoder().feed(b"stm32-oscilloscope: started\r\n5\r\n")
    assert len(events) == 1
    assert_samples(events[0], [5])


def test_garbage_bytes_are_skipped():
    events = AsciiDecoder().feed(b"\xff\xfe\r\n9\r\n")
    assert len(events) == 1
    assert_samples(events[0], [9])


def test_out_of_range_numbers_are_skipped():
    events = AsciiDecoder().feed(b"4096\r\n-1\r\n99999\r\n5\r\n")
    assert len(events) == 1
    assert_samples(events[0], [5])


def test_malformed_overrun_lines_are_skipped():
    data = b"Overrun: x\r\nOverrun: 1:2\r\nOverrun: -1\r\nOverrun: 65536\r\n"
    events = AsciiDecoder().feed(data + b"5\r\n")
    assert len(events) == 1
    assert_samples(events[0], [5])


def test_overrun_without_samples_gives_no_empty_block():
    events = AsciiDecoder().feed(b"Overrun: 1\r\nOverrun: 2\r\n5\r\n")
    assert len(events) == 3
    assert events[0] == Overrun(1)
    assert events[1] == Overrun(2)
    assert_samples(events[2], [5])


def test_overrun_line_split_across_chunks():
    decoder = AsciiDecoder()
    assert decoder.feed(b"Over") == []
    assert decoder.feed(b"run: 4\r\n") == [Overrun(4)]


def test_sample_blocks_compare_by_identity():
    block = SampleBlock(np.array([1, 2], dtype=np.uint16))
    assert block != SampleBlock(np.array([1, 2], dtype=np.uint16))
    assert block == block
