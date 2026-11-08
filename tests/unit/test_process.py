"""Encounter processing, observed PET, TET/TIT, calibration, hierarchy and scenario reports."""

import numpy as np
import pytest

from pyssms import calibration, datasets, hierarchy, process, scenario
from pyssms.trajectories import from_arrays


def _two_cars(delta, v=10.0, dt=0.04, dur=14.0):
    """Car A east-bound and car B north-bound; B reaches the origin delta s after A (at 4 s)."""
    t = np.arange(0, dur, dt)
    xa, ya = v * (t - 4.0), np.zeros_like(t)
    xb, yb = np.zeros_like(t), v * (t - 4.0 - delta)
    return from_arrays(
        t=np.r_[t, t], uid=np.r_[np.zeros(t.size), np.ones(t.size)], x=np.r_[xa, xb],
        y=np.r_[ya, yb], length=4.5, width=1.8,
    )  # fmt: skip


def test_candidate_pairs_and_series():
    tr = _two_cars(2.0)
    assert process.candidate_pairs(tr, max_distance=30.0) == [(0, 1)]
    # the paths cross, so the pair stays a candidate even if the distance rule is switched off
    assert process.candidate_pairs(tr, max_distance=1.0) == [(0, 1)]
    t = np.arange(0, 5, 0.1)
    apart = from_arrays(
        t=np.r_[t, t], uid=np.r_[np.zeros(t.size), np.ones(t.size)], x=np.r_[t, t] * 10,
        y=np.r_[np.zeros(t.size), np.full(t.size, 50.0)], length=4.5, width=1.8,
    )  # fmt: skip
    assert process.candidate_pairs(apart, max_distance=30.0) == []
    (e,) = process.encounters(tr, horizon=10.0)
    assert (e.a, e.b) == (0, 1)
    # at t=0 A is 40 m before the origin, B is 40 - 20 = ... B reaches origin at 6 s: TAdv ~ 2 s
    i = 0
    assert e.state[i] == "B"
    assert e.tadv[i] == pytest.approx(2.0, abs=0.7)  # bodies have extent; approximate by size
    assert e.min_distance() == pytest.approx(10.0 * np.sqrt(2), abs=0.5)
    assert e.angle[0] == pytest.approx(np.pi / 2)


def test_state_a_when_arriving_together():
    (e,) = process.encounters(_two_cars(0.0), horizon=10.0)
    assert (e.state == "A").any()
    assert e.min_ttc() < 4.0


def test_observed_pet_close_vs_far():
    near = process.observed_pet(_two_cars(2.0), 0, 1)
    far = process.observed_pet(_two_cars(5.0), 0, 1)
    assert near["collision"] == 0 and far["collision"] == 0
    assert 0 < near["pet"] < far["pet"]
    # PET is about delta minus the time the bodies need to clear the other's path (~0.5 s here)
    assert near["pet"] == pytest.approx(
        2.0 - (4.5 + 1.8) / 2 / 10.0 - (4.5 + 1.8) / 2 / 10.0 + 0.0, abs=0.3
    )
    assert near["first"] == 0 and far["first"] == 0


def test_observed_pet_collision_and_reverse_order():
    hit = process.observed_pet(_two_cars(0.0), 0, 1)
    assert hit["collision"] == 1 and hit["pet"] == 0.0
    rev = process.observed_pet(_two_cars(-3.0), 0, 1)
    assert rev["first"] == 1 and rev["pet"] > 0


def test_observed_pet_without_overlap_is_nan():
    t = np.arange(0, 3, 0.1)
    tr = from_arrays(
        t=np.r_[t, t], uid=np.r_[np.zeros(t.size), np.ones(t.size)], x=np.r_[t, t],
        y=np.r_[np.zeros(t.size), np.full(t.size, 20.0)], length=4.5, width=1.8,
    )  # fmt: skip
    assert np.isnan(process.observed_pet(tr, 0, 1)["pet"])


def test_tet_tit():
    t = np.arange(0, 5, 1.0)
    v = np.array([np.nan, 1.0, 0.5, 2.0, 1.0])
    r = process.tet_tit(t, v, threshold=1.5)
    assert r["tet"] == pytest.approx(3.0)  # values 1.0, 0.5, 1.0
    assert r["tit"] == pytest.approx(0.5 + 1.0 + 0.5)
    assert process.tet_tit(np.array([]), np.array([]))["tet"] == 0.0


def test_conflict_type():
    assert process.conflict_type(np.radians(10)) == "rear-end"
    assert process.conflict_type(np.radians(60)) == "lane-change"
    assert process.conflict_type(np.radians(90)) == "crossing"
    assert process.conflict_type(np.radians(60), rear_end=70, crossing=80) == "rear-end"


