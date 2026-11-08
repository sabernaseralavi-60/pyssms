"""NGSIM reader, smoothing, conflict windows, the shipped bank and the plots."""

import numpy as np
import pytest

from pyssms import bank, datasets, io, preprocessing
from pyssms.trajectories import from_arrays

FT = 0.3048


def _ngsim_file(path, rows):
    """Rows (id, frame, x_ft, y_ft, length_ft, width_ft, cls, v_fts) in the 18-column layout."""
    lines = []
    for vid, fr, x, y, ln, wd, cls, v in rows:
        lines.append(
            f"{vid:5d} {fr:5d} 100 {1118846980200 + 100 * fr:14d} {x:9.3f} {y:9.3f} "
            f"{x + 1000:12.3f} {y + 2000:12.3f} {ln:5.1f} {wd:5.1f} {cls:3d} {v:7.2f} "
            "0.00 2 0 0 0.00 0.00"
        )
    path.write_text("\n".join(lines) + "\n")


def test_read_ngsim_units_reference_point_and_heading(tmp_path):
    # vehicle 1 drives along +y (global) at 20 ft/s, front centre y = 10 + 2 ft per frame;
    # vehicle 2 stands still; class 3 = truck
    rows = [(1, f, 5.0, 10.0 + 2.0 * f, 15.0, 6.0, 2, 20.0) for f in range(1, 31)]
    rows += [(2, f, 50.0, 80.0, 40.0, 8.0, 3, 0.0) for f in range(1, 31)]
    p = tmp_path / "trajectories-test.txt"
    _ngsim_file(p, rows)
    tr = io.read_ngsim(p, coordinates="local")
    assert tr.dt == pytest.approx(0.1)
    assert tr.meta["frame_rate"] == 10.0
    a = tr.track(1)
    assert a.kind[0] == "car" and tr.track(2).kind[0] == "truck"
    np.testing.assert_allclose(a.length, 15.0 * FT)
    np.testing.assert_allclose(a.heading, np.pi / 2, atol=1e-9)
    np.testing.assert_allclose(np.hypot(a.vx, a.vy), 20.0 * FT)
    # front centre at y_ft -> body centre half a length behind it, along the heading
    front_y = (10.0 + 2.0 * np.arange(1, 31)) * FT
    np.testing.assert_allclose(a.y, front_y - 0.5 * 15.0 * FT, atol=1e-9)
    np.testing.assert_allclose(a.x, 5.0 * FT, atol=1e-9)
    s = tr.track(2)
    np.testing.assert_allclose(np.hypot(s.vx, s.vy), 0.0, atol=1e-12)
    assert np.all(np.isfinite(s.heading))


def test_read_ngsim_global_and_errors(tmp_path):
    rows = [(1, f, 5.0, 10.0 + 2.0 * f, 15.0, 6.0, 2, 20.0) for f in range(1, 6)]
    p = tmp_path / "t.txt"
    _ngsim_file(p, rows)
    g = io.read_ngsim(p)
    assert g.meta["coordinates"] == "global"
    assert g.x[0] > 1000 * FT - 20  # global X = x + 1000 ft in the synthetic file
    with pytest.raises(ValueError):
        io.read_ngsim(p, coordinates="polar")
    (tmp_path / "short.txt").write_text("1 2 3 4 5\n")
    with pytest.raises(ValueError):
        io.read_ngsim(tmp_path / "short.txt")


def test_moving_average_causal_and_centred():
    v = np.arange(10.0)
    c = preprocessing.moving_average(v, 3, causal=True)
    np.testing.assert_allclose(c[2:], (v[2:] + v[1:-1] + v[:-2]) / 3)
    assert c[0] == v[0] and c[1] == pytest.approx(0.5)
    w = v.copy()
    w[6:] += 100.0  # change the future: earlier outputs must not move
    np.testing.assert_allclose(preprocessing.moving_average(w, 3, causal=True)[:6], c[:6])
    z = preprocessing.moving_average(v, 3, causal=False)
    np.testing.assert_allclose(z[1:-1], v[1:-1])  # a line is unchanged by a centred mean
    with pytest.raises(ValueError):
        preprocessing.moving_average(v, 4, causal=False)
    with pytest.raises(ValueError):
        preprocessing.moving_average(v, 0)


def test_smooth_trajectories_reduces_noise_and_keeps_labels():
    rng = np.random.default_rng(1)
    t = np.arange(0, 20, 0.1)
    x = 10.0 * t + rng.normal(0, 0.3, t.size)
    tr = from_arrays(t=t, uid=np.zeros(t.size), x=x, y=np.zeros_like(t), length=4.5, width=1.8)
    for causal, win in ((True, 5), (False, 5)):
        sm = preprocessing.smooth_trajectories(tr, window=win, causal=causal)
        assert sm.meta["smoothing"] == {"window": win, "causal": causal}
        assert np.std(sm.vx[10:-10] - 10.0) < np.std(tr.vx[10:-10] - 10.0)
        np.testing.assert_array_equal(sm.uid, tr.uid)
        np.testing.assert_allclose(sm.length, tr.length)
    lag = preprocessing.smooth_trajectories(tr, window=5, causal=True)
    assert np.mean(tr.x[20:-20] - lag.x[20:-20]) == pytest.approx(10.0 * 0.2, abs=0.15)  # 2 frames


