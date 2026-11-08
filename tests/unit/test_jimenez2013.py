"""The worked example of Jimenez, Naranjo and Garcia (2013, Int. J. ITS Res. 11:34-42), section 5.

Two 2 x 5 m vehicles cross perpendicularly, "10 m apart from the central point of the crossing";
the vehicle at 19 m/s meets a vehicle at 20 m/s (scenario 1) or 25 m/s (scenario 2).

Reading Fig. 4 and section 3.3.1 of the paper (roles exchanged: the 19 m/s vehicle plays the paper's
vehicle 2, whose front corner reaches the other path after 10 - 1 = 9 m: TA21 = 9/19 s; the other
vehicle reaches it with its front corner after 9 m, TD11 = 9/20 s, and with its rear corner, 5 m
behind, after 9 + 5 m, TC11 = (9 + 5)/v), the printed values are reproduced for scenario 1
(14/20 s) and the collision condition TC11 >= TA21 >= TD11 holds: TTC = TA21 = 9/19 s. For
scenario 2 the same rule gives TC11 = 14/25 = 0.56 s >= 9/19 s: a collision; the paper prints
11/25 = 0.44 s and "no collision", a slip in the numerator (11 instead of 14). The polygon and
a time-stepped overlap search agree with the collision (both scenarios at 9/19 s). Details:
`docs/jimenez2013_note.md`.
"""

import numpy as np
import pytest

from pyssms import indicators_rect

V1 = 19.0
CENTRE_DISTANCE = 12.5  # front bumper 10 m from the crossing centre, body 5 m long


def _package(v2):
    return indicators_rect(
        -CENTRE_DISTANCE, 0.0, 0.0, V1, 0.0, 5.0, 2.0,
        0.0, -CENTRE_DISTANCE, np.pi / 2, 0.0, v2, 5.0, 2.0,
        horizon=10.0,
    )  # fmt: skip


def _brute_force(v2, step=1e-5):
    for t in np.arange(0.0, 3.0, step):
        x1 = -CENTRE_DISTANCE + V1 * t
        y2 = -CENTRE_DISTANCE + v2 * t
        if (x1 + 2.5 > -1 and x1 - 2.5 < 1) and (y2 + 2.5 > -1 and y2 - 2.5 < 1):
            return t
    return float("nan")


def test_scenario_1_ttc_equals_the_papers_ta21():
    k = _package(20.0)
    assert k.state[0] == "A"
    assert k.ttc[0] == pytest.approx(9.0 / 19.0, abs=1e-9)  # TTC = TA21 as printed
    assert _brute_force(20.0) == pytest.approx(9.0 / 19.0, abs=2e-5)


def test_scenario_2_is_a_collision_for_the_stated_bodies():
    k = _package(25.0)
    assert (
        k.state[0] == "A"
    )  # the paper prints 'no collision' (11/25 s, a slip for 14/25 s); see the module docstring
    assert k.ttc[0] == pytest.approx(9.0 / 19.0, abs=1e-9)
    assert _brute_force(25.0) == pytest.approx(9.0 / 19.0, abs=2e-5)


def test_a_vehicle_2_fast_enough_to_clear_the_path_is_a_miss():
    """Where the paper's logic holds for these bodies: all of vehicle 2 clears first."""
    # vehicle 2 rear leaves the path after (9 + 2 + 5) / v2 < 9/19  ->  v2 > 33.8 m/s
    k = _package(36.0)
    assert k.state[0] == "B" and np.isnan(k.ttc[0])
    assert k.tadv[0] == pytest.approx(9.0 / 19.0 - 16.0 / 36.0, abs=1e-6)
    assert k.first[0] == 2
