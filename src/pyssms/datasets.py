"""Synthetic standard scenarios for trying every function without any data file.

These are **generated, not measured**: simple kinematic stories (constant speeds, one braking event)
with random offsets, meant for examples, tests and teaching. They say nothing about real traffic.
The LevelX data sets (inD, highD, rounD, exiD, uniD) may be used only under the licence granted to
each user and must not be redistributed; load them with :func:`pyssms.io.read_levelx`. The one real
data set that is shipped, as short windows around the most severe encounters, is NGSIM
(:func:`load_conflict_bank`; read the licence note in :mod:`pyssms.bank`).

All scenarios have a sampling interval of 0.04 s (25 Hz) and are returned as
:class:`~pyssms.trajectories.Trajectories`. Pairs of road users are separated in time (one pair
every ``spacing`` seconds) so that each pair is an independent encounter.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from pyssms.bank import available_banks, load_conflict_bank, load_summary
from pyssms.geometry import FloatArray
from pyssms.trajectories import Trajectories, from_arrays

__all__ = [
    "SCENARIOS",
    "available_banks",
    "crossing",
    "following",
    "load_conflict_bank",
    "load_summary",
    "make",
    "merge",
    "pedestrian",
    "roundabout",
]

DT = 0.04
CAR = (4.5, 1.8)
PED = (0.5, 0.5)
V0 = 25.0  # initial speed in the car-following scenario (m/s)


class _Builder:
    """Collects the rows of the road users of one scenario."""

    def __init__(self) -> None:
        self.rows: dict[str, list[Any]] = {k: [] for k in "t uid x y length width kind".split()}
        self.next_id = 0

    def add(self, t: FloatArray, x: FloatArray, y: FloatArray, size: tuple[float, float],
            kind: str) -> int:  # fmt: skip
        uid = self.next_id
        self.next_id += 1
        n = t.size
        self.rows["t"].append(t)
        self.rows["uid"].append(np.full(n, uid))
        self.rows["x"].append(x)
        self.rows["y"].append(y)
        self.rows["length"].append(np.full(n, size[0]))
        self.rows["width"].append(np.full(n, size[1]))
        self.rows["kind"].append(np.full(n, kind))
        return uid

    def build(self, source: str) -> Trajectories:
        cat = {k: np.concatenate(v) for k, v in self.rows.items()}
        return from_arrays(**cat, source=f"synthetic: {source}", meta={"synthetic": True})


def _line(
    t0: float,
    dur: float,
    p0: tuple[float, float],
    heading: float,
    speed: Callable[[FloatArray], FloatArray],
) -> tuple[FloatArray, FloatArray, FloatArray]:
    t = np.asarray(np.arange(t0, t0 + dur, DT), dtype=float)
    s = np.cumsum(speed(t - t0)) * DT
    s -= s[0]
    x = np.asarray(p0[0] + s * np.cos(heading), dtype=float)
    y = np.asarray(p0[1] + s * np.sin(heading), dtype=float)
    return t, x, y


def _const(v: float) -> Callable[[FloatArray], FloatArray]:
    return lambda t: np.full_like(t, v)


def crossing(n_pairs: int = 20, seed: int = 0, spacing: float = 40.0) -> Trajectories:
    """Perpendicular crossing (unsignalised intersection): car A east-bound, car B north-bound.

    Both pass the origin; B arrives ``delta`` seconds after A, ``delta`` uniform in [-6, 6] s
    (|delta| below about 1 s makes the bodies meet). Speeds 8 to 14 m/s.
    """
    rng = np.random.default_rng(seed)
    b = _Builder()
    for i in range(n_pairs):
        t0 = i * spacing
        va, vb = rng.uniform(8, 14, 2)
        delta = rng.uniform(-6, 6)
        ta, tb = 4.0, 4.0 + delta  # arrival times at the origin after pair start
        dur = 10.0
        b.add(*_line(t0, dur, (-va * ta, 0.0), 0.0, _const(va)), CAR, "car")
        b.add(*_line(t0, dur, (0.0, -vb * tb), np.pi / 2, _const(vb)), CAR, "car")
    return b.build("crossing")


def following(n_pairs: int = 20, seed: int = 0, spacing: float = 40.0) -> Trajectories:
    """Highway car following: the leader brakes, the follower reacts after a reaction time.

    Speed 25 m/s, bumper gap 15 to 40 m, leader deceleration 2 to 7 m/s^2 for 3 s from t = 2 s,
    follower reaction 0.8 to 1.6 s then braking at 6 m/s^2 to a floor of the leader's speed.
    """
    rng = np.random.default_rng(seed)
    bld = _Builder()
    for i in range(n_pairs):
        t0 = i * spacing
        gap = rng.uniform(15, 40)
        dec_l, react = rng.uniform(2, 7), rng.uniform(0.8, 1.6)
        dur = 10.0

        def lead(t: FloatArray, d: float = dec_l, v0: float = V0) -> FloatArray:
            return np.where(t < 2, v0, np.maximum(v0 - d * (t - 2), v0 - d * 3))

        def foll(t: FloatArray, r: float = react, d: float = dec_l, v0: float = V0) -> FloatArray:
            floor = v0 - d * 3
            return np.where(t < 2 + r, v0, np.maximum(v0 - 6.0 * (t - 2 - r), floor))

        x_f = 0.0
        x_l = x_f + CAR[0] + gap  # centre distance = length + gap
        bld.add(*_line(t0, dur, (x_l, 0.0), 0.0, lead), CAR, "car")
        bld.add(*_line(t0, dur, (x_f, 0.0), 0.0, foll), CAR, "car")
    return bld.build("following")


def merge(n_pairs: int = 20, seed: int = 0, spacing: float = 40.0) -> Trajectories:
    """Ramp merge: a ramp vehicle converges at 12 degrees on a through vehicle (speed 22 m/s).

    The ramp vehicle reaches the merge point ``delta`` seconds before or after the through vehicle,
    ``delta`` uniform in [-4, 4] s.
    """
    rng = np.random.default_rng(seed)
    b = _Builder()
    ang = np.deg2rad(12.0)
    for i in range(n_pairs):
        t0 = i * spacing
        vm, vr = 22.0, rng.uniform(18, 24)
        delta = rng.uniform(-4, 4)
        tm, tr = 5.0, 5.0 + delta
        b.add(*_line(t0, 10.0, (-vm * tm, 0.0), 0.0, _const(vm)), CAR, "car")
        # the ramp path runs from below-left toward the merge point at the origin
        p0 = (-vr * tr * np.cos(ang), -vr * tr * np.sin(ang))
        b.add(*_line(t0, 10.0, p0, ang, _const(vr)), CAR, "car")
    return b.build("merge")


def roundabout(n_pairs: int = 20, seed: int = 0, spacing: float = 40.0) -> Trajectories:
    """Roundabout entry: a circulating vehicle (radius 15 m) and an entering vehicle.

    The entering vehicle follows a straight approach to the circle and then circulates; the
    circulating vehicle passes the entry point ``delta`` seconds before or after it, ``delta``
    uniform in [-4, 4] s. Speeds 6 to 9 m/s.
    """
    rng = np.random.default_rng(seed)
    b = _Builder()
    radius, alpha = 15.0, np.deg2rad(30.0)
    d = np.array([-np.sin(alpha), np.cos(alpha)])  # approach direction at the entry point (R, 0)
    for i in range(n_pairs):
        t0 = i * spacing
        v_c, v_e = rng.uniform(6, 9, 2)
        delta = rng.uniform(-4, 4)
        t_e = 8.0  # entering vehicle reaches the entry point
        t_c = t_e + delta  # circulating vehicle passes the entry point (angle 0)
        t = np.asarray(np.arange(t0, t0 + 14.0, DT), dtype=float)
        th = (v_c / radius) * ((t - t0) - t_c)
        b.add(t, radius * np.cos(th), radius * np.sin(th), CAR, "car")
        s = v_e * ((t - t0) - t_e)  # arc length from the entry point; negative = on the approach
        th_e = np.maximum(s, 0.0) / radius
        on_circle = s >= 0
        x = np.where(on_circle, radius * np.cos(th_e), radius + s * d[0])
        y = np.where(on_circle, radius * np.sin(th_e), s * d[1])
        b.add(t, x, y, CAR, "car")
    return b.build("roundabout")


def pedestrian(n_pairs: int = 20, seed: int = 0, spacing: float = 40.0) -> Trajectories:
    """Shared space: a pedestrian crosses a road (1.4 m/s) while a car drives past (8 to 12 m/s).

    The car arrives at the crossing line ``delta`` seconds before or after the pedestrian,
    ``delta`` uniform in [-5, 5] s. No braking by either.
    """
    rng = np.random.default_rng(seed)
    b = _Builder()
    for i in range(n_pairs):
        t0 = i * spacing
        vc, vp = rng.uniform(8, 12), 1.4
        delta = rng.uniform(-5, 5)
        t_p, t_c = 6.0, 6.0 + delta
        b.add(*_line(t0, 12.0, (-vc * t_c, 0.0), 0.0, _const(vc)), CAR, "car")
        b.add(*_line(t0, 12.0, (0.0, -vp * t_p), np.pi / 2, _const(vp)), PED, "pedestrian")
    return b.build("pedestrian")


SCENARIOS: dict[str, Callable[..., Trajectories]] = {
    "crossing": crossing,
    "following": following,
    "merge": merge,
    "roundabout": roundabout,
    "pedestrian": pedestrian,
}


def make(name: str, **kwargs: Any) -> Trajectories:
    """Build the scenario ``name`` (one of ``SCENARIOS``) with keyword arguments."""
    try:
        return SCENARIOS[name](**kwargs)
    except KeyError:
        raise KeyError(f"unknown scenario {name!r}; choose from {sorted(SCENARIOS)}") from None
