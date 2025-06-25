"""
Helpers for scanning SEGY files by shot location.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import threading

import fnmatch
from dataclasses import dataclass, field
import struct
import numpy as np
import cloudpickle

from .read import read_fileheader, read_traceheader, read_traces
from .utils import get_header
from .types import (
    SeisBlock,
    FileHeader,
    BinaryTraceHeader,
    TH_BYTE2SAMPLE,
)


@dataclass
class ShotRecord:
    """Information about a single shot location within a SEGY file."""

    path: str
    coordinates: Tuple[float, float, float]
    fileheader: FileHeader
    rec_depth_key: str = "GroupWaterDepth"
    segments: List[Tuple[int, int]] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    ns: int = 0
    dt: int = 0
    fs: Any = field(default=None, repr=False)
    _data: Optional[np.ndarray] = field(default=None, init=False, repr=False)
    _headers: Optional[List[BinaryTraceHeader]] = field(
        default=None, init=False, repr=False
    )
    _rec_coords: Optional[np.ndarray] = field(
        default=None, init=False, repr=False
    )

    def __str__(self) -> str:
        lines = ["ShotRecord:"]
        lines.append(f"    path: {self.path}")
        lines.append(
            "    source: ("
            f"{self.coordinates[0]}, {self.coordinates[1]}, "
            f"{self.coordinates[2]}"
            ")"
        )
        lines.append(f"    traces: {sum(c for _, c in self.segments)}")
        lines.append(f"    ns: {self.ns}, dt: {self.dt}")
        if self.summary:
            lines.append("    summary:")
            for k, (mn, mx) in self.summary.items():
                lines.append(f"        {k:30s}: {mn}..{mx}")
        return "\n".join(lines)

    __repr__ = __str__

    def read_data(self, keys: Optional[Iterable[str]] = None) -> SeisBlock:
        """Load all traces for this shot."""
        data_parts = []
        for offset, count in self.segments:
            opener = self.fs.open if self.fs is not None else open
            with opener(self.path, "rb") as f:
                f.seek(offset)
                h, d = read_traces(
                    f,
                    self.fileheader.bfh.ns,
                    count,
                    self.fileheader.bfh.DataSampleFormat,
                    keys,
                )
                data_parts.append(d)
        return np.concatenate(data_parts, axis=0) if data_parts else []

    def read_headers(
        self, keys: Optional[Iterable[str]] = None
    ) -> List[BinaryTraceHeader]:
        """Read only the headers for this shot."""
        headers: List[BinaryTraceHeader] = []
        ns = self.fileheader.bfh.ns
        for offset, count in self.segments:
            opener = self.fs.open if self.fs is not None else open
            with opener(self.path, "rb") as f:
                f.seek(offset)
                for _ in range(count):
                    th = read_traceheader(f, keys)
                    headers.append(th)
                    f.seek(ns * 4, os.SEEK_CUR)
        return headers

    @property
    def data(self) -> SeisBlock:
        if self._data is None:
            self._data = self.read_data()
        return self._data

    @property
    def rec_coordinates(self) -> np.ndarray:
        """Array of receiver coordinates for this shot."""
        if self._rec_coords is None:
            hdrs = self.read_headers(
                keys=[
                    "GroupX",
                    "GroupY",
                    self.rec_depth_key,
                    "RecSourceScalar",
                    "ElevationScalar",
                ]
            )
            gx = get_header(hdrs, "GroupX")
            gy = get_header(hdrs, "GroupY")
            dz = get_header(hdrs, self.rec_depth_key)
            self._rec_coords = np.column_stack((gx, gy, dz)).astype(np.float32)
        return self._rec_coords


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
        offset, size = TH_BYTE2SAMPLE[k]
        fmt = ">i" if size == 4 else ">h"
        val = struct.unpack_from(fmt, buf, offset)[0]
        setattr(th, k, val)
    th.keys_loaded = list(keys)
    return th


def _update_summary(
    summary: Dict[str, Tuple[float, float]],
    th: BinaryTraceHeader,
    keys: Iterable[str],
) -> None:
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
        v = get_header([th], k)[0]
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

    def __init__(self, fh: FileHeader, records: List[ShotRecord], fs=None) -> None:
        """Create a new :class:`SegyScan` instance.

        Parameters
        ----------
        fh : FileHeader
            File header common to all files being scanned.
        records : list of ShotRecord
            Shot metadata describing trace segments.
        fs : filesystem-like object, optional
            Filesystem providing ``open`` for reading data lazily.
        """
        self.fileheader = fh
        self.records = records
        self.fs = fs
        self._data: Optional[List[SeisBlock]] = None

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
        return [r.coordinates for r in self.records]

    @property
    def offsets(self) -> List[int]:
        """First trace byte offset for every shot."""
        return [r.segments[0][0] for r in self.records]

    @property
    def counts(self) -> List[int]:
        """Total number of traces for each shot."""
        return [sum(c for _, c in r.segments) for r in self.records]

    def __getitem__(self, idx: int) -> ShotRecord:
        """Return the ``idx``-th :class:`ShotRecord`."""
        return self.records[idx]

    @property
    def data(self) -> List[SeisBlock]:
        """Load data for all shots on first access."""
        if self._data is None:
            self._data = [self.read_data(i) for i in range(len(self.records))]
        return self._data

    def summary(self, idx: int) -> dict:
        """Header summaries for the ``idx``-th shot."""
        return self.records[idx].summary

    def read_data(
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
            opener = rec.fs.open if rec.fs is not None else (
                self.fs.open if getattr(self, "fs", None) is not None else open
            )
            with opener(rec.path, "rb") as f:
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
            opener = rec.fs.open if rec.fs is not None else (
                self.fs.open if getattr(self, "fs", None) is not None else open
            )
            with opener(rec.path, "rb") as f:
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
    rec_depth_key: str = "GroupWaterDepth",
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
    rec_depth_key : str, optional
        Header field giving the receiver depth.

    fs : filesystem-like object, optional
        Filesystem providing ``open`` if reading from non-local storage.

    Returns
    -------
    SegyScan
        Object describing all shots found in ``path``.
    """
    thread = threading.current_thread().name
    print(f"{thread} scanning file {path}")
    trace_keys = [
        "SourceX",
        "SourceY",
        depth_key,
        "GroupX",
        "GroupY",
        rec_depth_key,
        "RecSourceScalar",
        "ElevationScalar",
    ]
    if keys is not None:
        for k in keys:
            if k not in trace_keys:
                trace_keys.append(k)

    opener = fs.open if fs is not None else open

    with opener(path, "rb") as f:
        fh = read_fileheader(f)
        print(f"Header for {path}: ns={fh.bfh.ns} dt={fh.bfh.dt}")
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
            src = (
                np.float32(get_header([th], "SourceX")[0]),
                np.float32(get_header([th], "SourceY")[0]),
                np.float32(get_header([th], depth_key)[0]),
            )

            rec = records.get(src)
            if rec is None:
                rec = ShotRecord(
                    path,
                    src,
                    fh,
                    rec_depth_key,
                    [],
                    {},
                    ns,
                    fh.bfh.dt,
                    fs,
                )
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

    record_list = sorted(records.values(), key=lambda r: r.coordinates)
    print(f"{thread} found {len(record_list)} shots in {path}")
    return SegyScan(fh, record_list, fs=fs)