def test_braking_onset_and_swedish_pair():
    t = np.arange(0, 6, 0.1)
    s = np.where(t < 2.0, 10.0, np.maximum(10.0 - 4.0 * (t - 2.0), 0.0))
    i = process.braking_onset(t, s)
    assert i == 20  # braking starts at t = 2.0 s
    assert process.braking_onset(t, np.full_like(t, 10.0)) == -1
    (e,) = process.encounters(_two_cars(0.0), horizon=10.0)
    # constant speeds: no onset
    r = process.swedish_pair(e)
    assert np.isnan(r["ta"])


def test_swedish_pair_with_braking_car():
    tr = datasets.following(n_pairs=1, seed=3)
    (e,) = process.encounters(tr, horizon=10.0)
    r = process.swedish_pair(e, who=2)
    assert r["evader"] == 2.0 and r["v_conf"] > 5
    assert np.isfinite(r["t_onset"])


def _noisy_tracks(rng, lat_walk=0.0, lat_noise=0.0, lon_noise=0.0, n=400, dt=0.1, users=30):
    t = np.arange(n) * dt
    cols = {k: [] for k in ("t", "uid", "x", "y")}
    for u in range(users):
        cols["t"].append(t)
        cols["uid"].append(np.full(n, u))
        cols["x"].append(10.0 * t + rng.normal(0, lon_noise, n) if lon_noise else 10.0 * t)
        y = np.cumsum(rng.normal(0, lat_walk, n)) if lat_walk else np.zeros(n)
        cols["y"].append(y + (rng.normal(0, lat_noise, n) if lat_noise else 0.0))
    d = {k: np.concatenate(v) for k, v in cols.items()}
    # the true velocity is given, so the prediction itself carries no estimation noise
    return from_arrays(**d, vx=np.full(d["t"].size, 10.0), vy=np.zeros(d["t"].size),
                       length=4.5, width=1.8)  # fmt: skip


def test_calibration_random_walk_grows_with_horizon():
    tr = _noisy_tracks(np.random.default_rng(0), lat_walk=0.02)
    s = calibration.calibrate_scales(tr, taus=(0.5, 1.0, 2.0))
    assert np.all(s.n > 1000)
    # a random walk with step 0.02 m per 0.1 s: sd after tau seconds = 0.02 sqrt(tau / 0.1)
    for tau, got in zip(s.tau, s.sigma_eps, strict=True):
        assert got == pytest.approx(0.02 * np.sqrt(tau / 0.1), rel=0.15)
    sd, se = s.at(1.5)
    assert s.sigma_eps[1] < se < s.sigma_eps[2]
    r = calibration.calibrate_scales(tr, taus=(1.0,), robust=True)
    assert r.sigma_eps[0] == pytest.approx(s.sigma_eps[1], rel=0.2)


def test_calibration_position_noise_gives_timing_scale():
    tr = _noisy_tracks(np.random.default_rng(1), lat_noise=0.1, lon_noise=0.2)
    s = calibration.calibrate_scales(tr, taus=(1.0,))
    assert s.sigma_eps[0] == pytest.approx(0.1 * np.sqrt(2), rel=0.1)  # difference of two samples
    assert s.sigma_delta[0] == pytest.approx(0.2 * np.sqrt(2) / 10.0, rel=0.1)  # metres / 10 m/s


def test_unhindered_ids():
    near = _two_cars(2.0)  # the two cars are within 30 m while on the map
    assert calibration.unhindered_ids(near, min_gap=60.0).size == 0
    assert calibration.unhindered_ids(near, min_gap=2.0).size == 2


def test_hierarchy_levels_and_plot():
    enc = process.encounters(datasets.crossing(n_pairs=30, seed=2), horizon=10.0)
    sev = [hierarchy.closing_speed_at_minimum(e) for e in enc]
    h = hierarchy.build_hierarchy(enc, severity=sev)
    assert h.counts.sum() == len(enc)
    assert h.levels[0].startswith("A") and h.levels[-1].startswith("C")
    n_a = sum(lv.startswith("A") for lv in h.levels)
    assert h.totals[:n_a].sum() > 0  # some pairs arrive nearly together
    assert h.totals[0] > 0  # ... and some of those within 1.5 s
    assert "| level |" in h.table()
    mpl = pytest.importorskip("matplotlib")
    mpl.use("Agg")
    ax = hierarchy.plot_hierarchy(h)
    assert len(ax.patches) == len(h.levels)


