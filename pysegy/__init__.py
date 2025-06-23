"""
Minimal Python port of SegyIO.jl
"""

from .types import (
    BinaryFileHeader,
    BinaryTraceHeader,
    FileHeader,
    SeisBlock,
)
from .read import (
    read_fileheader,
    read_traceheader,
    read_file,
    segy_read,
    segy_read_async,
)
from .scan import SegyScan, segy_scan, segy_scan_async
from .write import (
    write_fileheader,
    write_traceheader,
    write_block,
    segy_write,
    segy_write_async,
)

__all__ = [
    "BinaryFileHeader",
    "BinaryTraceHeader",
    "FileHeader",
    "SeisBlock",
    "SegyScan",
    "read_fileheader",
    "read_traceheader",
    "read_file",
    "segy_read",
    "segy_read_async",
    "segy_scan",
    "segy_scan_async",
    "write_fileheader",
    "write_traceheader",
    "write_block",
    "segy_write",
    "segy_write_async",
]
