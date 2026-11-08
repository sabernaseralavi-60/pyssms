"""Readers and the writer: round trips and files in the documented layouts (synthetic content)."""

import struct

import numpy as np
import pytest

from pyssms import datasets, io
from pyssms.trajectories import from_arrays


def _traj():
    t = np.arange(0, 2.0, 0.1)
    x = 5.0 * t
    return from_arrays(
        t=np.r_[t, t], uid=np.r_[np.zeros(t.size), np.ones(t.size)], x=np.r_[x, x + 30.0],
        y=np.r_[np.zeros(t.size), np.full(t.size, 3.0)], length=4.5, width=1.8,
    )  # fmt: skip


def test_trj_round_trip(tmp_path):
    tr = _traj()
    p = tmp_path / "a.trj"
    io.write_trj(tr, p)
    back = io.read_trj(p)
    assert len(back) == len(tr)
    key = np.lexsort((tr.t, tr.uid))
    key2 = np.lexsort((back.t, back.uid))
    np.testing.assert_allclose(back.x[key2], tr.x[key], atol=1e-4)
    np.testing.assert_allclose(back.y[key2], tr.y[key], atol=1e-4)
    np.testing.assert_allclose(back.heading[key2], tr.heading[key], atol=1e-4)
    np.testing.assert_allclose(
        np.hypot(back.vx, back.vy)[key2], np.hypot(tr.vx, tr.vy)[key], atol=1e-4
    )
    np.testing.assert_allclose(back.length, 4.5, atol=1e-5)


def _sumo_style_trj(path, z=False):
    """A file laid out byte by byte as in SSAM spec 1.04 / 3.0 and SUMO's converter."""
    out = struct.pack("=cc", b"\x00", b"L") + struct.pack("f", 3.0 if z else 1.04)
    if z:
        out += b"\x01"
    out += b"\x01\x01" + struct.pack("=f", 1.0) + struct.pack("=4i", 0, 0, 100, 100)
    for k in range(3):
        out += b"\x02" + struct.pack("=f", 0.5 * k)
        fmt = "=iiB8f" + ("2f" if z else "")
        args = [7, 2, 1, 10.0 + k, 20.0, 5.5 + k, 20.0, 4.5, 1.8, 2.0, 0.0]
        out += b"\x03" + struct.pack(fmt, *args, *([0.0, 0.0] if z else []))
    path.write_bytes(out)


@pytest.mark.parametrize("z", [False, True])
def test_trj_reads_spec_layout(tmp_path, z):
    p = tmp_path / "s.trj"
    _sumo_style_trj(p, z)
    tr = io.read_trj(p)
    assert len(tr) == 3 and set(tr.uid) == {7}
    np.testing.assert_allclose(tr.x, [7.75, 8.75, 9.75])  # midpoint of front 10 and rear 5.5
    np.testing.assert_allclose(tr.heading, 0.0)
    np.testing.assert_allclose(tr.vx, 2.0)
    np.testing.assert_allclose(tr.t, [0.0, 0.5, 1.0])
    assert tr.meta["z"] is z


def test_trj_english_units(tmp_path):
    out = struct.pack("=cc", b"\x00", b"L") + struct.pack("f", 1.04)
    out += b"\x01\x00" + struct.pack("=f", 1.0) + struct.pack("=4i", 0, 0, 100, 100)
    out += b"\x02" + struct.pack("=f", 0.0)
    out += b"\x03" + struct.pack("=iiB8f", 1, 1, 0, 10.0, 0.0, 0.0, 0.0, 15.0, 6.0, 10.0, 0.0)
    p = tmp_path / "e.trj"
    p.write_bytes(out)
    tr = io.read_trj(p)
    assert tr.length[0] == pytest.approx(15.0 * 0.3048)
    assert tr.x[0] == pytest.approx(5.0 * 0.3048)
    assert tr.vx[0] == pytest.approx(10.0 * 0.3048)


def test_trj_rejects_garbage(tmp_path):
    p = tmp_path / "bad.trj"
    p.write_bytes(b"hello")
    with pytest.raises(ValueError):
        io.read_trj(p)


LEVELX_TRACKS = (
    "recordingId,trackId,frame,trackLifetime,xCenter,yCenter,heading,width,length,"
    "xVelocity,yVelocity,xAcceleration,yAcceleration,lonVelocity,latVelocity,"
    "lonAcceleration,latAcceleration\n"
)


