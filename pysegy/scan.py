"""Simple scanning utilities for SEGY files."""

from typing import BinaryIO, Iterable, List, Dict

from .types import FileHeader, BinaryTraceHeader, BlockScan, SeisCon
from .read import read_fileheader, read_traceheader


def scan_file(
    f: BinaryIO,
    keys: Iterable[str],
    blocksize: int,
    bigendian: bool = True,
) -> SeisCon:
    """Scan ``f`` for header fields in ``keys`` in blocks of ``blocksize`` traces."""
    fh = read_fileheader(f, bigendian=bigendian)
    ns = fh.bfh.ns
    dsf = fh.bfh.DataSampleFormat
    trace_size = 240 + ns * 4
    f.seek(0, 2)
    end = f.tell()
    ntraces = (end - 3600) // trace_size
    f.seek(3600)
    blocks: List[BlockScan] = []
    klist = list(keys)
    for start in range(0, ntraces, blocksize):
        start_byte = f.tell()
        count = min(blocksize, ntraces - start)
        summary: Dict[str, List[int]] = {k: [0, 0] for k in klist}
        first = True
        for _ in range(count):
            th = read_traceheader(f, klist, bigendian)
            for k in klist:
                val = getattr(th, k)
                if first:
                    summary[k][0] = val
                    summary[k][1] = val
                else:
                    if val < summary[k][0]:
                        summary[k][0] = val
                    if val > summary[k][1]:
                        summary[k][1] = val
            f.seek(ns * 4, 1)
            first = False
        end_byte = start_byte + trace_size * count
        blocks.append(BlockScan(getattr(f, "name", ""), start_byte, end_byte, summary))
    return SeisCon(ns, dsf, blocks)


def segy_scan(path: str, keys: Iterable[str], blocksize: int) -> SeisCon:
    """Convenience wrapper to scan ``path``."""
    with open(path, "rb") as f:
        return scan_file(f, keys, blocksize)
