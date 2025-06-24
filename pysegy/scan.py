"""
Helpers for scanning SEGY files by shot location.
"""

from typing import Dict, Iterable, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import threading

import fnmatch
from dataclasses import dataclass, field
import struct
import numpy as np

from . import logger
from .read import read_fileheader, read_traceheader, read_traces
from .types import (
    SeisBlock,
    FileHeader,
    BinaryTraceHeader,
    TH_BYTE2SAMPLE,
    TH_INT32_FIELDS,
)


@dataclass
class ShotRecord:
    """
    Information about a single shot location within a SEGY file.
    """

    path: str
    shot: Tuple[int, int, int]
    segments: List[Tuple[int, int]] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    ns: int = 0
    dt: int = 0

    def __str__(self) -> str:
        lines = ["ShotRecord:"]
        lines.append(f"    path: {self.path}")
        lines.append(
            f"    source: ({self.shot[0]}, {self.shot[1]}, {self.shot[2]})"
        )
        lines.append(f"    traces: {sum(c for _, c in self.segments)}")
        lines.append(f"    ns: {self.ns}, dt: {self.dt}")
        if self.summary:
            lines.append("    summary:")
            for k, (mn, mx) in self.summary.items():
                lines.append(f"        {k:30s}: {mn}..{mx}")
        return "\n".join(lines)

    __repr__ = __str__


def _parse_header(buf: bytes, keys: Iterable[str]) -> BinaryTraceHeader:
    """
    Return a :class:`BinaryTraceHeader` parsed from ``buf``.

    Parameters
    ----------
    buf : bytes
        240-byte buffer containing the raw trace header.
    keys : Iterable[str]
        Header fields to decode from ``buf``.

    Returns
    -------
    BinaryTraceHeader
        Trace header populated with the requested fields.
    """
    th = BinaryTraceHeader()
    for k in keys:
        offset = TH_BYTE2SAMPLE[k]
        size = 4 if k in TH_INT32_FIELDS else 2
        fmt = ">i" if size == 4 else ">h"
        val = struct.unpack_from(fmt, buf, offset)[0]
        setattr(th, k, val)
    th.keys_loaded = list(keys)
    return th


def _update_summary(summary: Dict[str, Tuple[int, int]], th: BinaryTraceHeader,
                    keys: Iterable[str]) -> None:
    """
    Update ``summary`` with values from ``th``.

    Parameters
    ----------
    summary : dict
        Mapping of header name to ``(min, max)`` tuple.
    th : BinaryTraceHeader
        Header providing new values.
    keys : Iterable[str]
        Header fields to include in the summary.
    """
    for k in keys:
        v = getattr(th, k)
        if k in summary:
            mn, mx = summary[k]
            if v < mn:
                mn = v
            if v > mx:
                mx = v
            summary[k] = (mn, mx)
        else:
            summary[k] = (v, v)


def _iter_trace_headers(
    f,
    start: int,
    count: int,
    ns: int,
    keys: Iterable[str],
    chunk: int = 1024,
) -> Iterable[Tuple[int, BinaryTraceHeader]]:
    """
    Yield offsets and headers from ``f`` starting at ``start``.

    Parameters
    ----------
    f : file-like object
        Opened file positioned at ``start``.
    start : int
        Byte offset of the first trace.
    count : int
        Number of traces to read.
    ns : int
        Samples per trace.
    keys : Iterable[str]
        Header fields to decode.
    chunk : int, optional
        Number of traces to read per block.

    Yields
    ------
    tuple
        ``(offset, header)`` for each trace encountered.
    """
    trace_size = 240 + ns * 4
    pos = start
    remaining = count
    while remaining > 0:
        n = min(chunk, remaining)
        buf = f.read(trace_size * n)
        for i in range(n):
            base = i * trace_size
            hdr = _parse_header(buf[base:base + 240], keys)
            yield pos + base, hdr
        pos += n * trace_size
        remaining -= n


