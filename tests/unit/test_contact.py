"""Face and corner of the first contact, checked against a time-stepped geometric search."""

import numpy as np
import pytest

from pyssms import indicators, rectangle
from pyssms.contact import FACES, avoided_contact_faces, contact_faces


def _step_contact(shape1, p1, v1, shape2, p2, v2, dt=1e-4, horizon=10.0):
    """First time the bodies touch, and the (body, face, corner) found by brute force.

    At the first overlapping step the touching pair is the (corner, face) with the smallest
    penetration: for every corner of one body and every face of the other, the signed distance of
    the corner behind the face line; the pair with the largest (least negative) minimum over the
    other faces is the entry.
    """
    for t in np.arange(0.0, horizon, dt):
        c1 = shape1 + p1 + v1 * t
        c2 = shape2 + p2 + v2 * t
        # separating axis test on the 8 face normals
        slack = []
        for (ca,), (cb,), who in (
            ((c1,), (c2,), 1),
            ((c2,), (c1,), 2),
        ):
            edge = np.roll(ca, -1, axis=0) - ca
            nrm = np.stack([edge[:, 1], -edge[:, 0]], -1)
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
            for f in range(len(nrm)):
                sep = (cb @ nrm[f]).min() - (ca @ nrm[f]).max()
                slack.append((sep, who, f, int(np.argmin(cb @ nrm[f]))))
        worst = max(slack)  # the largest separation: the face that still separates
        if worst[0] < 0:
            return t, worst
    return np.nan, None


def _setup(h1, h2, p2, v1=(10.0, 0.0), v2=(0.0, 0.0)):
    s1 = rectangle(np.array([h1]), 4.5, 1.8)
    s2 = rectangle(np.array([h2]), 4.5, 1.8)
    return (s1, np.array([[-20.0, 0.3]]), np.array([v1]), s2, np.array([p2]), np.array([v2]))


def test_ttc_matches_the_indicator():
    args = _setup(0.0, np.deg2rad(30), [0.0, 0.0])
    ct = contact_faces(*args, horizon=10.0)
    k = indicators(*args, horizon=10.0)
    assert ct.ttc[0] == pytest.approx(k.ttc[0], abs=1e-9)
    assert ct.body[0] in (1, 2) and not ct.already[0]


@pytest.mark.parametrize("h2", [30, 60, 120, 200, 310])
def test_face_and_corner_agree_with_the_time_stepped_search(h2):
    args = _setup(0.0, np.deg2rad(h2), [0.0, 0.0])
    ct = contact_faces(*args, horizon=10.0)
    t_step, worst = _step_contact(*[x[0] if x.ndim == 3 or x.shape[0] == 1 else x for x in args])
    assert ct.ttc[0] == pytest.approx(t_step, abs=2e-3)
    sep, who, face, corner = worst
    assert ct.n_active[0] == 1
    assert (ct.body[0], ct.face[0], ct.corner[0]) == (who, face, corner)


def test_stationary_car_ahead_is_a_face_to_face_tie():
    s = rectangle(np.array([0.0]), 4.5, 1.8)
    ct = contact_faces(
        s, np.array([[-20.0, 0.0]]), np.array([[10.0, 0.0]]), s, np.array([[0.0, 0.0]]),
        np.zeros((1, 2)), horizon=10.0,
    )  # fmt: skip
    assert ct.ttc[0] == pytest.approx((20.0 - 4.5) / 10.0)
    assert ct.n_active[0] >= 2  # front of car 1 on rear of car 2: two parallel rows
    assert FACES[ct.face[0]] in ("front", "rear")


def test_no_contact_and_already_overlapping():
    s = rectangle(np.array([0.0]), 4.5, 1.8)
    miss = contact_faces(
        s, np.array([[-20.0, 5.0]]), np.array([[10.0, 0.0]]), s, np.array([[0.0, 0.0]]),
        np.zeros((1, 2)), horizon=10.0,
    )  # fmt: skip
    assert np.isnan(miss.ttc[0]) and miss.body[0] == 0 and miss.face[0] == -1
    over = contact_faces(
        s, np.array([[0.5, 0.0]]), np.array([[1.0, 0.0]]), s, np.array([[0.0, 0.0]]),
        np.zeros((1, 2)), horizon=10.0,
    )  # fmt: skip
    assert over.already[0] and over.body[0] == 0 and over.ttc[0] == 0.0


