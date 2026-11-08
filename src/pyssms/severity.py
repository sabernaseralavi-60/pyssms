"""Delta-V and Extended Delta-V of Laureshyn et al. (2017, Accid. Anal. Prev. 98, 46-56).

Definitions as printed in the paper (Section 2.2-2.3):

* Delta-V of a hypothetical collision between two road users treated as *point masses that stick
  together* (completely inelastic collision, momentum conserved): with approach angle ``alpha``
  between the velocity vectors,
  ``dv1 = m2 / (m1 + m2) * sqrt(v1^2 + v2^2 - 2 v1 v2 cos alpha) = m2 / (m1 + m2) * |v1 - v2|``
  and ``dv2 = m1 / (m1 + m2) * |v1 - v2|``. The severity of the encounter is the larger of the two.
* Extended Delta-V reduces both speeds by braking at the constant rate ``a`` over the time ``t``
  that remains for the *last-to-arrive* road user (the T2 of the encounter) and floors the
  speed at zero: ``v = v0 - a t`` if ``v0 - a t >= 0`` else ``0`` (the paper uses a = 4 m/s^2 for
  "Extended Delta-V4" and a = 8 m/s^2 for "Extended Delta-V8"; a = 0 is Delta-V0).

Masses enter only through the ratio. The paper distinguishes four vehicle classes and prints mass
ratios (heaviest / lightest) of 1.00 (car-car), 1.69 (car-minivan) and 3.85 (car-HGV) in Table 1;
the mass of a bus is not given there and has no default here.

The collision is treated as a point-mass collision: no rotation, impact point or restitution
(the paper itself lists "completely inelastic" and "four masses" as simplifications, Section 5.2).

For a road user that is much lighter than the other (pedestrian, cyclist) the point-mass Delta-V is
about 0.91 to 0.98 of the closing speed, so it hardly discriminates; :func:`injury_risk` therefore
maps the *closing speed at the hypothetical impact* (:func:`extended_closing_speed`) to a
probability of injury with the logistic risk curves of Lubbe, Wu and Jeppsson (2022, Traffic
Safety Research 2, 000006, doi:10.55329/vfma7555; Tables 2-5), read from the paper itself. These are
curves for crashes that happened (German in-depth data, struck road user older than 14 years,
impact on the front of a passenger car): conditional on a collision, not a probability of a
collision, and not validated for conflicts. The three levels are fitted separately, so the curves
can cross outside the range of the data (for cyclists above about 90 km/h at age 65).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from pyssms.geometry import FloatArray

__all__ = [
    "INJURY_COEFFICIENTS",
    "MASS_RATIO_TO_CAR",
    "delta_v",
    "extended_closing_speed",
    "extended_delta_v",
    "injury_risk",
    "reduced_velocity",
    "safe_closing_speed",
]

#: Mass relative to a passenger car, from the mass ratios printed in Table 1 of the 2017 paper.
MASS_RATIO_TO_CAR: dict[str, float] = {"car": 1.0, "minivan": 1.69, "hgv": 3.85}


def delta_v(
    mass1: ArrayLike, mass2: ArrayLike, vel1: ArrayLike, vel2: ArrayLike
) -> tuple[FloatArray, FloatArray]:
    """Delta-V of road users 1 and 2 for a completely inelastic collision (m/s).

    Args:
        mass1: Mass of road user 1 (any unit; only the ratio matters), shape ``(N,)`` or scalar.
        mass2: Mass of road user 2.
        vel1: Velocity vector of road user 1 at the hypothetical collision, ``(N, 2)``.
        vel2: Velocity vector of road user 2, ``(N, 2)``.

    Returns:
        ``(dv1, dv2)``, each of shape ``(N,)``.
    """
    m1, m2 = np.broadcast_arrays(np.asarray(mass1, float), np.asarray(mass2, float))
    rel = np.linalg.norm(np.atleast_2d(np.asarray(vel1, float)) - np.atleast_2d(vel2), axis=1)
    total = m1 + m2
    dv1: FloatArray = m2 / total * rel
    dv2: FloatArray = m1 / total * rel
    return dv1, dv2


def reduced_velocity(vel: ArrayLike, decel: float, time: ArrayLike) -> FloatArray:
    """Velocity after braking at ``decel`` (m/s^2) for ``time`` seconds, speed floored at zero.

    The direction is kept; a road user already at rest stays at rest.
    """
    v = np.atleast_2d(np.asarray(vel, float))
    speed = np.linalg.norm(v, axis=1)
    t = np.asarray(time, float)
    new = np.maximum(speed - decel * t, 0.0)
    scale = np.divide(new, speed, out=np.zeros_like(speed), where=speed > 0)
    out: FloatArray = v * scale[:, None]
    return out


def extended_delta_v(
    mass1: ArrayLike,
    mass2: ArrayLike,
    vel1: ArrayLike,
    vel2: ArrayLike,
    time: ArrayLike,
    decel: float = 8.0,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Extended Delta-V (m/s): Delta-V after braking at ``decel`` for ``time`` seconds.

    Args:
        mass1: Mass (or mass class value) of road user 1.
        mass2: Mass of road user 2.
        vel1: Velocity of road user 1 at the moment of evaluation, ``(N, 2)``.
        vel2: Velocity of road user 2, ``(N, 2)``.
        time: Time left for the last-to-arrive road user (T2), seconds.
        decel: Assumed deceleration, m/s^2 (4 normal, 8 emergency braking in the paper;
            0 gives Delta-V0).

    Returns:
        ``(dv1, dv2, severity)`` where severity is ``max(dv1, dv2)``, the value the paper uses.
    """
    v1 = reduced_velocity(vel1, decel, time)
    v2 = reduced_velocity(vel2, decel, time)
    dv1, dv2 = delta_v(mass1, mass2, v1, v2)
    return dv1, dv2, np.maximum(dv1, dv2)