class SegyScan:
    """
    Representation of SEGY data grouped by shot.

    Parameters
    ----------
    fh : FileHeader
        File header shared by all scanned files.
    records : list of ShotRecord
        Collection of shot metadata describing trace segments.
    """

    def __init__(self, fh: FileHeader, records: List[ShotRecord]) -> None:
        """Create a new :class:`SegyScan` instance.

        Parameters
        ----------
        fh : FileHeader
            File header common to all files being scanned.
        records : list of ShotRecord
            Shot metadata describing trace segments.
        """
        self.fileheader = fh
        self.records = records

    def __len__(self) -> int:
        """Return the number of distinct shots."""
        return len(self.records)

    @property
    def paths(self) -> List[str]:
        """List of file paths corresponding to each shot."""
        return [r.path for r in self.records]

    @property
    def shots(self) -> List[Tuple[int, int, int]]:
        """Source coordinates for each shot including depth."""
        return [r.shot for r in self.records]

    @property
    def offsets(self) -> List[int]:
        """First trace byte offset for every shot."""
        return [r.segments[0][0] for r in self.records]

    @property
    def counts(self) -> List[int]:
        """Total number of traces for each shot."""
        return [sum(c for _, c in r.segments) for r in self.records]

    def summary(self, idx: int) -> dict:
        """Header summaries for the ``idx``-th shot."""
        return self.records[idx].summary

    def read_shot(
        self, idx: int, keys: Optional[Iterable[str]] = None
    ) -> SeisBlock:
        """
        Load all traces for a single shot.

        Parameters
        ----------
        idx : int
            Index of the shot to read.
        keys : Iterable[str], optional
            Additional header fields to load with each trace.

        Returns
        -------
        SeisBlock
            In-memory representation of the selected shot.
        """
        rec = self.records[idx]
        headers: List[BinaryTraceHeader] = []
        data_parts = []
        for offset, count in rec.segments:
            with open(rec.path, "rb") as f:
                f.seek(offset)
                h, d = read_traces(
                    f,
                    self.fileheader.bfh.ns,
                    count,
                    self.fileheader.bfh.DataSampleFormat,
                    keys,
                )
                headers.extend(h)
                data_parts.append(d)
        # Concatenate data parts if necessary
        if data_parts:
            data = np.concatenate(data_parts, axis=0)
        else:
            data = []
        return SeisBlock(self.fileheader, headers, data)

    def read_headers(
        self, idx: int, keys: Optional[Iterable[str]] = None
    ) -> List[BinaryTraceHeader]:
        """
        Read only the headers for a single shot.

        Parameters
        ----------
        idx : int
            Shot index to read.
        keys : Iterable[str], optional
            Header fields to populate; by default all are read.

        Returns
        -------
        list of BinaryTraceHeader
            Parsed headers for the requested shot.
        """
        rec = self.records[idx]
        headers: List[BinaryTraceHeader] = []
        ns = self.fileheader.bfh.ns
        for offset, count in rec.segments:
            with open(rec.path, "rb") as f:
                f.seek(offset)
                for _ in range(count):
                    th = read_traceheader(f, keys)
                    headers.append(th)
                    f.seek(ns * 4, os.SEEK_CUR)
        return headers

    def __str__(self) -> str:
        lines = ["SegyScan:"]
        lines.append(f"    shots: {len(self.records)}")
        lines.append(f"    ns: {self.fileheader.bfh.ns}")
        lines.append(f"    dt: {self.fileheader.bfh.dt}")
        return "\n".join(lines)

    __repr__ = __str__


