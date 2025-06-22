from typing import List, Tuple, Iterable, Optional
import os

from .read import read_fileheader, read_traceheader, read_traces
from .types import SeisBlock, FileHeader


class SegyScan:
    """Lazy representation of a SEGY file grouped by shot location."""

    def __init__(self, path: str, fh: FileHeader,
                 shots: List[Tuple[int, int]],
                 offsets: List[int], counts: List[int]):
        self.path = path
        self.fileheader = fh
        self.shots = shots
        self.offsets = offsets
        self.counts = counts

    def __len__(self) -> int:
        return len(self.shots)

    def read_shot(self, idx: int, keys: Optional[Iterable[str]] = None) -> SeisBlock:
        """Read traces for shot ``idx`` from the dataset."""
        offset = self.offsets[idx]
        ntr = self.counts[idx]
        with open(self.path, "rb") as f:
            f.seek(offset)
            headers, data = read_traces(
                f,
                self.fileheader.bfh.ns,
                ntr,
                self.fileheader.bfh.DataSampleFormat,
                keys,
            )
        return SeisBlock(self.fileheader, headers, data)


def segy_scan(path: str) -> SegyScan:
    """Scan ``path`` for shot locations without loading trace data."""
    with open(path, "rb") as f:
        fh = read_fileheader(f)
        ns = fh.bfh.ns
        trace_size = 240 + ns * 4
        f.seek(0, os.SEEK_END)
        total = (f.tell() - 3600) // trace_size
        f.seek(3600)

        shots: List[Tuple[int, int]] = []
        offsets: List[int] = []
        counts: List[int] = []

        current = None
        count = 0
        pos = 3600
        for _ in range(total):
            th = read_traceheader(f)
            src = (th.SourceX, th.SourceY)
            if current is None:
                current = src
                offsets.append(pos)
            elif src != current:
                shots.append(current)
                counts.append(count)
                current = src
                offsets.append(pos)
                count = 0
            count += 1
            f.seek(ns * 4, os.SEEK_CUR)
            pos += trace_size
        if current is not None:
            shots.append(current)
            counts.append(count)

    return SegyScan(path, fh, shots, offsets, counts)
