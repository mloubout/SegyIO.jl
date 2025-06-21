import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pysegy as seg
from pysegy.ibm import ibm_to_ieee, ieee_to_ibm
from pysegy.types import BinaryFileHeader, FileHeader, BinaryTraceHeader, SeisBlock
from io import BytesIO

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

import urllib.request
import gzip
import shutil
import pytest

BP_URL = "http://s3.amazonaws.com/open.source.geoscience/open_data/bpmodel94/Model94_shots.segy.gz"

@pytest.mark.xfail(reason="Dataset requires network access")
def test_bp_model_headers(tmp_path):
    gz_path = tmp_path / "Model94_shots.segy.gz"
    segy_path = tmp_path / "Model94_shots.segy"
    urllib.request.urlretrieve(BP_URL, gz_path)
    with gzip.open(gz_path, "rb") as f_in, open(segy_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    block = seg.segy_read(str(segy_path))
    assert block.fileheader.bfh.dt > 0
    assert block.fileheader.bfh.ns > 0
    assert len(block.traceheaders) > 0

