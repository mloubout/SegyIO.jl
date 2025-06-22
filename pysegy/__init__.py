"""Minimal Python port of SegyIO.jl"""

from .types import (
    BinaryFileHeader,
    BinaryTraceHeader,
    FileHeader,
    SeisBlock,
)
from .read import read_fileheader, read_traceheader, read_file, segy_read
from .scan import segy_scan
from .write import write_fileheader, write_traceheader, write_block, segy_write

__all__ = [
    "BinaryFileHeader",
    "BinaryTraceHeader",
    "FileHeader",
    "SeisBlock",
    "read_fileheader",
    "read_traceheader",
    "read_file",
    "segy_read",
    "segy_scan",
    "write_fileheader",
    "write_traceheader",
    "write_block",
    "segy_write",
]
