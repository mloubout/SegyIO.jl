import os
import time

import pysegy as seg
from pysegy.scan import _scan_file

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PATTERN = 'overthrust_2D_shot_*.segy'
FILES = [
    os.path.join(DATA_DIR, f)
    for f in os.listdir(DATA_DIR)
    if f.startswith('overthrust_2D_shot_')
]
FILES.sort()


def scan_serial():
    scans = [_scan_file(f) for f in FILES]
    fh = scans[0].fileheader
    records = []
    for sc in scans:
        records.extend(sc.records)
    return seg.SegyScan(fh, records)


def main():
    t0 = time.perf_counter()
    scan_serial()
    t1 = time.perf_counter()
    seg.segy_scan(DATA_DIR, PATTERN)
    t2 = time.perf_counter()
    print(f"Sequential: {t1 - t0:.3f}s")
    print(f"Parallel:   {t2 - t1:.3f}s")


if __name__ == '__main__':
    main()
