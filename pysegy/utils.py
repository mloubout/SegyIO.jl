from typing import Iterable, List, Union

from .types import BinaryTraceHeader, SeisBlock

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


def get_header(
    src: Union[SeisBlock, Iterable[BinaryTraceHeader]],
    name: str,
    *,
    scale: bool = True,
) -> List[float]:
    """Return values for ``name`` from ``src`` optionally applying scaling."""
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


__all__ = ["get_header"]
