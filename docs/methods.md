# Methods

## The conflict polygon

Road user *i* is a convex polygon `S_i` (relative to its reference point `c_i`) that moves with
constant velocity `v_i` and does not rotate. With a separate clock `tau_i >= 0` for each road
user, the bodies overlap exactly when

    (c2 - c1) + v2 tau2 - v1 tau1  in  M = S1 (+) (-S2).

`M` is the Minkowski difference; for two rectangles it has at most 8 edges and its half-planes
are `n.x <= h_S1(n) + h_S2(-n)` for the edge normals `n` of both bodies. Substitution gives
linear inequalities in `(tau1, tau2)`; with the horizon box `[0, T]^2` they define the conflict
polygon `K`. Undisturbed motion is the diagonal `tau1 = tau2`.

| indicator | reading on K |
|---|---|
| TTC | `min t` with `(t, t)` in `K` |
| TAdv | `min |tau1 - tau2|` over `K` (0 on a collision course) |
| T2 | `max(tau1, tau2)` at the TAdv minimiser (TTC on a collision course) |
| TG | `min max(tau1, tau2)` over `K` |
| state | A if TTC exists, B if `K` is non-empty, C if `K` is empty |

Implementation (`pyssms.timetime`): all pairwise intersections of the constraint lines are
tested for feasibility (exact vertex enumeration); TTC is the lower end of the chord of the
diagonal. Rank-deficient cases (parallel paths, a standing road user, both standing) need no
special code: a row without `tau`-dependence is a constant test, and the horizon box bounds the
strip. Ties of TAdv are broken by the smallest T2. Optima on the horizon edge give `NaN`.

## Reading of Appendix A (`pyssms.reference.laureshyn2010`)

1. **Eqs. (8) and (9) sign.** Substituting Eq. (4) into Eq. (6) gives
   `t = -[(y_p - y_ln1) - k (x_p - x_ln1)] / [(v_py - v_lny) - k (v_px - v_lnx)]`. This is the
   form printed in the author's 2010 thesis (Appendix, printed p. 138); it is used by default.
   The "article in press" PDF of the journal paper omits the leading minus sign (example: a
   point at the origin moving at 1 m/s towards a still vertical section at x = 10 gives -10 s
   by Eq. (9) without the minus sign, 10 s with it). `as_printed=True` evaluates that preprint
   form; whether the final journal version has the minus sign was not checked.
2. **Eq. (10).** The second lines read `x_ln1 >= x2` and `y_ln1 >= y2` (in the thesis and in the
   preprint); we read `x_ln2`, `y_ln2`.
   The test needs equality of floating-point numbers when a side is parallel to an axis;
   `tol` widens it (`tol=0` is the printed test).
3. **Fig. 11 special cases.** Read as clipping to the future: the common point is replaced by
   the point where the corner's path enters the region swept by the side through the side's
   present position (`t_ln = 0`), or by the corner's present position (`t_p = 0`).
4. **Not covered.** Corner and side paths parallel (`k` and common points undefined), a road
   user standing still (`S/v`), and bodies that overlap at `t = 0`.
5. **Aggregation.** Lowest TTC over the 32 combinations; TAdv only when no combination is on a
   collision course; TG = TTC for a combination on a collision course (as printed), minimum
   over combinations otherwise.

## Disturbance set D (`pyssms.disturbance`)

Delay one road user by `delta = tau1 - tau2` (the diagonal of the time-time plane is `delta = 0`) and
shift the path of road user 2 by `eps` metres along a unit vector `u`. With `tau2 = t` and
`tau1 = t + delta` the overlap condition `(c2 - c1) + eps u + v2 t - v1 (t + delta) in M` is linear in
`(t, delta, eps)`, as are `t >= 0`, `t + delta >= 0` and the horizon. Eliminating `t` (Fourier-Motzkin:
every pair of one upper and one lower bound on `t` gives one inequality; at most
`U * L + Z` rows) yields the half-planes of the convex polygon `D`; it is exact, and the
construction does not depend on `K`. Readings: origin in `D` = collision course; shortest distance
to `D` along the `delta` axis = Time Advantage, along the `eps` axis = lateral margin of road user 2
(both checked against `timetime` and `margins`); the signed distance in scaled coordinates is
`beta`. `Phi(-beta)` is the first-order reliability approximation (exact for a half-plane D).

## Evasive capacity by braking (`pyssms.escape`)

Braking at `a` from speed `v` gives travelled distance `sigma(t)`; on a straight path that is the
position of a constant-velocity road user at the virtual clock `tau(t) = sigma(t)/v`, so braking of
road user 1 is the curve `(tau1(t), t)` in the time-time plane (it ends at `tau1 = v/(2a)`). It
avoids a contact exactly when it misses `K` (tested against `stories.first_contact`, 800
encounters). `required_braking` returns the smallest deceleration on a grid (then refined by
bisection) with a contact-free outcome; braking is not always the right action, so this is not a
monotone threshold. Swerving is not modelled.

## Stories on the overlap polygon (`pyssms.stories`)

For straight paths with unit directions `d_i`, body `i` is at `c_i + sigma_i d_i`. The set of
travelled-distance pairs `(sigma1, sigma2)` at which the bodies overlap,

    R = {(s1, s2) : (c2 - c1) + s2 d2 - s1 d1  in  S1 (+) (-S2)},

is a convex polygon with at most 8 edges (the same construction as `K` with unit instead of
actual speeds) and does not depend on speeds, accelerations or jerks. A motion "story" (constant
speed, constant acceleration or braking, constant jerk; the L2/F1 stories of Naseralavi et al.,
2025) gives `sigma_i(t)` as a polynomial in `t`, stopped at the time its speed reaches zero.
Contact is `g(t) = max_k (a_k sigma1(t) + c_k sigma2(t) - r_k) <= 0`.

**Hypothesis check (proposed by a collaborator, 2026-11-01): confirmed for straight paths.** The
polygon `R` stays a polygon under any story; only the time dependence becomes polynomial. We do
not use closed-form roots: a single code path (conservative advancement, then bisection) covers
quadratic and cubic stories and the stop at zero speed. Checks (`tests/unit/test_stories.py`):

* constant-speed stories give the same TTC as the time-time polygon (3,000 encounters: no wrong
  value; at most 3 contacts missed);
* a braking story (-4 m/s^2) against a brute-force time scan with the separating-axis test.

**Known limit.** The search advances by at least `min_step` (2 ms); a contact window shorter than
that (a grazing touch) can be missed, never mis-timed. With `min_step=1e-6` the two missed cases in
a 5,000-encounter probe were recovered. One-dimensional indicators defined by distance or
deceleration (SDI, PSD, MPSD, DRAC, MDRAC, DCIA) are not implemented; their two-dimensional
definition along `sigma` is a theoretical decision still to be made and marked as a proposal.
