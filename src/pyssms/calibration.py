"""Scales of the constant-velocity prediction error, estimated from unhindered road users.

The disturbance set of :mod:`pyssms.disturbance` needs two scales: ``sigma_delta`` (s), the spread
of the *timing* error of a constant-velocity prediction, and ``sigma_eps`` (m), the spread of the
*sideways* error. :func:`calibrate_scales` estimates both from trajectories in which nobody
interacts with the road user (an *unhindered* set, :func:`unhindered_ids`), as a function of the
prediction horizon ``tau``:

* take each moving road user at time ``t`` with position ``p``, velocity ``v`` and heading
  ``u = v/|v|``;
* predict ``p + v tau`` and compare with the realised position ``p(t + tau)``;
* split the error into the part along ``u`` (``e_L``) and across it (``e_T``);
* timing error ``delta = -e_L / |v|`` (s; positive when the road user is later than predicted),
  sideways error ``eps = e_T`` (m);
* report the root-mean-square (``robust=False``) or the median-absolute-deviation scale
  (``robust=True``, 1.4826 x MAD about the median) of each over all samples.

This is one concrete definition of the scales, not a validated one: whether a spread estimated this
way is the right standardiser for a margin is the open question of ``docs/beta_proposal.md``. The
result depends on who is in the unhindered set; with data of a signalised intersection, stopping at
a red light is mistaken for a timing error unless those road users are excluded.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from pyssms.geometry import FloatArray, IntArray
from pyssms.trajectories import Trajectories

__all__ = ["Scales", "calibrate_scales", "unhindered_ids"]


@dataclass(frozen=True)
class Scales:
    """Scales of the prediction error per horizon.

    Attributes:
        tau: Prediction horizons (s).
        sigma_delta: Timing scale (s) per horizon.
        sigma_eps: Sideways scale (m) per horizon.
        n: Number of samples per horizon.
    """

    tau: FloatArray
    sigma_delta: FloatArray
    sigma_eps: FloatArray
    n: IntArray

    def at(self, tau: float) -> tuple[float, float]:
        """``(sigma_delta, sigma_eps)`` linearly interpolated at ``tau`` (clamped to the range)."""
        ok = np.isfinite(self.sigma_delta) & np.isfinite(self.sigma_eps)
        if not ok.any():
            return float("nan"), float("nan")
        return (
            float(np.interp(tau, self.tau[ok], self.sigma_delta[ok])),
            float(np.interp(tau, self.tau[ok], self.sigma_eps[ok])),
        )


def unhindered_ids(
    traj: Trajectories, min_gap: float = 15.0, min_duration: float = 2.0, min_speed: float = 1.0
) -> IntArray:
    """Ids of road users that never come within ``min_gap`` m (centres) of another one.

    Only road users observed for at least ``min_duration`` seconds and moving faster than
    ``min_speed`` m/s at least half of that time are returned. The rule is a proxy for "not
    interacting"; it also removes dense traffic, so the set can be biased toward free flow.
    """
    ts = traj.times
    key = np.searchsorted(ts, traj.t)
    order = np.argsort(key, kind="stable")
    bounds = np.searchsorted(key[order], np.arange(ts.size + 1))
    near: set[int] = set()
    for k in range(ts.size):
        rows = order[bounds[k] : bounds[k + 1]]
        if rows.size < 2:
            continue
        x, y = traj.x[rows], traj.y[rows]
        d = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
        np.fill_diagonal(d, np.inf)
        near.update(int(u) for u in traj.uid[rows[(d < min_gap).any(axis=1)]])
    keep = []
    for u in traj.ids:
        if int(u) in near:
            continue
        tr = traj.track(int(u))
        if len(tr) < 2 or tr.t[-1] - tr.t[0] < min_duration:
            continue
        if np.mean(np.hypot(tr.vx, tr.vy) > min_speed) < 0.5:
            continue
        keep.append(int(u))
    return np.array(keep, dtype=np.int64)


def _spread(v: FloatArray, robust: bool) -> float:
    if v.size < 2:
        return float("nan")
    if robust:
        return float(1.4826 * np.median(np.abs(v - np.median(v))))
    return float(np.sqrt(np.mean(v**2)))


def calibrate_scales(
    traj: Trajectories,
    ids: IntArray | Sequence[int] | None = None,
    taus: Sequence[float] = (0.5, 1.0, 2.0, 3.0, 4.0),
    min_speed: float = 1.0,
    robust: bool = False,
) -> Scales:
    """Estimate ``sigma_delta(tau)`` and ``sigma_eps(tau)`` from (unhindered) trajectories.

    Args:
        traj: Trajectories sampled at a regular interval.
        ids: Road users to use; default all (pass :func:`unhindered_ids` for free-flow scales).
        taus: Prediction horizons (s); each is rounded to a whole number of frames.
        min_speed: Samples with a lower speed are skipped (heading and timing are undefined).
        robust: Use the MAD-based scale instead of the root-mean-square.

    Returns:
        :class:`Scales` (``NaN`` where fewer than two samples exist).
    """
    dt = traj.dt
    use = traj.ids if ids is None else np.asarray(ids, dtype=np.int64)
    e_long: dict[float, list[FloatArray]] = {tau: [] for tau in taus}
    e_lat: dict[float, list[FloatArray]] = {tau: [] for tau in taus}
    for u in use:
        tr = traj.track(int(u))
        sp = np.hypot(tr.vx, tr.vy)
        for tau in taus:
            k = int(round(tau / dt))
            if k < 1 or len(tr) <= k:
                continue
            ex = tr.x[k:] - (tr.x[:-k] + tr.vx[:-k] * (k * dt))
            ey = tr.y[k:] - (tr.y[:-k] + tr.vy[:-k] * (k * dt))
            s = sp[:-k]
            ok = s >= min_speed
            ux, uy = tr.vx[:-k][ok] / s[ok], tr.vy[:-k][ok] / s[ok]
            long = ex[ok] * ux + ey[ok] * uy
            lat = -ex[ok] * uy + ey[ok] * ux
            e_long[tau].append(-long / s[ok])  # timing error: behind prediction = later
            e_lat[tau].append(lat)
    sd, se, n = [], [], []
    for tau in taus:
        d = np.concatenate(e_long[tau]) if e_long[tau] else np.empty(0)
        e = np.concatenate(e_lat[tau]) if e_lat[tau] else np.empty(0)
        sd.append(_spread(d, robust))
        se.append(_spread(e, robust))
        n.append(int(d.size))
    return Scales(
        tau=np.array(taus, dtype=float),
        sigma_delta=np.array(sd),
        sigma_eps=np.array(se),
        n=np.array(n, dtype=np.int64),
    )