def test_vectorised_over_many_encounters_equals_one_by_one():
    rng = np.random.default_rng(4)
    n = 50
    h1, h2 = rng.uniform(-np.pi, np.pi, n), rng.uniform(-np.pi, np.pi, n)
    s1, s2 = rectangle(h1, 4.5, 1.8), rectangle(h2, 4.5, 1.8)
    p1, p2 = rng.uniform(-5, 5, (n, 2)), rng.uniform(15, 25, (n, 2))
    v1 = 10.0 * np.stack([np.cos(h1), np.sin(h1)], -1)
    v2 = 8.0 * np.stack([np.cos(h2), np.sin(h2)], -1)
    allc = contact_faces(s1, p1, v1, s2, p2, v2, 20.0)
    for i in range(n):
        one = contact_faces(s1[i : i + 1], p1[i : i + 1], v1[i : i + 1], s2[i : i + 1],
                            p2[i : i + 1], v2[i : i + 1], 20.0)  # fmt: skip
        assert (one.body[0], one.face[0], one.corner[0]) == (
            allc.body[i],
            allc.face[i],
            allc.corner[i],
        )
        np.testing.assert_allclose(one.ttc[0], allc.ttc[i], equal_nan=True)


# ---------------------------------------------------------------- avoided contact (state B)


def _random_encounters(n, seed, spread=25.0):
    rng = np.random.default_rng(seed)
    h1, h2 = rng.uniform(-np.pi, np.pi, n), rng.uniform(-np.pi, np.pi, n)
    s1, s2 = rectangle(h1, 4.5, 1.8), rectangle(h2, 4.5, 1.8)
    p1, p2 = np.zeros((n, 2)), rng.uniform(-spread, spread, (n, 2))
    v1 = rng.uniform(4, 20, (n, 1)) * np.stack([np.cos(h1), np.sin(h1)], -1)
    v2 = rng.uniform(4, 20, (n, 1)) * np.stack([np.cos(h2), np.sin(h2)], -1)
    return s1, p1, v1, s2, p2, v2


def _overlap_at(c1, c2):
    """Separating-axis test of two convex polygons (strict overlap)."""
    for a, b in ((c1, c2), (c2, c1)):
        edge = np.roll(a, -1, axis=0) - a
        nrm = np.stack([edge[:, 1], -edge[:, 0]], -1)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
        for f in range(len(nrm)):
            if (b @ nrm[f]).min() >= (a @ nrm[f]).max() - 1e-12:
                return False
    return True


def _overlap_any(args, i, delay, who, t0, half=0.06, step=2e-4):
    s1, p1, v1, s2, p2, v2 = (x[i] for x in args)
    for t in np.arange(max(t0 - half, 0.0), t0 + half, step):
        t1 = t - (delay if who == 1 else 0.0)
        t2 = t - (delay if who == 2 else 0.0)
        if _overlap_at(s1 + p1 + v1 * t1, s2 + p2 + v2 * t2):
            return True
    return False


def test_avoided_contact_tadv_and_first_equal_the_indicators():
    args = _random_encounters(3000, seed=11)
    k = indicators(*args, horizon=10.0)
    av = avoided_contact_faces(*args, horizon=10.0)
    b = k.state == "B"
    assert b.sum() > 500
    assert np.allclose(av.tadv[b], k.tadv[b], atol=1e-9)
    assert np.array_equal(av.first[b], k.first[b])
    assert np.all(np.isnan(av.tadv[~b])) and np.all(av.n_active[~b] == 0)


def test_avoided_contact_is_a_graze_at_exactly_tadv_of_delay():
    args = _random_encounters(3000, seed=12)
    av = avoided_contact_faces(*args, horizon=10.0)
    ok = np.flatnonzero((av.n_active == 2) & ~av.horizon_active)
    assert ok.size > 100
    for i in ok[:12]:
        later = max(av.tau1[i], av.tau2[i])
        # delay the road user ahead by a little less / more than TAdv: no overlap / overlap
        assert not _overlap_any(args, i, av.tadv[i] - 3e-3, av.first[i], later)
        assert _overlap_any(args, i, av.tadv[i] + 3e-3, av.first[i], later)


