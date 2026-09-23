"""The runtime-cost measurement reports the shapes the paper reads from it."""

import asyncio

import pandas as pd

from scripts.measure_runtime_cost import _file_channel, _text_channel, measure, sample_frame


def test_a_sample_frame_carries_the_cell_kinds_a_delivered_table_has():
    frame = sample_frame(4)
    assert list(frame.columns) == ["identifier", "name", "count", "ratio"]
    assert frame["identifier"].iloc[0] == "00000000"   # a zero-padded identifier
    assert len(frame) == 4


def test_the_text_channel_reports_what_a_reply_would_spend(tmp_path):
    small, large = _text_channel(sample_frame(10)), _text_channel(sample_frame(1000))
    assert large["approx_tokens"] > small["approx_tokens"] * 50
    assert large["bytes"] > small["bytes"]


def test_the_file_channel_reports_its_own_size(tmp_path):
    channel = _file_channel(sample_frame(100), tmp_path)
    assert channel["bytes"] > 0
    assert channel["write"]["trials"] == channel["read"]["trials"]


def test_a_measurement_covers_both_runtimes_and_both_channels(tmp_path):
    report = asyncio.run(measure(tmp_path))
    assert set(report["start_up"]) == {"in_process", "kernel"}
    assert set(report["throughput"]) == {"in_process", "kernel"}
    for rows, channels in report["crossing"].items():
        assert set(channels) == {"in_process", "kernel", "parquet_file", "reply_json"}, rows
    # The machine's load is recorded, because it bounds how finely timings read.
    assert report["machine"]["load_average"] and report["machine"]["cpu_count"]


def test_one_crossing_is_what_the_memory_figure_covers(tmp_path):
    """The timing loop repeats the crossing, so memory is read around one of them."""
    report = asyncio.run(measure(tmp_path))
    for rows, channels in report["crossing"].items():
        for runtime in ("in_process", "kernel"):
            held = channels[runtime]["resident_increase_one_table"]
            assert set(held) == {"host_rss_mb", "kernel_rss_mb"}, (rows, runtime)
        # A frame the host already holds costs the in-process runtime nothing to lend.
        assert channels["in_process"]["resident_increase_one_table"]["host_rss_mb"] < 5, rows
