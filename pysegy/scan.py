from typing import List, Tuple
import os

from .read import read_fileheader, read_traceheader


def segy_scan(path: str):
    """Scan ``path`` for shot locations and trace counts."""
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

    return fh, shots, offsets, counts