def test_levelx_new_layout(tmp_path):
    rows = ""
    for f in range(5):
        rows += f"0,1,{f},{f},{10 + f * 0.4},5,90.0,1.8,4.5,0,10,0,0,10,0,0,0\n"
        rows += f"0,2,{f},{f},20,{f * 0.05},0,0,0,1.2,0,0,0,1.2,0,0,0\n"
    (tmp_path / "00_tracks.csv").write_text(LEVELX_TRACKS + rows)
    (tmp_path / "00_tracksMeta.csv").write_text(
        "recordingId,trackId,initialFrame,finalFrame,numFrames,width,length,class\n"
        "0,1,0,4,5,1.8,4.5,car\n0,2,0,4,5,0,0,pedestrian\n"
    )
    (tmp_path / "00_recordingMeta.csv").write_text(
        "recordingId,frameRate,orthoPxToMeter\n0,25,0.0126\n"
    )
    tr = io.read_levelx(
        tmp_path / "00_tracks.csv",
        tmp_path / "00_tracksMeta.csv",
        tmp_path / "00_recordingMeta.csv",
    )
    assert tr.meta["layout"] == "xCenter" and tr.meta["frame_rate"] == 25.0
    assert tr.dt == pytest.approx(0.04)
    car = tr.track(1)
    assert car.kind[0] == "car" and car.heading[0] == pytest.approx(np.pi / 2)
    ped = tr.track(2)
    assert ped.kind[0] == "pedestrian"
    assert (ped.length[0], ped.width[0]) == io.DEFAULT_VRU_SIZE  # zero size replaced by the default


def test_levelx_frame_rate_assumed(tmp_path):
    (tmp_path / "t.csv").write_text(LEVELX_TRACKS + "0,1,0,0,1,1,0,1.8,4.5,1,0,0,0,1,0,0,0\n")
    tr = io.read_levelx(tmp_path / "t.csv")
    assert tr.meta["frame_rate_assumed"] is True


def test_levelx_highd_layout(tmp_path):
    (tmp_path / "h.csv").write_text(
        "frame,id,x,y,width,height,xVelocity,yVelocity\n0,3,100.0,20.0,4.0,1.8,-30,0\n"
        "1,3,98.8,20.0,4.0,1.8,-30,0\n"
    )
    tr = io.read_levelx(tmp_path / "h.csv", frame_rate=25.0)
    assert tr.meta["layout"] == "highD"
    assert tr.x[0] == pytest.approx(102.0) and tr.y[0] == pytest.approx(20.9)
    assert tr.length[0] == 4.0 and tr.width[0] == 1.8
    assert tr.heading[0] == pytest.approx(np.pi)


def test_levelx_missing_columns(tmp_path):
    (tmp_path / "x.csv").write_text("a,b\n1,2\n")
    with pytest.raises(KeyError):
        io.read_levelx(tmp_path / "x.csv")


SUMO_XML = """<?xml version="1.0"?>
<fcd-export>
  <timestep time="0.00">
    <vehicle id="a" x="10.00" y="0.00" angle="90.00" type="car" speed="10.00"/>
    <person id="p" x="20.00" y="-5.00" angle="0.00" speed="1.40" edge="e"/>
  </timestep>
  <timestep time="0.10">
    <vehicle id="a" x="11.00" y="0.00" angle="90.00" type="car" speed="10.00"/>
    <person id="p" x="20.00" y="-4.86" angle="0.00" speed="1.40" edge="e"/>
  </timestep>
</fcd-export>
"""


def test_sumo_fcd_xml(tmp_path):
    p = tmp_path / "fcd.xml"
    p.write_text(SUMO_XML)
    tr = io.read_sumo_fcd(p, sizes={"car": (5.0, 2.0)})
    assert tr.meta["id_names"] == ["vehicle:a", "person:p"]
    car = tr.track(0)
    assert car.heading[0] == pytest.approx(0.0)  # compass 90 = east = maths 0
    assert car.x[0] == pytest.approx(10.0 - 2.5)  # front bumper -> centre
    assert car.vx[0] == pytest.approx(10.0) and car.length[0] == 5.0
    ped = tr.track(1)
    assert ped.heading[0] == pytest.approx(np.pi / 2)  # compass 0 = north
    assert ped.vy[0] == pytest.approx(1.4) and ped.kind[0] == "pedestrian"


