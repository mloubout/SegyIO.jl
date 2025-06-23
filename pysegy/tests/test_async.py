import os
import asyncio
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

import pysegy as seg  # noqa: E402
from pysegy.types import FileHeader, BinaryTraceHeader, SeisBlock  # noqa: E402

DATAFILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "data",
    "overthrust_2D_shot_1_20.segy",
)


def test_segy_read_async():
    block = asyncio.run(seg.segy_read_async(DATAFILE))
    assert block.fileheader.bfh.ns == 751
    assert len(block.traceheaders) == 3300
    assert block.traceheaders[0].SourceX == 400
    assert block.traceheaders[0].GroupX == 100


def test_async_write_roundtrip(tmp_path):
    async def run():
        fh = FileHeader()
        fh.bfh.ns = 4
        fh.bfh.DataSampleFormat = 5
        headers = [BinaryTraceHeader() for _ in range(2)]
        for th in headers:
            th.ns = 4
            th.SourceX = 1234
        data = [[float(i*j) for j in range(2)] for i in range(4)]
        block = SeisBlock(fh, headers, data)
        tmp = tmp_path / "temp_async.segy"
        await seg.segy_write_async(str(tmp), block)
        out = await seg.segy_read_async(str(tmp))
        assert out.fileheader.bfh.ns == 4
        assert out.traceheaders[0].SourceX == 1234
        assert out.data == data

    asyncio.run(run())


def test_segy_scan_async_directory_pattern():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    scan = asyncio.run(
        seg.segy_scan_async(
            data_dir,
            "overthrust_2D_shot_*.segy",
            keys=["GroupX"],
        )
    )
    assert isinstance(scan, seg.SegyScan)
    assert len(scan.shots) == 97
    assert len(set(scan.paths)) == 5
    idx = 0
    assert scan.paths[idx].endswith("overthrust_2D_shot_1_20.segy")
    assert scan.counts[idx] == 127
    assert scan.summary(idx)["GroupX"] == (100, 6400)
