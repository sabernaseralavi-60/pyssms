r"""Readers (and one writer) for trajectory files: LevelX drone data, SSAM ``.trj``, SUMO, VISSIM.

Every reader returns a :class:`pyssms.trajectories.Trajectories` in SI units with the **centre** of
the body as reference point.

What has been checked, and against what (be explicit about it before trusting a reader):

* :func:`read_trj` / :func:`write_trj` follow the *SSAM File Format Specification 1.04* (Siemens
  ITS, 2004) and its 3.0 addition (elevation), downloaded from the SSAM repository
  (github.com/OSADP/SSAM, folder Documentation); the byte layout was also compared with the
  converter of SUMO (``sumolib/output/convert/trj.py``). Tested by round trip and by a file written
  with SUMO's byte layout; **not** yet opened with the SSAM program itself.
* :func:`read_levelx` follows the column names used by the reference loader of the data provider
  (``ika-rwth-aachen/drone-dataset-tools``, ``tracks_import.py``) for inD, rounD, exiD and uniD
  (``xCenter``, ``yCenter``, ``heading`` in degrees, ``length``, ``width``, ``xVelocity``,
  ``yVelocity``; frame rate and ``class`` from the ``*_recordingMeta.csv`` / ``*_tracksMeta.csv``
  files). The older highD layout (``x``, ``y`` of the upper-left corner, ``width`` along x and
  ``height`` along y) is coded from the data provider's description and has **not** been run on a
  real highD file. All LevelX readers are tested on synthetic files with these headers only.
* :func:`read_sumo_fcd` reads SUMO ``--fcd-output`` XML (``<timestep>`` with ``<vehicle>`` and
  ``<person>``) or the CSV written by SUMO's ``xml2csv.py``. SUMO reports the position of the
  *front bumper* of a vehicle and the heading as a compass angle (0 = north, clockwise);
  both are converted. Body sizes are not part of the FCD output and must be supplied.
* :func:`read_vissim_fzp` is driven by the ``$VEHICLE:`` header line of the file, so any attribute
  selection works as long as the needed attributes were selected in VISSIM; the attribute names
  default to the VISSIM names and can be changed. Not run on a real VISSIM file.
* There is no Aimsun-specific reader: Aimsun has no fixed trajectory file layout known to this
  package. Use :func:`read_table` with a column map, or write ``.trj`` from your tool.
"""

from __future__ import annotations

import csv
import json
import struct
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path

import numpy as np

from pyssms.geometry import FloatArray
from pyssms.trajectories import Trajectories, from_arrays

__all__ = [
    "build_levelx_cache",
    "load_levelx_fast",
    "read_levelx",
    "read_ngsim",
    "read_sumo_fcd",
    "read_table",
    "read_trj",
    "read_vissim_fzp",
    "write_trj",
]

_FT = 0.3048
#: Size (m) given to road users whose source gives no body size (pedestrians in drone data).
DEFAULT_VRU_SIZE = (0.5, 0.5)
#: ``(length, width)`` in m for SUMO vehicle types not in ``sizes`` (a passenger car).
DEFAULT_SUMO_SIZE = (4.5, 1.8)


# --------------------------------------------------------------------------- LevelX


def _header(path: Path, delimiter: str = ",") -> list[str]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [h.strip() for h in next(csv.reader(fh, delimiter=delimiter))]


def _numeric_columns(path: Path, names: list[str], delimiter: str = ",") -> dict[str, FloatArray]:
    head = _header(path, delimiter)
    missing = [n for n in names if n not in head]
    if missing:
        raise KeyError(f"{path.name}: missing columns {missing}; file has {head}")
    idx = [head.index(n) for n in names]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # numpy warns on an empty file; handled below
        data = np.loadtxt(path, delimiter=delimiter, skiprows=1, usecols=idx, ndmin=2)
    if data.size == 0:
        data = np.empty((0, len(names)))
    return {n: data[:, k] for k, n in enumerate(names)}


