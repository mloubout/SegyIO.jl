import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import python as seg
from python.types import BinaryFileHeader, FileHeader, BinaryTraceHeader, SeisBlock

DATAFILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'overthrust_2D_shot_1_20.segy')


def test_read():
    block = seg.segy_read(DATAFILE)
    assert block.fileheader.bfh.ns == 751
    assert len(block.traceheaders) == 3300
    assert block.traceheaders[0].SourceX == 400
    assert block.traceheaders[0].GroupX == 100


def test_write_roundtrip(tmp_path):
    fh = FileHeader()
    fh.bfh.ns = 4
    fh.bfh.DataSampleFormat = 5
    headers = [BinaryTraceHeader() for _ in range(2)]
    for th in headers:
        th.ns = 4
        th.SourceX = 1234
    data = [[float(i*j) for j in range(2)] for i in range(4)]
    block = SeisBlock(fh, headers, data)
    tmp = tmp_path / 'temp.segy'
    seg.segy_write(str(tmp), block)
    out = seg.segy_read(str(tmp))
    assert out.fileheader.bfh.ns == 4
    assert out.traceheaders[0].SourceX == 1234
    assert out.data == data