def _crossing_bank():
    tr = datasets.make("crossing", n_pairs=6, seed=3)
    return bank.extract_conflicts(tr, n_collision=3, n_crossing=2, n_none=1, name="syn")


def test_extract_conflicts_windows(tmp_path):
    b = _crossing_bank()
    assert 0 < len(b) <= 6
    assert set(np.asarray(b.table["level"])) <= {"A", "B", "C"}
    for k in range(len(b)):
        w = b.window(k)
        assert set(w.ids.tolist()) == {0, 1}
        assert w.t.min() == 0.0
        assert w.t.max() <= 10.0 + 1e-9
        assert abs(float(b.table["t_centre"][k])) >= 0
    assert abs(float(b.rows.x.mean())) < 100  # shifted to a local origin
    with pytest.raises(IndexError):
        b.window(len(b))
    path = bank.save_bank(b, tmp_path / "b.npz")
    with np.load(path, allow_pickle=False) as z:
        back = bank._read_bank(z)
    assert len(back) == len(b)
    np.testing.assert_array_equal(back.table["level"], b.table["level"])
    np.testing.assert_allclose(back.window(0).x, b.window(0).x)
    both = bank.concat_banks([b, b], "twice")
    assert len(both) == 2 * len(b)
    assert set(both.window(len(b)).ids.tolist()) == {0, 1}
    with pytest.raises(ValueError):
        bank.concat_banks([], "none")


def test_extract_conflicts_none_when_no_pairs():
    t = np.arange(0, 5, 0.1)
    far = from_arrays(
        t=np.r_[t, t], uid=np.r_[np.zeros(t.size), np.ones(t.size)], x=np.r_[t, t] * 10,
        y=np.r_[np.zeros(t.size), np.full(t.size, 500.0)], length=4.5, width=1.8,
    )  # fmt: skip
    assert len(bank.extract_conflicts(far)) == 0


def test_shipped_bank_and_summary():
    assert "ngsim" in bank.available_banks()
    b = datasets.load_conflict_bank("ngsim")
    assert len(b) >= 20
    assert {"A", "B"} <= set(np.asarray(b.table["level"]))
    assert set(np.asarray(b.table["site"])) <= {"US-101", "I-80", "Lankershim", "Peachtree"}
    assert "Attribution 2.0" in b.info and "FHWA" in b.info
    w = b.window(0)
    assert len(w) > 20 and set(w.ids.tolist()) == {0, 1}
    # the table agrees with the indicators recomputed from the shipped window itself
    from pyssms import process

    checked = 0
    for k in b.select("A")[:6]:
        e = process.pair_series(b.window(k), 0, 1, horizon=10.0)
        assert e is not None
        assert float(np.nanmin(e.ttc)) == pytest.approx(float(b.table["min_ttc"][k]), abs=1e-6)
        assert float(np.nanmin(e.ttc)) > 0.0  # overlapping bodies were dropped at extraction
        checked += 1
    for k in b.select("B")[:4]:
        e = process.pair_series(b.window(k), 0, 1, horizon=10.0)
        assert e is not None
        assert float(np.nanmin(e.tadv)) == pytest.approx(float(b.table["min_tadv"][k]), abs=1e-6)
        checked += 1
    assert checked == 10
    with pytest.raises(KeyError):
        datasets.load_conflict_bank("inD")  # German data are never shipped
    s = datasets.load_summary()
    assert {"inD", "rounD", "uniD", "exiD", "highD"} <= set(s)
    from importlib import resources

    d = resources.files("pyssms").joinpath("data")
    assert "FHWA" in d.joinpath("NGSIM_LICENSE.txt").read_text(encoding="utf-8")
    size = len(d.joinpath("conflict_bank_ngsim.npz").read_bytes())
    assert size < 3_000_000


def test_viz_smoke():
    plt = pytest.importorskip("matplotlib.pyplot")
    import matplotlib

    matplotlib.use("Agg")
    from pyssms import process, rectangle, viz
    from pyssms.disturbance import disturbance_set

    s = rectangle(np.array([0.0]), 4.5, 1.8)
    s2 = rectangle(np.array([np.pi / 2]), 4.5, 1.8)
    p1, v1 = np.array([-30.0, 0.0]), np.array([10.0, 0.0])
    p2, v2 = np.array([0.0, -40.0]), np.array([0.0, 10.0])
    ax = viz.plot_conflict_polygon(s, p1, v1, s2, p2, v2)
    assert ax.get_title().startswith("state")
    d = disturbance_set(s, p1[None], v1[None], s2, p2[None], v2[None], np.array([[1.0, 0.0]]))
    viz.plot_disturbance_set(d, 0, 0.5, 0.5)
    encs = process.encounters(datasets.make("crossing", n_pairs=4, seed=0))
    assert encs
    viz.plot_indicator_profile(encs[0])
    plt.close("all")
