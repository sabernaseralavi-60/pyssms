"""Evasive capacity by braking: analytic case, and braking curve in the time-time plane."""

import numpy as np
import pytest

from pyssms import rectangle
from pyssms.escape import required_braking, virtual_clock
from pyssms.reference import random_encounters
from pyssms.stories import Story, first_contact
from pyssms.timetime import constraint_rows

T = 10.0


def _dirs(e):
    return (
        np.stack([np.cos(e.heading1), np.sin(e.heading1)], -1),
        np.stack([np.cos(e.heading2), np.sin(e.heading2)], -1),
    )


def test_braking_for_a_standing_obstacle_is_v_squared_over_twice_the_free_distance():
    v, centre_distance, l1, l2 = 10.0, 50.0, 4.5, 4.5
    sh1 = rectangle(0.0, l1, 1.8)
    sh2 = rectangle(0.0, l2, 1.8)
    z = np.zeros((1, 2))
    a = required_braking(
        sh1,
        z,
        np.array([[1.0, 0.0]]),
        np.array([v]),
        sh2,
        np.array([[centre_distance, 0.0]]),
        np.array([[1.0, 0.0]]),
        np.array([0.0]),
        who=1,
        horizon=15.0,
        coarse=0.1,
    )
    free = centre_distance - 0.5 * (l1 + l2)
    assert a[0] == pytest.approx(v**2 / (2 * free), abs=2e-3)
    # the obstacle cannot brake for the car: no deceleration of road user 2 helps
    b = required_braking(
        sh1,
        z,
        np.array([[1.0, 0.0]]),
        np.array([v]),
        sh2,
        np.array([[centre_distance, 0.0]]),
        np.array([[1.0, 0.0]]),
        np.array([0.0]),
        who=2,
        horizon=15.0,
    )
    assert np.isnan(b[0])


def test_no_collision_course_needs_no_braking():
    e = random_encounters(500, "generic", seed=61)
    d1, d2 = _dirs(e)
    sp1, sp2 = np.linalg.norm(e.vel1, axis=1), np.linalg.norm(e.vel2, axis=1)
    c = first_contact(
        e.shape1,
        e.pos1,
        d1,
        Story.constant_speed(sp1),
        e.shape2,
        e.pos2,
        d2,
        Story.constant_speed(sp2),
        horizon=T,
    )
    a = required_braking(e.shape1, e.pos1, d1, sp1, e.shape2, e.pos2, d2, sp2, who=1, horizon=T)
    assert (a[np.isnan(c)] == 0.0).all()
    assert (a[np.isfinite(c)] > 0).any()


def test_the_returned_braking_avoids_the_contact_and_a_little_less_does_not():
    e = random_encounters(600, "generic", seed=62)
    d1, d2 = _dirs(e)
    sp1, sp2 = np.linalg.norm(e.vel1, axis=1), np.linalg.norm(e.vel2, axis=1)
    a = required_braking(
        e.shape1, e.pos1, d1, sp1, e.shape2, e.pos2, d2, sp2, who=1, horizon=T, coarse=0.5
    )
    use = np.isfinite(a) & (a > 0.2)
    assert use.sum() > 30

    def contact(acc):
        return first_contact(
            e.shape1[use],
            e.pos1[use],
            d1[use],
            Story.constant_acceleration(sp1[use], -acc),
            e.shape2[use],
            e.pos2[use],
            d2[use],
            Story.constant_speed(sp2[use]),
            horizon=T,
        )

    assert np.isnan(contact(a[use] + 1e-6)).all()
    # slightly less braking than the bisection result does not avoid it (up to a tiny margin)
    assert np.isfinite(contact(a[use] - 0.02)).mean() > 0.9


def test_braking_curve_misses_k_exactly_when_the_story_search_finds_no_contact():
    e = random_encounters(800, "generic", seed=63)
    d1, d2 = _dirs(e)
    sp1, sp2 = np.linalg.norm(e.vel1, axis=1), np.linalg.norm(e.vel2, axis=1)
    decel = 3.0
    c = first_contact(
        e.shape1,
        e.pos1,
        d1,
        Story.constant_acceleration(sp1, -decel),
        e.shape2,
        e.pos2,
        d2,
        Story.constant_speed(sp2),
        horizon=T,
    )
    a_, c_, r_, ok = constraint_rows(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, 1e3)
    t = np.arange(0.0, T, 0.002)
    hit = np.zeros(len(sp1), bool)
    for i in range(len(sp1)):
        if not ok[i] or sp1[i] <= 0:
            continue
        tau1 = virtual_clock(sp1[i], decel, t)
        # rows a tau1 + c tau2 <= r with tau2 = t (the horizon rows are not needed: t < T)
        lhs = a_[i, None, :-4] * tau1[:, None] + c_[i, None, :-4] * t[:, None]
        hit[i] = bool((lhs <= r_[i, None, :-4] + 1e-9).all(axis=1).any())
    story = np.isfinite(c)
    assert story.sum() > 100
    assert (hit == story).mean() > 0.99
