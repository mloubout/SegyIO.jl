"""
Writing utilities for the minimal Python SEGY implementation.
"""

import struct
from typing import BinaryIO
from . import logger
from .types import (
    SeisBlock,
    FileHeader,
    BinaryTraceHeader,
    FH_BYTE2SAMPLE,
    TH_BYTE2SAMPLE,
    TH_INT32_FIELDS,
)
from .ibm import ieee_to_ibm


def write_fileheader(
    f: BinaryIO, fh: FileHeader, bigendian: bool = True
) -> None:
    """
    Write ``fh`` to ``f``.

    Parameters
    ----------
    f : BinaryIO
        Open binary file handle to write to.
    fh : FileHeader
        Header values to write.
    bigendian : bool, optional
        Write numbers in big-endian order when ``True``.
    """
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


def write_traceheader(
    f: BinaryIO, th: BinaryTraceHeader, bigendian: bool = True
) -> None:
    """
    Write a single trace header to ``f``.

    Parameters
    ----------
    f : BinaryIO
        Open file handle for output.
    th : BinaryTraceHeader
        Trace header values to write.
    bigendian : bool, optional
        Write numbers in big-endian order when ``True``.
    """
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


def write_block(f: BinaryIO, block: SeisBlock, bigendian: bool = True) -> None:
    """
    Write an entire :class:`SeisBlock` to ``f``.

    Parameters
    ----------
    f : BinaryIO
        File handle where the block will be written.
    block : SeisBlock
        Data to serialise.
    bigendian : bool, optional
        Write numbers in big-endian order when ``True``.
    """
    write_fileheader(f, block.fileheader, bigendian)
    ns = block.fileheader.bfh.ns
    dsf = block.fileheader.bfh.DataSampleFormat
    for i, hdr in enumerate(block.traceheaders):
        trace = [block.data[j][i] for j in range(ns)]
        write_traceheader(f, hdr, bigendian)
        if dsf == 1:
            converted = b"".join(ieee_to_ibm(float(x)) for x in trace)
            f.write(converted)
        else:
            fmt = ">%df" % ns if bigendian else "<%df" % ns
            f.write(struct.pack(fmt, *trace))


def segy_write(path: str, block: SeisBlock) -> None:
    """
    Convenience wrapper to write ``block`` to ``path``.

    Parameters
    ----------
    path : str
        Destination file path.
    block : SeisBlock
        Dataset to write to disk.
    """
    logger.info("Writing SEGY file %s", path)
    with open(path, "wb") as f:
        write_block(f, block)
    logger.info("Finished writing %s", path)
