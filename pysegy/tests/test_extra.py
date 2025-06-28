import os
import importlib
import importlib.metadata
from io import BytesIO

import numpy as np
import pytest

import pysegy as seg
from pysegy.types import FileHeader, BinaryTraceHeader, SeisBlock, BinaryFileHeader

DATAFILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "overthrust_2D_shot_1_20.segy")


def test_package_not_found(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", lambda name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError()))
    importlib.reload(seg)
    assert seg.__version__ == "0+untagged"


def test_ibm_conversions():
    arr = np.array([1.0, -2.0, 0.0], dtype=np.float32)
    buf = b"".join(seg.ibm.ieee_to_ibm(float(x)) for x in arr)
    out = seg.ibm.ibm_to_ieee_array(buf, 3)
    assert out.shape == arr.shape
    assert seg.ibm.ieee_to_ibm(0.0) == b"\x00\x00\x00\x00"
    with pytest.raises(ValueError):
        seg.ibm.ibm_to_ieee(b"\x00\x00")
    assert seg.ibm.ibm_to_ieee(b"\x00\x00\x00\x00") == 0.0
    assert seg.ibm.ibm_to_ieee(0x41000000) == 0.0
    assert seg.ibm.ibm_to_ieee(0) == 0.0
    seg.ibm.ieee_to_ibm(-0.5)
    seg.ibm.ieee_to_ibm(32.0)
    seg.ibm.ieee_to_ibm(-0.5)


def test_get_header_no_scale():
    fh = FileHeader()
    fh.bfh.ns = 1
    th = BinaryTraceHeader()
    th.ns = 1
    block = SeisBlock(fh, [th], np.zeros((1, 1), dtype=np.float32))
    vals = seg.get_header(block, "ns")
    assert vals == [1]


def test_type_methods_roundtrip():
    bfh = BinaryFileHeader()
    bfh.keys_loaded = []
    bfh.Job = 5
    fh = FileHeader(bfh=bfh)
    th = BinaryTraceHeader()
    th.ns = 1
    block = SeisBlock(fh, [th], np.zeros((1, 1), dtype=np.float32))
    assert len(block) == 1
    assert "SeisBlock" in str(block)
    assert "BinaryFileHeader" in str(fh)
    assert "BinaryFileHeader" in str(bfh)
    assert "BinaryTraceHeader" in str(th)
    state = bfh.__getstate__()
    dup = BinaryFileHeader()
    dup.__setstate__(state)
    assert dup.values == bfh.values
    th_state = th.__getstate__()
    th2 = BinaryTraceHeader()
    th2.__setstate__(th_state)
    assert th2.values == th.values
    assert repr(th).startswith("BinaryTraceHeader")
    with pytest.raises(AttributeError):
        _ = bfh.nope
    with pytest.raises(AttributeError):
        BinaryTraceHeader().nope


def test_read_write_little_endian():
    fh = FileHeader()
    fh.th = b"HDR"
    fh.bfh.ns = 2
    fh.bfh.DataSampleFormat = 5
    th = BinaryTraceHeader()
    th.ns = 2
    th.SourceX = 42
    data = np.array([[1.0], [2.0]], dtype=np.float32)
    block = SeisBlock(fh, [th], data)
    bio = BytesIO()
    seg.write.write_block(bio, block, bigendian=False)
    bio.seek(0)
    out = seg.read.read_file(bio, bigendian=False)
    assert out.traceheaders[0].SourceX == 42
    np.testing.assert_allclose(out.data, data)


def test_read_write_ibm():
    fh = FileHeader()
    fh.bfh.ns = 1
    fh.bfh.DataSampleFormat = 1
    th = BinaryTraceHeader()
    th.ns = 1
    data = np.array([[3.0]], dtype=np.float32)
    block = SeisBlock(fh, [th], data)
    bio = BytesIO()
    seg.write.write_block(bio, block)
    bio.seek(0)
    out = seg.read.read_file(bio)
    assert out.data.shape == data.shape


import fsspec


def test_scan_utilities(tmp_path):
    fs = fsspec.filesystem("file")
    scan = seg.segy_scan(DATAFILE, keys=["GroupX", "Offset"], fs=fs)
    assert "SegyScan" in str(scan)
    rec = scan[0]
    assert "ShotRecord" in str(rec)
    assert len(scan) == len(scan.records)
    assert scan.offsets[0] >= 3600
    assert "summary" in str(rec)
    path = tmp_path / "scan.pkl"
    seg.save_scan(str(path), scan)
    loaded = seg.load_scan(str(path))
    assert len(loaded.records) == len(scan.records)


def test_scan_errors(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    fs = fsspec.filesystem("file")
    with pytest.raises(FileNotFoundError):
        seg.segy_scan(str(empty), fs=fs)