def segy_scan(
    path: str,
    file_key: Optional[str] = None,
    keys: Optional[Iterable[str]] = None,
    chunk: int = 1024,
    depth_key: str = "SourceDepth",
    rec_depth_key: str = "GroupWaterDepth",
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
    rec_depth_key : str, optional
        Header field containing the receiver depth.
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

    print(
        f"Scanning {len(files)} files in {directory} with {threads} threads"
    )
    records: List[ShotRecord] = []
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {
            pool.submit(
                _scan_file, f, keys, chunk, depth_key, rec_depth_key, fs
            ): f
            for f in files
        }
        for fut in as_completed(futures):
            scan = fut.result()
            fh = scan.fileheader
            records.extend(scan.records)

    if not records:
        raise FileNotFoundError("No matching SEGY files found")

    records.sort(key=lambda r: r.coordinates)

    print(f"Combined scan has {len(records)} shots")
    return SegyScan(fh, records, fs=fs)


def save_scan(path: str, scan: SegyScan, fs=None) -> None:
    """Serialize ``scan`` to ``path``.

    Parameters
    ----------
    path : str
        Destination file path. When ``fs`` is provided the path is interpreted
        relative to that filesystem.
    scan : SegyScan
        Object to serialize.
    fs : filesystem-like object, optional
        Filesystem providing ``open`` when writing to non-local storage.
    """
    print(f"Saving SegyScan to {path}")
    opener = fs.open if fs is not None else open
    with opener(path, "wb") as f:
        cloudpickle.dump(scan, f, protocol=cloudpickle.DEFAULT_PROTOCOL)
    print(f"Finished saving {path}")


def load_scan(path: str, fs=None) -> SegyScan:
    """Load a :class:`SegyScan` previously saved with :func:`save_scan`.

    Parameters
    ----------
    path : str
        File system path of the saved object. When ``fs`` is provided the path
        is interpreted relative to that filesystem.
    fs : filesystem-like object, optional
        Filesystem providing ``open`` when reading from non-local storage.

    Returns
    -------
    SegyScan
        Deserialized scan object.
    """
    print(f"Loading SegyScan from {path}")
    opener = fs.open if fs is not None else open
    with opener(path, "rb") as f:
        scan = cloudpickle.load(f)

    # When loading from external storage the filesystem won't be part of the
    # serialized object. Attach it so lazy reads work correctly.
    if fs is not None:
        scan.fs = fs
        for rec in scan.records:
            rec.fs = fs

    print(f"Loaded SegyScan with {len(scan.records)} shots")
    return scan