def test_sumo_fcd_csv(tmp_path):
    p = tmp_path / "fcd.csv"
    p.write_text(
        "timestep_time;vehicle_angle;vehicle_id;vehicle_speed;vehicle_type;vehicle_x;vehicle_y\n"
        "0.00;90.00;a;10.00;car;10.00;0.00\n0.10;90.00;a;10.00;car;11.00;0.00\n"
    )
    tr = io.read_sumo_fcd(p, reference="centre")
    assert len(tr) == 2 and tr.x[0] == 10.0


def test_vissim_fzp(tmp_path):
    p = tmp_path / "v.fzp"
    p.write_text(
        "* VISSIM\n* comment\n$VEHICLE:SIMSEC;NO;COORDFRONTX;COORDFRONTY;COORDREARX;COORDREARY\n"
        "0.0;5;12.0;3.0;8.0;3.0\n0.1;5;13.0;3.0;9.0;3.0\n"
    )
    tr = io.read_vissim_fzp(p)
    assert tr.x[0] == pytest.approx(10.0) and tr.heading[0] == pytest.approx(0.0)
    assert tr.vx[0] == pytest.approx(10.0)  # finite difference, independent of VISSIM's units
    with pytest.raises(KeyError):
        io.read_vissim_fzp(p, front=("NOPE", "COORDFRONTY"))


def test_read_table(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("time,id,px,py\n0,1,0,0\n1,1,10,0\n")
    tr = io.read_table(p, {"t": "time", "uid": "id", "x": "px", "y": "py"}, delimiter=",")
    assert tr.vx[0] == pytest.approx(10.0)


def test_scenarios_build_and_trj_round_trip(tmp_path):
    for name in datasets.SCENARIOS:
        tr = datasets.make(name, n_pairs=2, seed=1)
        assert tr.meta["synthetic"] and tr.ids.size >= 4
        p = tmp_path / f"{name}.trj"
        io.write_trj(tr, p)
        assert len(io.read_trj(p)) == len(tr)
    with pytest.raises(KeyError):
        datasets.make("nope")


def test_levelx_cache_round_trip_and_staleness(tmp_path):
    rows = ""
    for f in range(6):
        rows += f"0,1,{f},{f},{10 + f * 0.4},5,90.0,1.8,4.5,0,10,0,0,10,0,0,0\n"
        rows += f"0,2,{f},{f},20,{f * 0.05},0,0,0,1.2,0,0,0,1.2,0,0,0\n"
    tracks = tmp_path / "00_tracks.csv"
    tracks.write_text(LEVELX_TRACKS + rows)
    meta = tmp_path / "00_tracksMeta.csv"
    meta.write_text(
        "recordingId,trackId,initialFrame,finalFrame,numFrames,width,length,class\n"
        "0,1,0,5,6,1.8,4.5,car\n0,2,0,5,6,0,0,pedestrian\n"
    )
    rec = tmp_path / "00_recordingMeta.csv"
    rec.write_text("recordingId,frameRate,orthoPxToMeter\n0,25,0.0126\n")
    slow = io.read_levelx(tracks, meta, rec)
    out = io.build_levelx_cache(tracks, meta, rec)
    assert out.parent.name == "_pyssms_cache" and out.exists()
    fast = io.load_levelx_fast(tracks, meta, rec)
    for f in ("t", "uid", "x", "y", "heading", "vx", "vy", "length", "width", "kind"):
        np.testing.assert_array_equal(getattr(fast, f), getattr(slow, f), err_msg=f)
    assert fast.meta["cache"] is True and fast.meta["frame_rate"] == 25.0
    # unchanged source: the cache file is reused (not rewritten)
    stamp = out.stat().st_mtime_ns
    io.load_levelx_fast(tracks, meta, rec)
    assert out.stat().st_mtime_ns == stamp
    # changed settings or source: rebuilt
    io.load_levelx_fast(tracks, meta, rec, vru_size=(0.7, 0.7))
    assert out.stat().st_mtime_ns != stamp
    again = io.load_levelx_fast(tracks, meta, rec, vru_size=(0.7, 0.7))
    assert again.length[again.uid == 2][0] == pytest.approx(0.7)
    tracks.write_text(LEVELX_TRACKS + rows + "0,1,6,6,12.4,5,90.0,1.8,4.5,0,10,0,0,10,0,0,0\n")
    assert len(io.load_levelx_fast(tracks, meta, rec, vru_size=(0.7, 0.7))) == len(slow) + 1
