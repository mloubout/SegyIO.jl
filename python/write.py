import struct
from .types import (
    SeisBlock,
    FileHeader,
    BinaryTraceHeader,
    FH_BYTE2SAMPLE,
    TH_BYTE2SAMPLE,
    TH_INT32_FIELDS,
)
from .ibm import ieee_to_ibm


def write_fileheader(f, fh: FileHeader, bigendian=True):
    th = fh.th
    if len(th) < 3200:
        th = th + b" " * (3200 - len(th))
    f.write(th[:3200])
    bfh = fh.bfh
    size_written = 3200
    for key in FH_BYTE2SAMPLE:
        val = getattr(bfh, key)
        size = 4 if key in ("Job", "Line", "Reel") else 2
        fmt = ">i" if size == 4 else ">h"
        if not bigendian:
            fmt = "<i" if size == 4 else "<h"
        f.write(struct.pack(fmt, val))
        size_written += size
    pad = 3600 - size_written
    if pad > 0:
        f.write(b"\x00" * pad)


def write_traceheader(f, th: BinaryTraceHeader, bigendian=True):
    buf = bytearray(240)
    for key in TH_BYTE2SAMPLE:
        val = getattr(th, key)
        offset = TH_BYTE2SAMPLE[key]
        size = 4 if key in TH_INT32_FIELDS else 2
        fmt = ">i" if size == 4 else ">h"
        if not bigendian:
            fmt = "<i" if size == 4 else "<h"
        struct.pack_into(fmt, buf, offset, val)
    f.write(buf)


def write_block(f, block: SeisBlock, bigendian=True):
    write_fileheader(f, block.fileheader, bigendian)
    ns = block.fileheader.bfh.ns
    dsf = block.fileheader.bfh.DataSampleFormat
    ntraces = len(block.traceheaders)
    for i, hdr in enumerate(block.traceheaders):
        trace = [block.data[j][i] for j in range(ns)]
        write_traceheader(f, hdr, bigendian)
        if dsf == 1:
            converted = b"".join(ieee_to_ibm(float(x)) for x in trace)
            f.write(converted)
        else:
            fmt = ">%df" % ns if bigendian else "<%df" % ns
            f.write(struct.pack(fmt, *trace))


def segy_write(path, block: SeisBlock):
    with open(path, 'wb') as f:
        write_block(f, block)
