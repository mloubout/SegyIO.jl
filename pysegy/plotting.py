import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Sequence, Union

ArrayLike = Union[np.ndarray, Sequence[Sequence[float]]]


def _clip_limits(img: np.ndarray, perc: int = 95, positive: bool = False,
                 vmax: float | None = None) -> Tuple[float, float]:
    if positive:
        high = np.percentile(img, perc)
        high = vmax if vmax is not None else high
        return 0.0, high
    high = np.percentile(np.abs(img), perc)
    high = vmax if vmax is not None else high
    return -high, high


def _plot_with_units(
    image: ArrayLike,
    spacing: Tuple[float, float],
    *,
    perc: int = 95,
    cmap: str = "gray",
    vmax: float | None = None,
    origin: Tuple[float, float] = (0.0, 0.0),
    interp: str = "nearest",
    aspect: str | None = None,
    d_scale: float = 0.0,
    positive: bool = False,
    labels: Tuple[str, str] = ("X", "Depth"),
    cbar: bool = False,
    alpha: float | None = None,
    units: Tuple[str, str] = ("m", "m"),
    name: str = "",
    new_fig: bool = True,
    save: str | None = None,
):
    arr = np.asarray(image)
    nz, nx = arr.shape
    dz, dx = spacing
    oz, ox = origin
    if d_scale != 0:
        depth = np.arange(nz, dtype=float) ** d_scale
    else:
        depth = np.ones(nz, dtype=float)
    scaled = arr * depth[:, None]
    vmin, vmax = _clip_limits(scaled, perc, positive, vmax)
    extent = [ox, ox + (nx - 1) * dx, oz + (nz - 1) * dz, oz]
    if aspect is None:
        aspect = "auto"

    if new_fig:
        plt.figure()

    im = plt.imshow(
        scaled,
        vmin=vmin,
        vmax=vmax,
        cmap=cmap,
        aspect=aspect,
        interpolation=interp,
        extent=extent,
        alpha=alpha,
    )
    plt.xlabel(f"{labels[0]} [{units[0]}]")
    plt.ylabel(f"{labels[1]} [{units[1]}]")
    if name:
        plt.title(name)
    if cbar:
        plt.colorbar(im)
    if save:
        plt.savefig(save, bbox_inches="tight", dpi=150)
    return im


def plot_simage(
    image: ArrayLike,
    spacing: Tuple[float, float],
    **kw,
):
    kw.setdefault("cmap", "gray")
    kw.setdefault("name", "RTM")
    kw.setdefault("labels", ("X", "Depth"))
    kw.setdefault("units", ("m", "m"))
    return _plot_with_units(image, spacing, **kw)


def plot_velocity(
    image: ArrayLike,
    spacing: Tuple[float, float],
    **kw,
):
    kw.setdefault("cmap", "turbo")
    kw.setdefault("name", "Velocity")
    kw.setdefault("labels", ("X", "Depth"))
    kw.setdefault("units", ("m", "m"))
    kw.setdefault("positive", True)
    return _plot_with_units(image, spacing, **kw)


def plot_fslice(
    image: ArrayLike,
    spacing: Tuple[float, float],
    **kw,
):
    kw.setdefault("cmap", "seismic")
    kw.setdefault("name", "Frequency slice")
    kw.setdefault("labels", ("X", "X"))
    kw.setdefault("units", ("m", "m"))
    return _plot_with_units(image, spacing, **kw)


def plot_sdata(
    image: ArrayLike,
    spacing: Tuple[float, float],
    **kw,
):
    kw.setdefault("cmap", "gray")
    kw.setdefault("name", "Shot record")
    kw.setdefault("labels", ("Xrec", "T"))
    kw.setdefault("units", ("m", "s"))
    return _plot_with_units(image, spacing, **kw)


def wiggle_plot(
    data: ArrayLike,
    xrec: Sequence[float] | None = None,
    time_axis: Sequence[float] | None = None,
    *,
    t_scale: float = 1.5,
    new_fig: bool = True,
):
    arr = np.asarray(data)
    if xrec is None:
        xrec = np.arange(arr.shape[1])
    if time_axis is None:
        time_axis = np.arange(arr.shape[0])
    xrec = np.asarray(xrec)
    time_axis = np.asarray(time_axis)
    tg = time_axis ** t_scale
    dx = np.diff(xrec, prepend=xrec[0])
    if new_fig:
        plt.figure()
    plt.ylim(time_axis.max(), time_axis.min())
    plt.xlim(xrec.min(), xrec.max())
    for i, xr in enumerate(xrec):
        trace = tg * arr[:, i]
        if np.max(np.abs(trace)) != 0:
            trace = dx[i] * trace / np.max(np.abs(trace)) + xr
        else:
            trace = trace + xr
        plt.plot(trace, time_axis, "k-", linewidth=0.5)
        plt.fill_betweenx(time_axis, xr, trace, where=trace > xr, color="k")
    plt.xlabel("X")
    plt.ylabel("Time")


def compare_shots(
    shot1: ArrayLike,
    shot2: ArrayLike,
    spacing: Tuple[float, float],
    *,
    cmap: Sequence[str] | str = "gray",
    side_by_side: bool = False,
    chunksize: int = 20,
    **kw,
):
    arr1 = np.asarray(shot1)
    arr2 = np.asarray(shot2)
    if isinstance(cmap, str):
        cmap = (cmap, cmap)
    if side_by_side:
        pad = np.zeros((arr1.shape[0], 5))
        combo = np.hstack([arr1, pad, arr2[:, ::-1]])
        plot_sdata(combo, spacing, cmap=cmap[0], **kw)
        return

    nrec = min(arr1.shape[1], arr2.shape[1])
    out1 = np.zeros_like(arr1[:, :nrec])
    out2 = np.zeros_like(arr2[:, :nrec])
    for start in range(0, nrec, 2 * chunksize):
        out1[:, start:start + chunksize] = arr1[:, start:start + chunksize]
    for start in range(chunksize, nrec, 2 * chunksize):
        out2[:, start:start + chunksize] = arr2[:, start:start + chunksize]
    plot_sdata(out1, spacing, cmap=cmap[0], **kw)
    _plot_with_units(
        out2,
        spacing,
        cmap=cmap[1],
        new_fig=False,
        alpha=0.25,
        **kw,
    )
