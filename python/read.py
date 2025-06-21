"""Reading utilities for the minimal Python SEGY implementation."""

from .types import (
    BinaryFileHeader,
    BinaryTraceHeader,
    FileHeader,
    SeisBlock,
    FH_BYTE2SAMPLE,
    TH_BYTE2SAMPLE,
    TH_INT32_FIELDS,
)
from typing import BinaryIO, Iterable, List, Optional, Tuple

from .ibm import ibm_to_ieee
import struct


def read_fileheader(
    f: BinaryIO, keys: Optional[Iterable[str]] = None, bigendian: bool = True
) -> FileHeader:
    """Read and parse the binary file header from an open file object."""
    if keys is None:
        keys = list(FH_BYTE2SAMPLE.keys())
    start = f.tell()
    f.seek(0)
    text_header = f.read(3600)
    bfh = BinaryFileHeader()
    for k in keys:
        offset = FH_BYTE2SAMPLE[k]
        # all fields are 2 or 4 bytes integers
        size = 4 if k in ("Job", "Line", "Reel") else 2
        fmt = ">i" if size == 4 else ">h"
        if not bigendian:
            fmt = "<i" if size == 4 else "<h"
        val_bytes = text_header[offset:offset+size]
        val = struct.unpack(fmt, val_bytes)[0]
        setattr(bfh, k, val)
    f.seek(start)
    return FileHeader(text_header[:3200], bfh)


def read_traceheader(
    f: BinaryIO, keys: Optional[Iterable[str]] = None, bigendian: bool = True
) -> BinaryTraceHeader:
    """Read a single binary trace header from ``f``."""
    if keys is None:
        keys = list(TH_BYTE2SAMPLE.keys())
    hdr_bytes = f.read(240)
    th = BinaryTraceHeader()
    for k in keys:
        offset = TH_BYTE2SAMPLE[k]
        size = 4 if k in TH_INT32_FIELDS else 2
        fmt = ">i" if size == 4 else ">h"
        if not bigendian:
            fmt = "<i" if size == 4 else "<h"
        val = struct.unpack(fmt, hdr_bytes[offset : offset + size])[0]
        setattr(th, k, val)
    return th


def read_traces(
    f: BinaryIO,
    ns: int,
    ntraces: int,
    datatype: int,
    keys: Optional[Iterable[str]] = None,
    bigendian: bool = True,
) -> Tuple[List[BinaryTraceHeader], List[List[float]]]:
    """Read ``ntraces`` traces and their headers from ``f``."""
    data: List[List[float]] = [[0.0 for _ in range(ntraces)] for _ in range(ns)]
    headers: List[BinaryTraceHeader] = [BinaryTraceHeader() for _ in range(ntraces)]
    for i in range(ntraces):
        hdr = read_traceheader(f, keys, bigendian)
        headers[i] = hdr
        raw = f.read(ns * 4)
        if datatype == 1:  # IBM float
            traces = [ibm_to_ieee(raw[j : j + 4]) for j in range(0, ns * 4, 4)]
            for j, v in enumerate(traces):
                data[j][i] = v
        else:
            fmt = (">%df" % ns) if bigendian else ("<%df" % ns)
            vals = struct.unpack(fmt, raw)
            for j, v in enumerate(vals):
                data[j][i] = v
    return headers, data


def read_file(
    f: BinaryIO,
    warn_user: bool = True,
    keys: Optional[Iterable[str]] = None,
    bigendian: bool = True,
) -> SeisBlock:
    """Read a complete SEGY file from an open file handle."""
    fh = read_fileheader(f, bigendian=bigendian)
    ns = fh.bfh.ns
    dsf = fh.bfh.DataSampleFormat
    trace_size = 240 + ns * 4
    f.seek(0, 2)
    end = f.tell()
    ntraces = (end - 3600) // trace_size
    f.seek(3600)
    headers, data = read_traces(f, ns, ntraces, dsf, keys, bigendian)
    return SeisBlock(fh, headers, data)


def segy_read(path: str, keys: Optional[Iterable[str]] = None) -> SeisBlock:
    """Convenience wrapper to read a SEGY file from ``path``."""
    with open(path, "rb") as f:
        return read_file(f, keys=keys)
