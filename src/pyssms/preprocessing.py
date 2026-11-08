"""Smoothing of trajectories, causal or centred, before indicators are computed.

Video- and drone-based trajectories carry measurement noise, and velocities or accelerations
obtained from them carry more (NGSIM is the well-known case, see ``docs/ngsim_notes.md``). Two
choices are offered and the difference matters:

* ``causal=True`` (default): the smoothed value at time ``t`` uses only samples up to ``t``
  (a trailing mean). This is what an on-line indicator could have known, and what a *pre-onset*
  validation needs (no information from the future leaks into the indicator). Its price is a
  **lag** of ``(window - 1) / 2`` frames: the smoothed position trails the true one, and a
  time-to-collision computed from it is slightly late.
* ``causal=False``: a centred mean, no lag, but each value uses future samples. Fine for a
  description of what happened, not for questions about what could have been foreseen.

Neither choice is claimed to be the best filter; both are simple, transparent baselines. The
package does not ship a filter tuned to one data set.
"""

from __future__ import annotations

import numpy as np

from pyssms.geometry import FloatArray
from pyssms.trajectories import Trajectories

__all__ = ["moving_average", "smooth_trajectories"]


def moving_average(values: FloatArray, window: int = 5, causal: bool = True) -> FloatArray:
    """Mean over ``window`` samples of one series (equally spaced), same length as the input.

    With ``causal=True`` the value at ``i`` is the mean of samples ``i-window+1 .. i`` (fewer at
    the start of the series: the window is truncated, never padded). With ``causal=False`` it is
    the centred mean of ``i-h .. i+h`` (``window`` must then be odd; ``h = (window-1)//2``),
    truncated at both ends.

    Args:
        values: One-dimensional series.
        window: Number of samples (>= 1).
        causal: Trailing (``True``) or centred (``False``) window.

    Returns:
        The smoothed series.
    """
    v = np.asarray(values, dtype=float)
    if window < 1:
        raise ValueError("window must be at least 1")
    if not causal and window % 2 == 0:
        raise ValueError("a centred window must be odd")
    if window == 1 or v.size == 0:
        out0: FloatArray = v.copy()
        return out0
    c = np.concatenate(([0.0], np.cumsum(v)))
    i = np.arange(v.size)
    if causal:
        lo, hi = np.maximum(i - window + 1, 0), i + 1
    else:
        h = (window - 1) // 2
        lo, hi = np.maximum(i - h, 0), np.minimum(i + h + 1, v.size)
    out: FloatArray = np.asarray((c[hi] - c[lo]) / (hi - lo), dtype=float)
    return out


def smooth_trajectories(
    traj: Trajectories,
    window: int = 5,
    causal: bool = True,
    min_heading_speed: float = 1.0,
) -> Trajectories:
    """Smooth the positions of every road user and re-derive velocity and heading from them.

    Positions ``x`` and ``y`` are smoothed with :func:`moving_average`. The velocity is then the
    backward difference of the smoothed positions (``causal=True``: uses only the past) or the
    central difference (``causal=False``). The heading becomes the direction of that velocity
    where the speed is at least ``min_heading_speed`` and is kept from the input elsewhere.
    Sizes, classes and ids are unchanged. Rows need not be sorted; each road user's series is
    ordered by time and must be sampled at equal steps.

    Args:
        traj: Input trajectories.
        window: Number of samples of the mean (odd if ``causal=False``).
        causal: See the module docstring.
        min_heading_speed: Speed (m/s) below which the input heading is kept.

    Returns:
        A new :class:`~pyssms.trajectories.Trajectories`; ``meta`` records the filter.
    """
    n = len(traj)
    x, y = traj.x.copy(), traj.y.copy()
    vx, vy, heading = traj.vx.copy(), traj.vy.copy(), traj.heading.copy()
    order = np.lexsort((traj.t, traj.uid))
    us = traj.uid[order]
    starts = np.flatnonzero(np.r_[True, us[1:] != us[:-1]])
    stops = np.r_[starts[1:], n]
    for s0, s1 in zip(starts, stops, strict=True):
        idx = order[s0:s1]
        if idx.size < 2:
            continue
        t = traj.t[idx]
        xs = moving_average(traj.x[idx], window, causal)
        ys = moving_average(traj.y[idx], window, causal)
        if causal:
            dt = np.diff(t)
            ax = np.r_[0.0, np.diff(xs) / dt]
            ay = np.r_[0.0, np.diff(ys) / dt]
            ax[0], ay[0] = ax[1], ay[1]
        else:
            ax, ay = np.gradient(xs, t), np.gradient(ys, t)
        moving = np.hypot(ax, ay) >= min_heading_speed
        x[idx], y[idx], vx[idx], vy[idx] = xs, ys, ax, ay
        heading[idx] = np.where(moving, np.arctan2(ay, ax), traj.heading[idx])
    meta = dict(traj.meta)
    meta["smoothing"] = {"window": window, "causal": causal}
    return Trajectories(
        t=traj.t, uid=traj.uid, x=x, y=y, heading=heading, vx=vx, vy=vy, length=traj.length,
        width=traj.width, kind=traj.kind, source=traj.source, meta=meta,
    )  # fmt: skip