def _read_dicts(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [{k.strip(): v for k, v in row.items()} for row in csv.DictReader(fh)]


def read_levelx(
    tracks_csv: str | Path,
    tracks_meta_csv: str | Path | None = None,
    recording_meta_csv: str | Path | None = None,
    frame_rate: float | None = None,
    vru_size: tuple[float, float] = DEFAULT_VRU_SIZE,
) -> Trajectories:
    """Read one recording of a LevelX drone data set (inD, rounD, exiD, uniD, highD).

    Args:
        tracks_csv: ``NN_tracks.csv``.
        tracks_meta_csv: ``NN_tracksMeta.csv`` (gives the class of each road user); optional.
        recording_meta_csv: ``NN_recordingMeta.csv`` (gives ``frameRate``); optional. If neither
            this nor ``frame_rate`` is given, 25 Hz is assumed and recorded in ``meta``.
        frame_rate: Frame rate in Hz; overrides the meta file.
        vru_size: ``(length, width)`` in m used where the file gives no body size (zero), as for
            pedestrians. An assumption of this reader, not of the data provider.

    Returns:
        Trajectories with ``t = frame / frame_rate`` and ``meta['layout']`` = ``'xCenter'`` for the
        inD/rounD/exiD/uniD layout or ``'highD'`` for the corner-box layout.
    """
    tracks_csv = Path(tracks_csv)
    head = _header(tracks_csv)
    meta: dict[str, object] = {"file": tracks_csv.name}
    fr = frame_rate
    if fr is None and recording_meta_csv is not None:
        rec = _read_dicts(Path(recording_meta_csv))[0]
        fr = float(rec["frameRate"])
        meta["recording"] = rec
    if fr is None:
        fr = 25.0
        meta["frame_rate_assumed"] = True
    meta["frame_rate"] = fr

    if "xCenter" in head:
        meta["layout"] = "xCenter"
        c = _numeric_columns(
            tracks_csv,
            ["trackId", "frame", "xCenter", "yCenter", "heading", "width", "length",
             "xVelocity", "yVelocity"],
        )  # fmt: skip
        uid, x, y = c["trackId"], c["xCenter"], c["yCenter"]
        heading = np.deg2rad(c["heading"])
        length, width = c["length"], c["width"]
    elif "x" in head and "height" in head:
        meta["layout"] = "highD"
        c = _numeric_columns(
            tracks_csv, ["id", "frame", "x", "y", "width", "height", "xVelocity", "yVelocity"]
        )
        uid = c["id"]
        length, width = c["width"], c["height"]  # highD: 'width' is the extent along x
        x, y = c["x"] + length / 2.0, c["y"] + width / 2.0  # upper-left corner -> centre
        heading = np.arctan2(c["yVelocity"], c["xVelocity"])
    else:
        raise KeyError(
            f"{tracks_csv.name}: neither a LevelX 'xCenter' nor a highD 'x/height' layout"
        )

    unknown = (length <= 0) | (width <= 0)
    length = np.where(unknown, vru_size[0], length)
    width = np.where(unknown, vru_size[1], width)
    uid_i = uid.astype(np.int64)

    kinds = np.full(uid_i.shape, "", dtype=object)
    if tracks_meta_csv is not None:
        key = "trackId" if meta["layout"] == "xCenter" else "id"
        cls = {int(r[key]): r.get("class", "") for r in _read_dicts(Path(tracks_meta_csv))}
        ids, inverse = np.unique(uid_i, return_inverse=True)  # one lookup per track, not per row
        kinds = np.array([cls.get(int(u), "") for u in ids], dtype=object)[inverse]

    return from_arrays(
        t=c["frame"] / fr, uid=uid_i, x=x, y=y, heading=heading,
        vx=c["xVelocity"], vy=c["yVelocity"], length=length, width=width,
        kind=kinds.astype(str), source=f"LevelX {tracks_csv.name}", meta=meta,
    )  # fmt: skip


_CACHE_FIELDS = ("t", "uid", "x", "y", "heading", "vx", "vy", "length", "width", "kind")


def _cache_path(tracks_csv: Path, cache_dir: Path | None) -> Path:
    folder = cache_dir if cache_dir is not None else tracks_csv.parent / "_pyssms_cache"
    return folder / (tracks_csv.stem + ".npz")


def _fingerprint(tracks_csv: Path, **settings: object) -> str:
    st = tracks_csv.stat()
    return json.dumps({"size": st.st_size, "mtime_ns": st.st_mtime_ns, **settings}, sort_keys=True)


def build_levelx_cache(
    tracks_csv: str | Path,
    tracks_meta_csv: str | Path | None = None,
    recording_meta_csv: str | Path | None = None,
    cache_dir: str | Path | None = None,
    frame_rate: float | None = None,
    vru_size: tuple[float, float] = DEFAULT_VRU_SIZE,
    compress: bool = False,
) -> Path:
    """Read one LevelX recording with :func:`read_levelx` and store it as a NumPy ``.npz`` file.

    The cache holds the columns of :class:`~pyssms.trajectories.Trajectories` (float64, so reading
    it back is bit-identical to reading the CSV) and a fingerprint of the source file (size and
    modification time) and of the settings; :func:`load_levelx_fast` rebuilds it when either
    changes.

    The cache is **the data set itself in another format**: keep it next to the CSV files (the
    default, ``<folder>/_pyssms_cache``, inside the git-ignored ``data_raw``) and do not
    distribute it. The data providers' terms forbid redistributing the data set or modified
    versions of it.

    Args:
        tracks_csv: ``NN_tracks.csv``.
        tracks_meta_csv: ``NN_tracksMeta.csv`` (class of each road user).
        recording_meta_csv: ``NN_recordingMeta.csv`` (frame rate).
        cache_dir: Folder for the ``.npz`` file; default ``<folder of tracks_csv>/_pyssms_cache``.
        frame_rate: Overrides the frame rate of the meta file.
        vru_size: See :func:`read_levelx`.
        compress: Use ``savez_compressed`` (smaller, slower to read).

    Returns:
        Path of the cache file.
    """
    src = Path(tracks_csv)
    tr = read_levelx(src, tracks_meta_csv, recording_meta_csv, frame_rate, vru_size)
    out = _cache_path(src, Path(cache_dir) if cache_dir is not None else None)
    out.parent.mkdir(parents=True, exist_ok=True)
    save = np.savez_compressed if compress else np.savez
    save(
        out,
        **{f: getattr(tr, f) for f in _CACHE_FIELDS},
        fingerprint=np.array(
            _fingerprint(
                src,
                meta=str(tracks_meta_csv),
                rec=str(recording_meta_csv),
                fr=frame_rate,
                vru=list(vru_size),
            )
        ),
        info=np.array(json.dumps({"source": tr.source, "meta": tr.meta}, default=str)),
    )
    return out


def load_levelx_fast(
    tracks_csv: str | Path,
    tracks_meta_csv: str | Path | None = None,
    recording_meta_csv: str | Path | None = None,
    cache_dir: str | Path | None = None,
    frame_rate: float | None = None,
    vru_size: tuple[float, float] = DEFAULT_VRU_SIZE,
    rebuild: bool = False,
    compress: bool = False,
) -> Trajectories:
    """Like :func:`read_levelx`, but through a ``.npz`` cache that is built on first use.

    The cache is used only if its fingerprint (source size and modification time, meta file paths,
    frame rate and ``vru_size``) matches; otherwise it is rebuilt. Arguments as in
    :func:`build_levelx_cache`. ``meta`` of the result gains ``cache = True``; values that were not
    JSON-serialisable in ``meta`` come back as text.
    """
    src = Path(tracks_csv)
    path = _cache_path(src, Path(cache_dir) if cache_dir is not None else None)
    want = _fingerprint(
        src,
        meta=str(tracks_meta_csv),
        rec=str(recording_meta_csv),
        fr=frame_rate,
        vru=list(vru_size),
    )
    stale = rebuild or not path.exists()
    if not stale:
        with np.load(path, allow_pickle=False) as z:
            stale = str(z["fingerprint"]) != want
    if stale:
        build_levelx_cache(
            src, tracks_meta_csv, recording_meta_csv, cache_dir, frame_rate, vru_size, compress
        )
    with np.load(path, allow_pickle=False) as z:
        cols = {f: z[f] for f in _CACHE_FIELDS}
        info = json.loads(str(z["info"]))
    meta = dict(info["meta"])
    meta["cache"] = True
    return Trajectories(**cols, source=str(info["source"]), meta=meta)


# --------------------------------------------------------------------------- NGSIM

_NGSIM_CLASS = {1: "motorcycle", 2: "car", 3: "truck"}
#: Frame interval (s) of the NGSIM trajectory files ("Frame ID: units 1/10 of a second").
NGSIM_DT = 0.1


def read_ngsim(
    path: str | Path,
    coordinates: str = "global",
    heading_half_window: int = 5,
    min_heading_speed: float = 1.0,
    default_size: tuple[float, float] = (4.5, 1.8),
) -> Trajectories:
    """Read one NGSIM vehicle-trajectory file (US-101, I-80, Lankershim, Peachtree Street).

    Follows the *Vehicle Trajectory File Data Dictionary* shipped with each data set: whitespace
    separated, one row per vehicle and frame (0.1 s), columns 1-14 are vehicle id, frame id, total
    frames, epoch time (ms), local X, local Y, global X, global Y, length, width, class, velocity,
    acceleration and lane; everything else (preceding/following vehicle, origin and destination
    zones, ...) is ignored here. **Units are feet and are converted to metres.**

    Two points differ from the other readers and are assumptions of this reader, not of NGSIM:

    * NGSIM gives the position of the **front centre** of the vehicle. The centre of the body is
      the front centre moved back by half the length along the heading.
    * There is no heading column. The heading is the direction of the front-centre displacement
      over ``±heading_half_window`` frames (default 0.5 s each side, so it uses future frames: it is
      not causal), held at its last value while the displacement speed is below
      ``min_heading_speed``. The velocity vector is the data set's own speed column along that
      heading. NGSIM speeds and accelerations are known to be inconsistent with the positions
      (see the references in ``docs/ngsim_notes.md``); use :mod:`pyssms.preprocessing` before
      computing anything that depends on accelerations.

    Args:
        path: ``trajectories-*.txt``.
        coordinates: ``"global"`` (CA/GA State Plane, the only choice that is a single plane for
            the arterial sites) or ``"local"`` (section coordinates: lateral X, longitudinal Y;
            the right choice for a freeway section when only one direction matters).
        heading_half_window: Half-width (frames) of the displacement used for the heading.
        min_heading_speed: Speed (m/s) below which the heading is held.
        default_size: ``(length, width)`` in m used where the file gives a zero size.

    Returns:
        Trajectories with ``t = frame / 10`` and ``kind`` ``motorcycle``/``car``/``truck``.
        ``meta`` holds the epoch time (ms) of the first frame and the raw lane ids are not kept.
    """
    if coordinates not in ("global", "local"):
        raise ValueError("coordinates must be 'global' or 'local'")
    p = Path(path)
    with p.open(encoding="latin-1") as fh:
        ncol = len(fh.readline().split())
    if ncol < 14:
        raise ValueError(f"{p.name}: {ncol} columns, an NGSIM trajectory file has at least 14")
    raw = np.loadtxt(p, usecols=range(14), ndmin=2)
    vid, frame, epoch = raw[:, 0], raw[:, 1], raw[:, 3]
    cx, cy = (6, 7) if coordinates == "global" else (4, 5)
    fx, fy = raw[:, cx] * _FT, raw[:, cy] * _FT  # front centre (m)
    length, width = raw[:, 8] * _FT, raw[:, 9] * _FT
    speed = raw[:, 11] * _FT
    klass = raw[:, 10].astype(int)

    order = np.lexsort((frame, vid))
    inv = np.empty_like(order)
    inv[order] = np.arange(order.size)
    v_s, f_s, x_s, y_s = vid[order], frame[order], fx[order], fy[order]
    h_s = np.zeros_like(x_s)
    starts = np.flatnonzero(np.r_[True, v_s[1:] != v_s[:-1]])
    stops = np.r_[starts[1:], v_s.size]
    k = heading_half_window
    for s0, s1 in zip(starts, stops, strict=True):
        n = s1 - s0
        if n < 2:
            continue
        xs, ys = x_s[s0:s1], y_s[s0:s1]
        i = np.arange(n)
        hi, lo = np.minimum(i + k, n - 1), np.maximum(i - k, 0)
        df = np.maximum(f_s[s0:s1][hi] - f_s[s0:s1][lo], 1.0) * NGSIM_DT
        dx, dy = (xs[hi] - xs[lo]) / df, (ys[hi] - ys[lo]) / df
        h = np.arctan2(dy, dx)
        slow = np.hypot(dx, dy) < min_heading_speed
        if slow.all():
            h[:] = 0.0
        else:
            idx = np.where(~slow, i, -1)
            idx = np.maximum.accumulate(idx)  # last moving index so far
            first = int(np.flatnonzero(~slow)[0])
            idx[idx < 0] = first
            h = h[idx]
        h_s[s0:s1] = h
    heading = h_s[inv]
    ux, uy = np.cos(heading), np.sin(heading)
    unknown = (length <= 0) | (width <= 0)
    length = np.where(unknown, default_size[0], length)
    width = np.where(unknown, default_size[1], width)
    x, y = fx - 0.5 * length * ux, fy - 0.5 * length * uy
    kinds = np.array([_NGSIM_CLASS.get(int(c), "") for c in klass], dtype=object)
    meta = {
        "file": p.name,
        "frame_rate": 1.0 / NGSIM_DT,
        "coordinates": coordinates,
        "epoch_ms_first_frame": float(epoch[int(np.argmin(frame))]),
        "reference_point": "front centre moved back by half the length",
    }
    return from_arrays(
        t=(frame - float(np.min(frame))) * NGSIM_DT, uid=vid, x=x, y=y, heading=heading,
        vx=speed * ux, vy=speed * uy, length=length, width=width, kind=kinds.astype(str),
        source=f"NGSIM {p.name}", meta=meta,
    )  # fmt: skip


# --------------------------------------------------------------------------- SSAM .trj


def read_trj(path: str | Path) -> Trajectories:
    """Read an SSAM trajectory file (``.trj``, format 1.04 or 3.0), in metres and seconds.

    The file stores the middle of the front and rear bumper; the centre is their midpoint and the
    heading the direction rear -> front. ``x, y`` are multiplied by the file's scale; English units
    are converted to metric. Velocity is the recorded forward speed along the heading.
    """
    buf = Path(path).read_bytes()
    if len(buf) < 2 or buf[0] != 0:
        raise ValueError("not an SSAM trj file: first byte must be the FORMAT record (0)")
    end = {ord("L"): "<", ord("B"): ">"}.get(buf[1])
    if end is None:
        raise ValueError(f"unknown endian byte {buf[1]!r}")
    version = struct.unpack_from(end + "f", buf, 2)[0]
    off = 6
    has_z = False
    if version >= 2.0:  # 3.0 adds the Z Value Option byte to the FORMAT record
        has_z = buf[off] != 0
        off += 1
    if buf[off] != 1:
        raise ValueError("DIMENSIONS record (1) expected after FORMAT")
    metric = buf[off + 1] == 1
    scale = struct.unpack_from(end + "f", buf, off + 2)[0]
    off += 1 + 1 + 4 + 16
    unit = 1.0 if metric else _FT
    vfmt = struct.Struct(end + "iiB8f" + ("2f" if has_z else ""))
    rows: list[tuple[float, ...]] = []
    now = float("nan")
    n = len(buf)
    while off < n:
        rec = buf[off]
        if rec == 2:
            now = struct.unpack_from(end + "f", buf, off + 1)[0]
            off += 5
        elif rec == 3:
            v = vfmt.unpack_from(buf, off + 1)
            rows.append((now, *v[:2], *v[3:11]))
            off += 1 + vfmt.size
        else:
            raise ValueError(f"unknown record type {rec} at byte {off}")
    a = np.array(rows, dtype=float).reshape(-1, 11)
    t, vid, _, fx, fy, rx, ry, ln, wd, sp, _acc = (a[:, k] for k in range(11))
    fx, fy, rx, ry = (q * scale * unit for q in (fx, fy, rx, ry))
    heading = np.arctan2(fy - ry, fx - rx)
    spd = sp * unit
    return from_arrays(
        t=t, uid=vid.astype(np.int64), x=(fx + rx) / 2, y=(fy + ry) / 2, heading=heading,
        vx=spd * np.cos(heading), vy=spd * np.sin(heading), length=ln * unit, width=wd * unit,
        source=f"SSAM trj {Path(path).name}", meta={"trj_version": float(version), "z": has_z},
    )  # fmt: skip


def write_trj(traj: Trajectories, path: str | Path) -> None:
    """Write metric SSAM trajectory file (format 1.04, no elevation) from ``traj``.

    Bumper midpoints are centre -/+ half the length along the heading; bodies without a length
    get 4.5 m x 1.8 m. Speed is the velocity component along the heading and acceleration its
    finite difference per road user. Not yet opened with the SSAM program itself.
    """
    order = np.lexsort((traj.uid, traj.t))
    s = traj.select(np.ones(len(traj), bool))
    t, uid = s.t[order], s.uid[order]
    x, y, h = s.x[order], s.y[order], s.heading[order]
    ln = np.where(s.length[order] > 0, s.length[order], 4.5)
    wd = np.where(s.width[order] > 0, s.width[order], 1.8)
    spd = s.vx[order] * np.cos(h) + s.vy[order] * np.sin(h)
    acc = np.zeros_like(spd)
    for u in np.unique(uid):
        k = np.flatnonzero(uid == u)
        if k.size > 1:
            acc[k] = np.gradient(spd[k], t[k])
    fx, fy = x + ln / 2 * np.cos(h), y + ln / 2 * np.sin(h)
    rx, ry = x - ln / 2 * np.cos(h), y - ln / 2 * np.sin(h)
    lo = np.floor([np.min(x) - 5, np.min(y) - 5]).astype(int)
    hi = np.ceil([np.max(x) + 5, np.max(y) + 5]).astype(int)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBf", 0, ord("L"), 1.04))
        fh.write(struct.pack("<BBf4i", 1, 1, 1.0, lo[0], lo[1], hi[0], hi[1]))
        prev = None
        for i in range(t.size):
            if prev is None or t[i] != prev:
                fh.write(struct.pack("<Bf", 2, t[i]))
                prev = t[i]
            fh.write(
                struct.pack(
                    "<BiiB8f",
                    3,
                    int(uid[i]),
                    0,
                    0,
                    fx[i],
                    fy[i],
                    rx[i],
                    ry[i],
                    ln[i],
                    wd[i],
                    spd[i],
                    acc[i],
                )  # fmt: skip
            )


# --------------------------------------------------------------------------- SUMO


def _sumo_rows_xml(path: Path) -> list[tuple[float, str, str, float, float, float, float, str]]:
    out = []
    now = 0.0
    for _, el in ET.iterparse(path, events=("start", "end")):
        if _ == "start":
            if el.tag == "timestep":
                now = float(el.get("time", now))
            continue
        if el.tag in ("vehicle", "person"):
            out.append(
                (
                    now,
                    el.tag,
                    el.get("id", ""),
                    float(el.get("x", "nan")),
                    float(el.get("y", "nan")),
                    float(el.get("angle", "0")),
                    float(el.get("speed", "0")),
                    el.get("type", ""),
                )  # fmt: skip
            )
        if el.tag == "timestep":
            el.clear()
    return out


def _sumo_rows_csv(path: Path) -> list[tuple[float, str, str, float, float, float, float, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(2048)
        fh.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        out = []
        for r in csv.DictReader(fh, delimiter=delim):
            for tag in ("vehicle", "person"):
                if r.get(f"{tag}_id"):
                    out.append(
                        (
                            float(r["timestep_time"]),
                            tag,
                            r[f"{tag}_id"],
                            float(r[f"{tag}_x"]),
                            float(r[f"{tag}_y"]),
                            float(r.get(f"{tag}_angle") or 0.0),
                            float(r.get(f"{tag}_speed") or 0.0),
                            r.get(f"{tag}_type", "") or "",
                        )  # fmt: skip
                    )
    return out


def read_sumo_fcd(
    path: str | Path,
    sizes: Mapping[str, tuple[float, float]] | None = None,
    person_size: tuple[float, float] = DEFAULT_VRU_SIZE,
    reference: str = "front",
) -> Trajectories:
    """Read SUMO floating-car-data (``--fcd-output``) as XML or as ``xml2csv.py`` CSV.

    Args:
        path: ``.xml`` or ``.csv`` file.
        sizes: ``{vehicle type: (length, width)}`` in m; types not listed get a 4.5 m x 1.8 m car.
            FCD output carries no body sizes, so this is an input, not data.
        person_size: ``(length, width)`` of ``<person>`` entries.
        reference: ``'front'`` (SUMO's convention: the reported position is the front bumper) or
            ``'centre'`` if the file was produced with centred positions.

    Returns:
        Trajectories; velocity is ``speed`` along the heading; string ids are mapped to integers
        in order of first appearance (``meta['id_names']``).
    """
    p = Path(path)
    rows = _sumo_rows_csv(p) if p.suffix.lower() == ".csv" else _sumo_rows_xml(p)
    if not rows:
        raise ValueError(f"{p.name}: no <vehicle> or <person> entries found")
    names: dict[str, int] = {}
    sz = dict(sizes or {})
    t, uid, x, y, h, sp, ln, wd, kind = ([] for _ in range(9))
    for time, tag, name, xx, yy, ang, speed, vtype in rows:
        key = f"{tag}:{name}"
        uid.append(names.setdefault(key, len(names)))
        length, width = person_size if tag == "person" else sz.get(vtype, DEFAULT_SUMO_SIZE)
        heading = np.pi / 2 - np.deg2rad(ang)  # compass (0 = north, clockwise) -> maths
        if reference == "front" and tag == "vehicle":
            xx, yy = xx - length / 2 * np.cos(heading), yy - length / 2 * np.sin(heading)
        t.append(time)
        x.append(xx)
        y.append(yy)
        h.append(heading)
        sp.append(speed)
        ln.append(length)
        wd.append(width)
        kind.append("pedestrian" if tag == "person" else (vtype or "vehicle"))
    ha, sa = np.array(h), np.array(sp)
    return from_arrays(
        t=t, uid=uid, x=x, y=y, heading=ha, vx=sa * np.cos(ha), vy=sa * np.sin(ha),
        length=ln, width=wd, kind=np.array(kind),
        source=f"SUMO FCD {p.name}", meta={"id_names": list(names), "reference": reference},
    )  # fmt: skip


# --------------------------------------------------------------------------- VISSIM / generic


def _parse_table(
    path: str | Path, delimiter: str, skip_prefixes: tuple[str, ...], header_prefix: str
) -> tuple[dict[str, int], list[list[str]]]:
    """Header (upper-cased name -> column index) and the split data rows of a delimited file."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if header_prefix:
        hi = next(i for i, ln in enumerate(lines) if ln.startswith(header_prefix))
        header = [h.strip() for h in lines[hi][len(header_prefix) :].split(delimiter)]
        body = [ln for ln in lines[hi + 1 :] if ln.strip() and not ln.startswith(skip_prefixes)]
    else:
        body_all = [ln for ln in lines if ln.strip() and not ln.startswith(skip_prefixes)]
        header = [h.strip() for h in body_all[0].split(delimiter)]
        body = body_all[1:]
    index = {h.upper(): i for i, h in enumerate(header)}
    return index, [ln.split(delimiter) for ln in body]


def _column(
    index: dict[str, int], rows: list[list[str]], name: str, text: bool = False
) -> FloatArray:
    i = index.get(name.upper())
    if i is None:
        raise KeyError(f"column {name!r} not in header {list(index)}")
    out: FloatArray = (
        np.array([r[i] for r in rows]) if text else np.array([float(r[i]) for r in rows])
    )
    return out


def read_table(
    path: str | Path,
    columns: Mapping[str, str],
    delimiter: str = ";",
    skip_prefixes: tuple[str, ...] = ("*", "#"),
    time_scale: float = 1.0,
    length_scale: float = 1.0,
    length: float = DEFAULT_SUMO_SIZE[0],
    width: float = DEFAULT_SUMO_SIZE[1],
    header_prefix: str = "",
) -> Trajectories:
    """Generic delimited trajectory table (Aimsun exports, your own CSV).

    Args:
        path: Text file with a header line (column names are matched case-insensitively).
        columns: Maps ``t``, ``uid``, ``x``, ``y`` to header names (centre positions), optionally
            ``heading`` (radians), ``vx``, ``vy``, ``length``, ``width``, ``kind``. A heading in
            degrees is not converted: pre-convert or leave it out (then derived from velocity).
        delimiter: Field separator.
        skip_prefixes: Lines starting with one of these are ignored.
        time_scale: Multiply times by this to get seconds.
        length_scale: Multiply distances and speeds by this to get metres.
        length: Body length (m) used if no ``length`` column is mapped.
        width: Body width (m) used if no ``width`` column is mapped.
        header_prefix: If given, the header is the line starting with this prefix, which is
            removed (VISSIM: ``'$VEHICLE:'``).
    """
    index, rows = _parse_table(path, delimiter, skip_prefixes, header_prefix)
    num = {
        k: _column(index, rows, columns[k])
        for k in ("t", "uid", "x", "y", "heading", "vx", "vy", "length", "width")
        if k in columns
    }
    kind = _column(index, rows, columns["kind"], text=True) if "kind" in columns else ""
    return from_arrays(
        t=num["t"] * time_scale, uid=num["uid"].astype(np.int64), x=num["x"] * length_scale,
        y=num["y"] * length_scale, heading=num.get("heading"),
        vx=None if "vx" not in num else num["vx"] * length_scale,
        vy=None if "vy" not in num else num["vy"] * length_scale,
        length=num["length"] * length_scale if "length" in num else length,
        width=num["width"] * length_scale if "width" in num else width,
        kind=kind, source=f"table {Path(path).name}",
    )  # fmt: skip


def read_vissim_fzp(
    path: str | Path,
    front: tuple[str, str] = ("COORDFRONTX", "COORDFRONTY"),
    rear: tuple[str, str] = ("COORDREARX", "COORDREARY"),
    time: str = "SIMSEC",
    uid: str = "NO",
    length: float = DEFAULT_SUMO_SIZE[0],
    width: float = DEFAULT_SUMO_SIZE[1],
) -> Trajectories:
    """Read a PTV VISSIM vehicle record (``.fzp``) with front and rear bumper coordinates.

    The file must contain the attributes named by ``time``, ``uid``, ``front`` and ``rear``
    (select them in VISSIM's vehicle-record configuration; the defaults are VISSIM's attribute
    names). Centre = midpoint, heading = direction rear -> front, velocity by finite differences
    of the centre (independent of VISSIM's speed unit). Not run on a real VISSIM file.
    """
    index, rows = _parse_table(path, ";", ("*", "#"), "$VEHICLE:")
    fx, fy = _column(index, rows, front[0]), _column(index, rows, front[1])
    rx, ry = _column(index, rows, rear[0]), _column(index, rows, rear[1])
    return from_arrays(
        t=_column(index, rows, time), uid=_column(index, rows, uid).astype(np.int64),
        x=(fx + rx) / 2, y=(fy + ry) / 2, heading=np.arctan2(fy - ry, fx - rx),
        length=length, width=width, source=f"VISSIM {Path(path).name}",
    )  # fmt: skip
