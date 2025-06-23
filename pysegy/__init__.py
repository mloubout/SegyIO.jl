"""Minimal Python port of SegyIO.jl."""
# flake8: noqa

import logging

logger = logging.getLogger(__name__)

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
from .scan import SegyScan, segy_scan
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
    "write_fileheader",
    "write_traceheader",
    "write_block",
    "segy_write",
    "segy_write_async",
]

logging.basicConfig(level=logging.INFO)