def _scan_file(
    path: str,
    keys: Optional[Iterable[str]] = None,
    chunk: int = 1024,
    depth_key: str = "SourceDepth",
    fs=None,
) -> SegyScan:
    """
    Scan ``path`` for shot locations.

    Parameters
    ----------
    path : str
        SEGY file to scan.
    keys : Iterable[str], optional
        Additional header fields to summarise.
    chunk : int, optional
        Number of traces to read at once.
    depth_key : str, optional
        Trace header field giving the source depth.

    fs : filesystem-like object, optional
        Filesystem providing ``open`` if reading from non-local storage.

    Returns
    -------
    SegyScan
        Object describing all shots found in ``path``.
    """
    thread = threading.current_thread().name
    logger.info("%s scanning file %s", thread, path)
    trace_keys = ["SourceX", "SourceY", depth_key]
    if keys is not None:
        for k in keys:
            if k not in trace_keys:
                trace_keys.append(k)

    opener = fs.open if fs is not None else open

    with opener(path, "rb") as f:
        fh = read_fileheader(f)
        logger.info(
            "Header for %s: ns=%d dt=%d", path, fh.bfh.ns, fh.bfh.dt
        )
        ns = fh.bfh.ns
        f.seek(0, os.SEEK_END)
        total = (f.tell() - 3600) // (240 + ns * 4)
        f.seek(3600)

        records: Dict[Tuple[int, int, int], ShotRecord] = {}

        previous: Optional[Tuple[int, int, int]] = None
        seg_start = 0
        seg_count = 0

        for offset, th in _iter_trace_headers(
            f,
            3600,
            total,
            ns,
            trace_keys,
            chunk,
        ):
            src = (th.SourceX, th.SourceY, getattr(th, depth_key))

            rec = records.get(src)
            if rec is None:
                rec = ShotRecord(path, src, [], {}, ns, fh.bfh.dt)
                records[src] = rec
            _update_summary(rec.summary, th, keys or [])

            # New segment begins when the source position changes
            if previous is None:
                previous = src
                seg_start = offset
                seg_count = 1
            elif src == previous:
                seg_count += 1
            else:
                records[previous].segments.append((seg_start, seg_count))
                previous = src
                seg_start = offset
                seg_count = 1

        if previous is not None:
            # Append the final segment for the last shot
            records[previous].segments.append((seg_start, seg_count))

    record_list = sorted(records.values(), key=lambda r: r.shot)
    logger.info("%s found %d shots in %s", thread, len(record_list), path)
    return SegyScan(fh, record_list)


def segy_scan(
    path: str,
    file_key: Optional[str] = None,
    keys: Optional[Iterable[str]] = None,
    chunk: int = 1024,
    depth_key: str = "SourceDepth",
    threads: Optional[int] = None,
    fs=None,
) -> SegyScan:
    """
    Scan one or more SEGY files and merge the results.

    Parameters
    ----------
    path : str
        Directory containing SEGY files or a single file path.
    file_key : str, optional
        Glob pattern selecting files within ``path``. When omitted and
        ``path`` points to a file, only that file is scanned.
    keys : Iterable[str], optional
        Additional header fields to summarise while scanning.
    chunk : int, optional
        Number of traces to read per block.
    depth_key : str, optional
        Header name containing the source depth.
    fs : filesystem-like object, optional
        Filesystem providing ``open`` and ``glob`` if scanning non-local paths.

    Returns
    -------
    SegyScan
        Combined scan object describing all detected shots.
    """

    if threads is None:
        threads = os.cpu_count() or 1

    if file_key is None and (
        (fs is None and os.path.isfile(path)) or (fs and fs.isfile(path))
    ):
        files = [path]
        if fs is None:
            directory = os.path.dirname(path) or "."
        else:
            directory = getattr(fs, "_parent", os.path.dirname)(path)
    else:
        directory = path
        pattern = file_key or "*"
        if fs is None:
            files = [
                os.path.join(directory, fname)
                for fname in os.listdir(directory)
                if fnmatch.fnmatch(fname, pattern)
            ]
        else:
            files = fs.glob(f"{directory.rstrip('/')}/{pattern}")
    files.sort()

    logger.info(
        "Scanning %d files in %s with %d threads",
        len(files),
        directory,
        threads,
    )
    records: List[ShotRecord] = []
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {
            pool.submit(_scan_file, f, keys, chunk, depth_key, fs): f
            for f in files
        }
        for fut in as_completed(futures):
            scan = fut.result()
            fh = scan.fileheader
            file_path = futures[fut]
            logger.info("Completed scan of %s", file_path)
            records.extend(scan.records)

    if not records:
        raise FileNotFoundError("No matching SEGY files found")

    records.sort(key=lambda r: r.shot)

    logger.info("Combined scan has %d shots", len(records))
    return SegyScan(fh, records)
