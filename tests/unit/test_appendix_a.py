"""The time-time polygon against the 32 corner-side combinations of Appendix A (2010)."""

import numpy as np
import pytest

from pyssms.geometry import rectangle_corners
from pyssms.reference import appendix_a, random_encounters
from pyssms.timetime import indicators

T = 60.0


def _sat_overlap(c1, c2):
    sep = np.zeros(len(c1), dtype=bool)
    for poly in (c1, c2):
        edge = np.roll(poly, -1, axis=1) - poly
        normals = np.stack([edge[..., 1], -edge[..., 0]], -1)
        for k in range(normals.shape[1]):
            nk = normals[:, k]
            p1 = np.einsum("nvd,nd->nv", c1, nk)
            p2 = np.einsum("nvd,nd->nv", c2, nk)
            sep |= (p1.max(1) < p2.min(1)) | (p2.max(1) < p1.min(1))
    return ~sep


def _agree(a, b):
    return np.isclose(a, b, rtol=1e-7, atol=1e-6) | (np.isnan(a) & np.isnan(b))


@pytest.mark.parametrize("kind", ["generic", "axis_aligned"])
def test_equivalence_on_random_encounters(kind):
    e = random_encounters(5000, kind, seed=11)
    k = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, horizon=T)
    r = appendix_a(e.corners1, e.vel1, e.corners2, e.vel2, tol=1e-9)
    use = r.covered & ~_sat_overlap(e.corners1, e.corners2)
    assert use.sum() > 2000
    beyond = ~(r.t2 < T - 1e-6)
    assert _agree(k.ttc, np.where(r.ttc < T, r.ttc, np.nan))[use].all()
    assert _agree(k.tg, np.where(r.tg < T, r.tg, np.nan))[use].all()
    assert _agree(k.tadv, np.where(beyond, np.nan, r.tadv))[use].all()
    assert _agree(k.t2, np.where(beyond, np.nan, r.t2))[use].all()
    assert (k.first == np.where(beyond, 0, r.first))[use].all()


def test_preprint_form_of_eq8_and_eq9_misses_a_head_on_collision():
    # The thesis (p. 138) prints the minus sign; the "article in press" PDF omits it.
    c1 = rectangle_corners(0, 0, 0, 4.5, 1.8)
    c2 = rectangle_corners(50, 0, np.pi, 4.5, 1.8)
    v1, v2 = np.array([[10.0, 0]]), np.array([[-10.0, 0]])
    assert appendix_a(c1, v1, c2, v2).ttc[0] == pytest.approx((50 - 4.5) / 20)
    assert np.isnan(appendix_a(c1, v1, c2, v2, as_printed=True).ttc[0])


def test_printed_eq10_without_tolerance_is_fragile_for_axis_aligned_sides():
    e = random_encounters(2000, "axis_aligned", seed=3)
    exact = appendix_a(e.corners1, e.vel1, e.corners2, e.vel2, tol=1e-9)
    printed = appendix_a(e.corners1, e.vel1, e.corners2, e.vel2, tol=0.0)
    missed = np.isfinite(exact.ttc) & np.isnan(printed.ttc)
    assert missed.sum() > 0


def test_appendix_does_not_cover_parallel_or_standing():
    for kind in ("parallel", "stopped"):
        e = random_encounters(500, kind, seed=5)
        r = appendix_a(e.corners1, e.vel1, e.corners2, e.vel2)
        assert not r.covered.any()
