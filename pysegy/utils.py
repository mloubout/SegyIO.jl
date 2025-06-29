"""
Utility helpers shared across the :mod:`pysegy` package.
"""

from typing import BinaryIO, Iterable, List, Union
from contextlib import contextmanager
import struct
from functools import lru_cache
import numpy as np

from .types import BinaryTraceHeader, SeisBlock
from .ibm import ibm_to_ieee_array, ieee_to_ibm

_RECSRC_FIELDS = {
    "SourceX",
    "SourceY",
    "GroupX",
    "GroupY",
    "CDPX",
    "CDPY",
}

_ELEV_FIELDS = {
    "RecGroupElevation",
    "SourceSurfaceElevation",
    "SourceDepth",
    "RecDatumElevation",
    "SourceDatumElevation",
    "SourceWaterDepth",
    "GroupWaterDepth",
}


def _check_scale(name: str) -> tuple[bool, str]:
    if name in _RECSRC_FIELDS:
        return True, "RecSourceScalar"
    if name in _ELEV_FIELDS:
        return True, "ElevationScalar"
    return False, ""


@lru_cache(maxsize=None)
def struct_fmt(size: int, bigendian: bool) -> str:
    """
    Return ``struct`` format for ``size`` byte integer.
    """
    return (">" if bigendian else "<") + ("i" if size == 4 else "h")


@lru_cache(maxsize=None)
def struct_obj(size: int, bigendian: bool) -> struct.Struct:
    """
    Return cached :class:`struct.Struct` instance for the given integer size.
    """
    return struct.Struct(struct_fmt(size, bigendian))


def unpack_int(buf: bytes, size: int, bigendian: bool) -> int:
    """
    Decode integer from ``buf`` with ``size`` bytes.
    """
    return struct_obj(size, bigendian).unpack(buf)[0]


def pack_int(value: int, size: int, bigendian: bool) -> bytes:
    """
    Encode ``value`` to bytes according to ``size`` and endianness.
    """
    return struct_obj(size, bigendian).pack(value)


def read_samples(buf: bytes, ns: int, datatype: int, bigendian: bool) -> np.ndarray:
    """
    Return ``ns`` samples from ``buf`` given the SEGY data type.
    """
    if datatype == 1:
        return ibm_to_ieee_array(buf, ns, bigendian)
    dtype = (">" if bigendian else "<") + "f4"
    return np.frombuffer(buf, dtype=dtype, count=ns)


def write_samples(
    f: BinaryIO, trace: Iterable[float], datatype: int, bigendian: bool
) -> None:
    """
    Write ``trace`` values to ``f`` according to the SEGY format.
    """
    if datatype == 1:
        f.write(b"".join(ieee_to_ibm(float(x)) for x in trace))
    else:
        fmt = (">" if bigendian else "<") + f"{len(trace)}f"
        f.write(struct.pack(fmt, *trace))


@contextmanager
def open_file(path: str, mode: str = "rb", fs=None):
    """
    Context manager opening ``path`` using ``fs`` when provided.
    """
    opener = fs.open if fs is not None else open
    with opener(path, mode) as fh:
        yield fh


def get_header(
    src: Union[SeisBlock, Iterable[BinaryTraceHeader]],
    name: str,
    *,
    scale: bool = True,
) -> List[float]:
    """
    Return values for ``name`` from ``src`` optionally applying scaling.
    """
    if isinstance(src, SeisBlock):
        headers = src.traceheaders
    else:
        headers = list(src)

    vals = [getattr(h, name) for h in headers]

    scalable, scale_name = _check_scale(name)
    if scale and scalable:
        scaled: List[float] = []
        for h, v in zip(headers, vals):
            fact = getattr(h, scale_name)
            if fact > 0:
                scaled.append(v * fact)
            elif fact < 0:
                scaled.append(v / abs(fact))
            else:
                scaled.append(v)
        return scaled
    return vals


__all__ = [
    "get_header",
    "open_file",
    "read_samples",
    "write_samples",
    "struct_fmt",
    "pack_int",
    "unpack_int",
]
