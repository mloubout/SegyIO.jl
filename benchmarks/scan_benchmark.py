import os
import time
import asyncio

import pysegy as seg

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PATTERN = 'overthrust_2D_shot_*.segy'
FILES = [
    os.path.join(DATA_DIR, f)
    for f in os.listdir(DATA_DIR)
    if f.startswith('overthrust_2D_shot_')
]
FILES.sort()


async def main():
    t0 = time.perf_counter()
    seg.segy_scan(DATA_DIR, PATTERN, threads=1, workers=1)
    t1 = time.perf_counter()
    seg.segy_scan(DATA_DIR, PATTERN)
    t2 = time.perf_counter()
    await seg.segy_scan_async(DATA_DIR, PATTERN)
    t3 = time.perf_counter()
    print(f"Sequential: {t1 - t0:.3f}s")
    print(f"Threaded:   {t2 - t1:.3f}s")
    print(f"Async:      {t3 - t2:.3f}s")


if __name__ == '__main__':
    asyncio.run(main())
