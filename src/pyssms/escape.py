"""Evasive capacity by braking: the smallest deceleration that avoids a contact.

A road user that brakes at a constant rate ``a`` from speed ``v`` has travelled
``sigma(t) = v t - a t^2 / 2`` until it stops at ``t = v / a``. On its straight path this is the
position a constant-velocity road user would have at the *virtual clock*
``tau(t) = sigma(t) / v``. In the time-time plane of :mod:`pyssms.timetime` braking of road user 1
(road user 2 unchanged, ``tau2 = t``) is therefore the curve ``(tau1(t), t)``: it leaves the origin
along the diagonal, bends towards the ``tau2`` axis and ends at ``tau1 = v / (2 a)``. The braking
avoids a contact exactly when the curve misses the conflict polygon ``K`` (checked in
``tests/unit/test_escape.py`` against the first-contact search of :mod:`pyssms.stories`).

:func:`required_braking` searches the smallest constant deceleration, among those that avoid a
contact within the horizon, for either road user while the other keeps its speed. It is the
two-dimensional, shape-aware relative of DRAC and MDRAC (which assume a rear-end geometry). Three
caveats: braking is not always the right evasive action (a road user ahead of the other that
brakes may be hit from behind, so the result is the smallest value on a grid with a contact-free
outcome, not a monotone threshold); the search stops at ``a_max``; swerving is not modelled (a
sideways shift of the whole path, as in :mod:`pyssms.disturbance`, is not what a swerve does).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pyssms.geometry import FloatArray
from pyssms.stories import Story, first_contact

__all__ = ["required_braking", "virtual_clock"]


def virtual_clock(speed: float, decel: float, t: FloatArray) -> FloatArray:
    """Virtual clock ``tau(t)`` of a road user braking at ``decel`` from ``speed``."""
    te = np.minimum(t, speed / decel) if decel > 0 else t
    out: FloatArray = (speed * te - 0.5 * decel * te**2) / speed
    return out


def _contact(
    who: int,
    a: FloatArray,
    shape1: FloatArray,
    pos1: FloatArray,
    dir1: FloatArray,
    speed1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    dir2: FloatArray,
    speed2: FloatArray,
    horizon: float,
) -> FloatArray:
    acc = -np.asarray(a, float)
    s1 = Story.constant_acceleration(speed1, acc if who == 1 else 0.0)
    s2 = Story.constant_acceleration(speed2, acc if who == 2 else 0.0)
    return first_contact(shape1, pos1, dir1, s1, shape2, pos2, dir2, s2, horizon=horizon)


def required_braking(
    shape1: FloatArray,
    pos1: FloatArray,
    dir1: FloatArray,
    speed1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    dir2: FloatArray,
    speed2: FloatArray,
    who: int,
    a_max: float = 10.0,
    horizon: float = 10.0,
    coarse: float = 0.25,
    iters: int = 30,
) -> FloatArray:
    """Smallest constant deceleration (m/s^2) of road user ``who`` that avoids a contact.

    The other road user keeps its speed. ``0`` if there is no contact anyway; ``NaN`` if the
    bodies already overlap or no deceleration up to ``a_max`` avoids a contact within
    ``horizon``. The search scans ``0, coarse, 2 coarse, ...`` and refines the first
    contact-free value by bisection towards the last value with a contact.

    Args:
        shape1: Footprint of road user 1 relative to its centre ``(N, V, 2)``.
        pos1: Centre ``(N, 2)``.
        dir1: Unit direction of its straight path ``(N, 2)``.
        speed1: Speed (m/s) ``(N,)``.
        shape2: Footprint of road user 2.
        pos2: Centre of road user 2.
        dir2: Unit direction of road user 2.
        speed2: Speed of road user 2.
        who: ``1`` or ``2``: the road user that brakes.
        a_max: Largest deceleration considered (m/s^2).
        horizon: Prediction horizon (s).
        coarse: Step of the coarse scan (m/s^2).
        iters: Bisection steps.
    """
    if who not in (1, 2):
        raise ValueError("who must be 1 or 2")
    n = pos1.shape[0]
    args = (shape1, pos1, dir1, speed1, shape2, pos2, dir2, speed2, horizon)
    hi = np.full(n, np.nan)
    lo = np.zeros(n)
    found = np.zeros(n, bool)
    now = _contact(who, np.zeros(n), *args)
    already = now == 0.0
    free = np.isnan(now)
    hi[free] = 0.0
    found |= free
    prev = 0.0
    for a in np.arange(coarse, a_max + coarse / 2, coarse):
        todo = ~found & ~already
        if not todo.any():
            break
        c = _contact(who, np.full(n, a), *args)
        new = todo & np.isnan(c)
        lo[new], hi[new] = prev, a
        found |= new
        prev = float(a)
    ok = found & ~free
    if ok.any():
        sub = np.where(ok)[0]
        sel: tuple[Any, ...] = (*(x[sub] for x in args[:-1]), horizon)
        low, h = lo[sub].copy(), hi[sub].copy()
        for _ in range(iters):
            mid = 0.5 * (low + h)
            c = _contact(who, mid, *sel)
            avoid = np.isnan(c)
            h = np.where(avoid, mid, h)
            low = np.where(avoid, low, mid)
        hi[sub] = h
    out: FloatArray = np.where(found & ~already, hi, np.nan)
    return out