def test_scenario_summary_and_comparison():
    s1 = scenario.summarize_scenario(
        datasets.crossing(n_pairs=15, seed=0), "crossing", max_distance=100.0
    )
    s2 = scenario.summarize_scenario(
        datasets.merge(n_pairs=15, seed=0), "merge", max_distance=100.0
    )
    assert s1.metrics["encounters"] == 15
    assert s1.conflict_types["crossing"] > 0 and s2.conflict_types["lane-change"] == 0
    assert s1.metrics["road_users"] == 30
    md = scenario.compare_scenarios({"crossing": s1, "merge": s2})
    assert "crossing" in md and "merge" in md and "| level |" in md
    md2 = scenario.compare_scenarios({"a": datasets.pedestrian(n_pairs=5)}, ttc_threshold=2.0)
    assert "TET_s (TTC < 2 s)" in md2


def test_following_measures_ten_columns():
    tr = datasets.following(n_pairs=1, seed=0)
    out = scenario.following_measures(tr, leader=0, follower=1)
    for k in "ttc1 ttc2 ttc3 ttcd drac mdrac psd mpsd sdi dcia gap v_l v_f t".split():
        assert k in out and out[k].shape == out["t"].shape
    assert out["gap"][0] > 0
    assert np.nanmax(out["drac"]) > 0  # the follower closes in on the braking leader


def test_segment_distance_against_sampling():
    rng = np.random.default_rng(5)
    n = 200
    p1, p2 = rng.uniform(-20, 20, (n, 2)), rng.uniform(-20, 20, (n, 2))
    d1, d2 = rng.uniform(-30, 30, (n, 2)), rng.uniform(-30, 30, (n, 2))
    got = process._segment_distance(p1, d1, p2, d2)
    s = np.linspace(0, 1, 401)
    a = p1[:, None, :] + s[None, :, None] * d1[:, None, :]
    b = p2[:, None, :] + s[None, :, None] * d2[:, None, :]
    dist = np.linalg.norm(a[:, :, None, :] - b[:, None, :, :], axis=-1).min(axis=(1, 2))
    np.testing.assert_allclose(got, dist, atol=0.2)
    assert np.all(got <= dist + 1e-9)  # the exact value can only be smaller than the sampled one


def test_pet_for_pairs_that_never_come_close_in_space():
    tr = datasets.merge(n_pairs=4, seed=0)
    s = scenario.summarize_scenario(tr, "m")
    assert s.metrics["pairs with observed PET"] == 4  # passes seconds apart, tens of metres apart


def test_hyden_braking_limit():
    v = 50 / 3.6
    ta = process.hyden_braking_limit(v)
    assert ta == pytest.approx(v / (16.7 * np.exp(-0.0137 * 2 * v / 3)), rel=2e-3)  # as printed
    assert 0.9 < ta < 1.0
    assert process.hyden_braking_limit(v, friction0=0.55) == pytest.approx(1.46, abs=0.02)
    assert process.hyden_braking_limit(2 * v) > ta  # faster approach, longer minimum TA
    assert process.hyden_uniform_severity_ta(v, 2) == pytest.approx(2 * ta)
    assert 2.5 < process.hyden_uniform_severity_ta(70 / 3.6, 2) < 3.0
    with pytest.raises(ValueError):
        process.hyden_uniform_severity_ta(v, 3)


def test_hyden_severity_zones_and_serious_border():
    """Zones of ALT.DEF.2 (Hyden 1987, Figures 7.4 and 7.17): parallel copies, 0.5 s apart."""
    v = 50 / 3.6
    t_brake = process.hyden_uniform_severity_ta(v, 2)
    assert float(process.hyden_zone_offset(t_brake, v)) == pytest.approx(0.0, abs=1e-12)
    # zone 3 is the first on the safe side of the braking-time curve, then 2, then 1
    for shift, zone in [(-0.7, 5), (-0.2, 4), (0.0, 3), (0.3, 3), (0.5, 2), (0.9, 2), (1.0, 1),
                        (1.4, 1), (1.5, 0), (3.0, 0)]:  # fmt: skip
        assert float(process.hyden_severity_zone(t_brake + shift, v)) == zone
    # serious conflict = zone 2 or higher = offset < 1.0 s (section 7.3.9, p. 166)
    assert bool(process.hyden_serious_conflict(t_brake + 0.99, v))
    assert not bool(process.hyden_serious_conflict(t_brake + 1.0, v))
    # vectorised, NaN safe; the border moves to longer TA at higher speed
    ta = np.array([1.0, np.nan, 1.0])
    vv = np.array([v, v, 2 * v])
    zone = process.hyden_severity_zone(ta, vv)
    assert np.isnan(zone[1]) and zone[2] > zone[0]
    assert process.hyden_serious_conflict(ta, vv).tolist() == [True, False, True]
    assert process.HYDEN_ZONE_WIDTH == 0.5
