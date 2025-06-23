import os

import pysegy as seg  # noqa: E402

DATAFILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "data",
    "overthrust_2D_shot_1_20.segy",
)


def test_segy_scan_directory_pattern():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    scan = seg.segy_scan(
        data_dir,
        "overthrust_2D_shot_*.segy",
        keys=["GroupX"],
    )
    assert isinstance(scan, seg.SegyScan)
    assert len(scan.shots) == 97
    assert len(set(scan.paths)) == 5
    idx = 0
    assert scan.paths[idx].endswith("overthrust_2D_shot_1_20.segy")
    assert scan.counts[idx] == 127
    assert scan.summary(idx)["GroupX"] == (100, 6400)