def test_avoided_contact_names_a_face_and_a_corner_that_touch():
    args = _random_encounters(3000, seed=13)
    s1, p1, v1, s2, p2, v2 = args
    av = avoided_contact_faces(*args, horizon=10.0)
    ok = np.flatnonzero((av.n_active >= 1) & ~av.horizon_active)
    assert ok.size > 100
    for i in ok:
        q1 = p1[i] + v1[i] * av.tau1[i]
        q2 = p2[i] + v2[i] * av.tau2[i]
        for col in range(int(min(av.n_active[i], 2))):
            body, face, corner = av.body[i, col], av.face[i, col], av.corner[i, col]
            assert body in (1, 2) and 0 <= face < 4 and 0 <= corner < 4
            fs, fq, cs, cq = (s1[i], q1, s2[i], q2) if body == 1 else (s2[i], q2, s1[i], q1)
            edge = fs[(face + 1) % 4] - fs[face]
            nrm = np.array([edge[1], -edge[0]]) / np.linalg.norm(edge)  # outward normal
            line = (fs[face] + fq) @ nrm
            assert (cs[corner] + cq) @ nrm == pytest.approx(
                line, abs=1e-6
            )  # corner on the face line
            # and the corner lies within the face (a touch, not just the extended line)
            t = ((cs[corner] + cq) - (fs[face] + fq)) @ (edge / np.linalg.norm(edge))
            assert -1e-6 <= t <= np.linalg.norm(edge) + 1e-6


def test_avoided_contact_states_a_and_c_have_no_entry():
    s = rectangle(np.array([0.0, 0.0]), 4.5, 1.8)
    # row 0: collision course (state A); row 1: paths that never overlap (state C)
    p1 = np.array([[-20.0, 0.0], [-20.0, 0.0]])
    v1 = np.array([[10.0, 0.0], [10.0, 0.0]])
    p2 = np.array([[0.0, 0.0], [0.0, 30.0]])
    v2 = np.zeros((2, 2))
    av = avoided_contact_faces(s, p1, v1, s, p2, v2, horizon=10.0)
    assert np.all(np.isnan(av.tadv)) and np.all(av.n_active == 0) and np.all(av.body == 0)


def test_jimenez_2013_ten_configurations_are_the_contacts_the_polygon_produces():
    """Tables 1 and 2 of Jimenez, Naranjo and Garcia (2013): which part of which vehicle is hit.

    With vehicles that move forward, random collision courses give exactly six classes of
    (struck body, struck part) when the angle between the motions is below 90 degrees (A to F:
    side of either vehicle, front of either vehicle, rear of either vehicle) and four above 90
    degrees (G to J: side or front of either vehicle, never the rear).
    """
    n = 150_000
    rng = np.random.default_rng(5)
    h1, h2 = rng.uniform(-np.pi, np.pi, n), rng.uniform(-np.pi, np.pi, n)
    s1, s2 = rectangle(h1, 4.5, 1.8), rectangle(h2, 4.5, 1.8)
    p1, p2 = np.zeros((n, 2)), rng.uniform(-30, 30, (n, 2))
    v1 = rng.uniform(3, 20, (n, 1)) * np.stack([np.cos(h1), np.sin(h1)], -1)
    v2 = rng.uniform(3, 20, (n, 1)) * np.stack([np.cos(h2), np.sin(h2)], -1)
    ct = contact_faces(s1, p1, v1, s2, p2, v2, horizon=10.0)
    hit = (ct.body > 0) & (ct.n_active == 1)  # a corner strikes a face; ties are set aside
    cos = np.einsum("nd,nd->n", v1, v2) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1))
    part = {"front": "front", "rear": "rear", "left": "side", "right": "side"}

    def classes(sel):
        return {
            (int(b), part[FACES[f]])
            for b, f in zip(ct.body[hit & sel], ct.face[hit & sel], strict=True)
        }

    both = {1, 2}
    assert classes(cos > 0) == {(b, k) for b in both for k in ("side", "front", "rear")}  # A-F
    assert classes(cos < 0) == {(b, k) for b in both for k in ("side", "front")}  # G-J
    # and a hit is never a tie in random positions (the exceptions the paper sets aside)
    assert not np.any((ct.body > 0) & (ct.n_active > 1))
