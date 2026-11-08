"""Ready-made plots of the package's objects (needs matplotlib: ``pip install pyssms[plot]``).

Each function draws on a given ``matplotlib`` axes (or makes one) and returns it. They draw what
the data are, with no decoration that carries a claim: the polygon ``K`` in the plane of the two
arrival times, the disturbance set ``D`` with the signed margin, the time profile of the
indicators of one encounter, and the severity hierarchy of a recording.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pyssms.disturbance import DisturbanceSet
from pyssms.geometry import FloatArray
from pyssms.hierarchy import plot_hierarchy
from pyssms.process import Encounter
from pyssms.timetime import conflict_polygon, indicators

__all__ = [
    "plot_conflict_polygon",
    "plot_disturbance_set",
    "plot_hierarchy",
    "plot_indicator_profile",
]

_STATE_COLOUR = {"A": "#d62728", "B": "#ff7f0e", "C": "#7f7f7f"}


def _axes(ax: Any, figsize: tuple[float, float] = (5.0, 4.5)) -> Any:
    if ax is not None:
        return ax
    import matplotlib.pyplot as plt  # lazy: optional dependency

    return plt.subplots(figsize=figsize)[1]


def plot_conflict_polygon(
    shape1: FloatArray,
    pos1: Any,
    vel1: Any,
    shape2: FloatArray,
    pos2: Any,
    vel2: Any,
    horizon: float = 10.0,
    ax: Any = None,
) -> Any:
    """Draw the conflict polygon ``K`` of one encounter with the diagonal ``tau1 = tau2``.

    ``tau1`` and ``tau2`` are the times at which road users 1 and 2 reach their positions of
    contact (the plane of the two clocks). If ``K`` meets the diagonal the road users are on a
    collision course (state A) and TTC is where it first does; otherwise the shortest horizontal
    or vertical distance to the diagonal is the Time Advantage. Arguments as in
    :func:`pyssms.timetime.conflict_polygon`; the title gives the indicators.
    """
    from matplotlib.patches import Polygon

    ax = _axes(ax)
    poly = conflict_polygon(shape1, pos1, vel1, shape2, pos2, vel2, horizon=60.0)
    ind = indicators(
        shape1[:1], np.atleast_2d(pos1), np.atleast_2d(vel1), shape2[:1], np.atleast_2d(pos2),
        np.atleast_2d(vel2), horizon=horizon,
    )  # fmt: skip
    state = str(ind.state[0])
    if len(poly) >= 3:
        ax.add_patch(
            Polygon(poly, closed=True, fc=_STATE_COLOUR[state], ec="k", alpha=0.35, label="$K$")
        )
        hi = float(max(float(np.max(poly)), horizon))
    else:
        hi = horizon
    ax.plot([0, hi], [0, hi], color="k", lw=0.9, ls="--", label=r"$\tau_1=\tau_2$")
    ax.set_xlim(0, hi)
    ax.set_ylim(0, hi)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(r"$\tau_1$ (s)")
    ax.set_ylabel(r"$\tau_2$ (s)")
    ttc, tadv = float(ind.ttc[0]), float(ind.tadv[0])
    txt = f"state {state}; TTC {ttc:.2f} s" if state == "A" else f"state {state}; TAdv {tadv:.2f} s"
    ax.set_title(txt, fontsize=10)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    return ax


def plot_disturbance_set(
    d: DisturbanceSet,
    index: int = 0,
    sigma_delta: float = 1.0,
    sigma_eps: float = 1.0,
    ax: Any = None,
) -> Any:
    """Draw the disturbance set ``D`` of encounter ``index`` in scaled coordinates.

    Axes are the time shift ``delta`` and the sideways shift ``eps`` divided by their scales; the
    dotted circle has the radius of the signed margin ``beta`` (positive outside ``D``, negative
    inside). A state C encounter has an empty ``D``: only the origin is drawn.
    """
    from matplotlib.patches import Polygon

    ax = _axes(ax)
    ax.axhline(0, color="#999", lw=0.6)
    ax.axvline(0, color="#999", lw=0.6)
    ax.plot(0, 0, "ko", ms=5, label="undisturbed encounter")
    if not bool(d.empty[index]):
        poly = d.vertices(index) / np.array([sigma_delta, sigma_eps])
        if len(poly) >= 3:
            ax.add_patch(Polygon(poly, closed=True, fc="#9aa5b1", ec="k", alpha=0.5, label="$D$"))
        beta = float(d.signed_margin(sigma_delta, sigma_eps)[index])
        if np.isfinite(beta):
            th = np.linspace(0, 2 * np.pi, 200)
            r = abs(beta)
            ax.plot(
                r * np.cos(th), r * np.sin(th), ls=":", color="k", label=rf"$|\beta|$ = {r:.2f}"
            )
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale_view()
    ax.set_xlabel(r"$\delta/\sigma_\delta$ (scaled time shift)")
    ax.set_ylabel(r"$\varepsilon/\sigma_\varepsilon$ (scaled sideways shift)")
    ax.legend(loc="best", fontsize=8, frameon=False)
    return ax


def plot_indicator_profile(enc: Encounter, ax: Any = None) -> Any:
    """Time profile of TTC, TAdv and T2 of one encounter, shaded by state (A, B, C)."""
    ax = _axes(ax, (6.5, 3.6))
    t = enc.t
    for lv in ("A", "B", "C"):
        m = enc.state == lv
        if not m.any():
            continue
        edges = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
        for s, e in zip(edges[::2], edges[1::2], strict=True):
            ax.axvspan(t[s], t[min(e, t.size - 1)], color=_STATE_COLOUR[lv], alpha=0.12, lw=0)
    ax.plot(t, enc.ttc, label="TTC", color="#d62728")
    ax.plot(t, enc.tadv, label="TAdv", color="#ff7f0e")
    ax.plot(t, enc.t2, label="T2", color="#1f77b4")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("s")
    ax.set_title(f"pair {enc.a}-{enc.b}: red = collision course, orange = crossing, grey = none",
                 fontsize=9)  # fmt: skip
    ax.legend(fontsize=8, frameon=False)
    return ax