#: Logistic coefficients ``(intercept, closing speed [per km/h], age [per year])`` of Tables 2-5 of
#: Lubbe, Wu and Jeppsson (2022): ``P = 1 / (1 + exp(-(b0 + b1 v + b2 age)))`` with ``v`` in km/h.
#: Levels: MAIS2+F (at least moderate injury or death), MAIS3+F (at least serious), fatal.
INJURY_COEFFICIENTS: dict[tuple[str, str], tuple[float, float, float]] = {
    ("pedestrian", "MAIS2+F"): (-3.041, 0.062, 0.027),
    ("pedestrian", "MAIS3+F"): (-6.190, 0.078, 0.038),
    ("pedestrian", "fatal"): (-10.204, 0.099, 0.053),
    ("cyclist", "MAIS2+F"): (-3.231, 0.052, 0.019),
    ("cyclist", "MAIS3+F"): (-7.467, 0.079, 0.047),
    ("cyclist", "fatal"): (-10.674, 0.100, 0.053),
    ("motorcyclist", "MAIS2+F"): (-2.965, 0.047, 0.010),
    ("motorcyclist", "MAIS3+F"): (-4.555, 0.040, 0.011),
    ("motorcyclist", "fatal"): (-7.494, 0.047, 0.014),
    ("car_driver", "MAIS2+F"): (-4.255, 0.030, 0.010),
    ("car_driver", "MAIS3+F"): (-7.654, 0.041, 0.021),
    ("car_driver", "fatal"): (-9.645, 0.044, 0.021),
}


def extended_closing_speed(
    vel1: ArrayLike, vel2: ArrayLike, time: ArrayLike, decel: float = 0.0
) -> FloatArray:
    """Closing speed (km/h) of the hypothetical impact after braking both road users.

    Both speeds are reduced as in :func:`extended_delta_v` (``decel`` m/s^2 for ``time`` seconds,
    floored at zero); the result is the length of the difference of the two velocity vectors, in
    km/h, which is the "closing speed" of the injury risk curves.
    """
    v1 = reduced_velocity(vel1, decel, time)
    v2 = reduced_velocity(vel2, decel, time)
    out: FloatArray = 3.6 * np.linalg.norm(v1 - v2, axis=1)
    return out


def injury_risk(
    road_user: str, level: str, closing_speed: ArrayLike, age: ArrayLike = 40.0
) -> FloatArray:
    """Probability of an injury of at least ``level`` for a struck road user (Lubbe et al., 2022).

    Args:
        road_user: ``"pedestrian"``, ``"cyclist"``, ``"motorcyclist"`` or ``"car_driver"``.
        level: ``"MAIS2+F"``, ``"MAIS3+F"`` or ``"fatal"``.
        closing_speed: Closing speed at the impact (km/h).
        age: Age of the struck road user in years (the curves were fitted for ages above 14).

    Returns:
        Probability conditional on a front impact by a passenger car having happened.
    """
    b0, b1, b2 = INJURY_COEFFICIENTS[(road_user, level)]
    z = b0 + b1 * np.asarray(closing_speed, float) + b2 * np.asarray(age, float)
    out: FloatArray = 1.0 / (1.0 + np.exp(-z))
    return out


def safe_closing_speed(
    road_user: str, level: str, age: ArrayLike = 40.0, risk: float = 0.10
) -> FloatArray:
    """Closing speed (km/h) at which :func:`injury_risk` reaches ``risk`` (inverse of the curve)."""
    b0, b1, b2 = INJURY_COEFFICIENTS[(road_user, level)]
    logit = np.log(risk / (1.0 - risk))
    out: FloatArray = (logit - b0 - b2 * np.asarray(age, float)) / b1
    return out
