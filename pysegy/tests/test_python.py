import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pysegy as seg
from pysegy.ibm import ibm_to_ieee, ieee_to_ibm
from pysegy.types import BinaryFileHeader, FileHeader, BinaryTraceHeader, SeisBlock
from io import BytesIO
import urllib.request
import gzip
import pytest

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


def test_ibm_conversion():
    """Ensure IBM -> IEEE conversion works for known constant."""
    assert ibm_to_ieee(b"\x41\x10\x00\x00") == 1.0


def test_fileheader_io():
    """Round-trip a file header using in-memory bytes."""
    fh = FileHeader()
    fh.bfh.Job = 99
    fh.bfh.Line = 123
    buf = BytesIO()
    seg.write.write_fileheader(buf, fh)
    buf.seek(0)
    out = seg.read.read_fileheader(buf)
    assert out.bfh.Job == 99
    assert out.bfh.Line == 123
    assert len(buf.getvalue()) == 3600


def test_write_read_block_bytesio():
    """Write and read a simple block using BytesIO."""
    fh = FileHeader()
    fh.bfh.ns = 2
    fh.bfh.DataSampleFormat = 5
    headers = [BinaryTraceHeader() for _ in range(1)]
    headers[0].ns = 2
    data = [[1.0], [2.0]]
    block = SeisBlock(fh, headers, data)
    bio = BytesIO()
    seg.write.write_block(bio, block)
    bio.seek(0)
    out = seg.read.read_file(bio)
    assert out.data == data

BP_URL = "http://s3.amazonaws.com/open.source.geoscience/open_data/bpmodel94/Model94_shots.segy.gz"

def test_bp_model_headers():
    """Download a portion of the BP model data and verify header values."""
    response = urllib.request.urlopen(BP_URL)
    with gzip.GzipFile(fileobj=response) as gz:
        data = gz.read(40000)
    fh = seg.read.read_fileheader(BytesIO(data))
    assert fh.bfh.dt == 4000
    assert fh.bfh.ns == 2000
    assert fh.bfh.DataSampleFormat == 1
    bio = BytesIO(data)
    bio.seek(3600)
    th = seg.read.read_traceheader(bio)
    assert th.ns == 2000
    assert th.SourceX == 0
    assert th.GroupX == 15


def test_bp_model_scan(tmp_path):
    """Download the full BP Model dataset and verify shot statistics.

    The dataset contains 278 distinct shot locations. Receiver counts vary
    between 240 and 480 per shot. This test ensures the reader can process the
    entire file and that these counts match the known reference values.
    """
    dest = tmp_path / "Model94_shots.segy"
    response = urllib.request.urlopen(BP_URL)
    with gzip.GzipFile(fileobj=response) as gz, open(dest, "wb") as f:
        import shutil
        shutil.copyfileobj(gz, f)

    with open(dest, "rb") as f:
        fh = seg.read.read_fileheader(f)
        ns = fh.bfh.ns
        trace_size = 240 + ns * 4
        f.seek(0, os.SEEK_END)
        total = (f.tell() - 3600) // trace_size

        from collections import Counter

        counts: Counter[int] = Counter()
        f.seek(3600)
        for _ in range(total):
            th = seg.read.read_traceheader(f)
            counts[th.SourceX] += 1
            f.seek(ns * 4, os.SEEK_CUR)

    assert total == sum(counts.values())
    assert len(counts) == 278
    assert min(counts.values()) == 240
    assert max(counts.values()) == 480

