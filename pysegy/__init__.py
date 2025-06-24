"""Minimal Python port of SegyIO.jl."""
# flake8: noqa

import logging


logger = logging.getLogger('pysegy')
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)

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
)
from .scan import SegyScan, segy_scan, save_scan, load_scan
from .write import (
    write_fileheader,
    write_traceheader,
    write_block,
    segy_write,
)
from .utils import get_header

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
    "segy_scan",
    "save_scan",
    "load_scan",
    "write_fileheader",
    "write_traceheader",
    "write_block",
    "segy_write",
    "get_header",
]

logging.basicConfig(level=logging.INFO)
