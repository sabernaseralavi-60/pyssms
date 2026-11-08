"""Conflict windows: extract them from trajectories, store them, load the shipped ones.

A **conflict window** is the stretch of a pair's trajectories (by default 5 s each side) around the
moment its encounter was closest by one of the package's own indicators. A *bank* is a set of such
windows with a table that says where each came from and how it was chosen.

What the shipped bank is, and is not
------------------------------------
``load_conflict_bank("ngsim")`` returns windows cut from the FHWA **NGSIM** vehicle-trajectory data
(US-101, I-80, Lankershim Boulevard, Peachtree Street). NGSIM is licensed by the Federal Highway
Administration under a modified Creative Commons Attribution 2.0 licence (not public domain, not
CC0): reuse and redistribution are free **if credit is given to FHWA and the NGSIM program and if
any reuse states that it is subject to that licence** (``pyssms/data/NGSIM_LICENSE.txt``, copied
from the archives). The data are provided "as is". Positions were shifted to a local origin;
nothing else was changed (feet were converted to metres, the front-centre reference point to the
body centre, :func:`pyssms.io.read_ngsim`), and smoothing was applied as recorded in the table.

The windows are **chosen by the package's own indicators** (the most severe pairs by TTC for
collision courses, by Time Advantage for crossing courses, the closest pairs otherwise). They are
examples, test material and a starting point for method development. They are **not a random
sample**, so no frequency, rate or distribution may be read from them, and using them to compare
the indicators that selected them would be circular.

Data of the German drone data sets (inD, rounD, uniD, exiD, highD) are never shipped: only
aggregated counts and scales (:func:`load_summary`) that contain no trajectory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np

from pyssms import process
from pyssms.geometry import FloatArray, IntArray
from pyssms.trajectories import Trajectories

__all__ = [
    "ConflictBank",
    "available_banks",
    "concat_banks",
    "extract_conflicts",
    "load_conflict_bank",
    "load_summary",
    "save_bank",
]

_COLS = ("t", "x", "y", "heading", "vx", "vy", "length", "width")
_TABLE_NUM = ("min_ttc", "min_tadv", "min_distance", "t_centre")
_TABLE_INT = ("id_a", "id_b")
_TABLE_STR = ("level", "site", "period", "selection")
LEVELS = ("A", "B", "C")
_BATCH = 3000  # pairs per batch of encounters


@dataclass(frozen=True)
class ConflictBank:
    """A set of conflict windows.

    Attributes:
        name: Name of the bank.
        table: One entry per window, as arrays of equal length: ``level`` (``'A'`` collision
            course at some moment, ``'B'`` crossing courses only, ``'C'`` no overlap of the future
            paths), ``min_ttc`` (s, NaN if never on a collision course), ``min_tadv`` (s),
            ``min_distance`` (m), ``t_centre`` (s, in the time of the source file), ``id_a``,
            ``id_b`` (road-user ids of the source file), ``site``, ``period`` and ``selection``
            (the rule that picked the window).
        rows: Long table of all windows stacked (``uid`` is ``2 * k`` and ``2 * k + 1`` for window
            ``k``; ``t`` runs from 0 at the start of the window).
        row_start: ``(n_windows + 1,)`` row offsets of the windows in ``rows``.
        info: Free text about the origin, licence and preprocessing.
    """

    name: str
    table: dict[str, Any]
    rows: Trajectories
    row_start: IntArray
    info: str

    def __len__(self) -> int:
        """Number of windows."""
        return int(self.row_start.size - 1)

    def window(self, k: int) -> Trajectories:
        """Trajectories of window ``k`` (two road users, ``uid`` 0 and 1, ``t`` from 0)."""
        if not 0 <= k < len(self):
            raise IndexError(f"window {k} out of range 0..{len(self) - 1}")
        s = slice(int(self.row_start[k]), int(self.row_start[k + 1]))
        r = self.rows
        return Trajectories(
            t=r.t[s], uid=r.uid[s] - 2 * k, x=r.x[s], y=r.y[s], heading=r.heading[s], vx=r.vx[s],
            vy=r.vy[s], length=r.length[s], width=r.width[s], kind=r.kind[s],
            source=f"{self.name} window {k}", meta={"window": k},
        )  # fmt: skip

    def select(self, level: str) -> list[int]:
        """Indices of the windows of one level (``'A'``, ``'B'`` or ``'C'``)."""
        lv = np.asarray(self.table["level"])
        return [int(i) for i in np.flatnonzero(lv == level)]


def _rank(values: FloatArray) -> IntArray:
    order: IntArray = np.argsort(values, kind="stable")
    return order


def extract_conflicts(
    traj: Trajectories,
    n_collision: int = 8,
    n_crossing: int = 4,
    n_none: int = 2,
    half_window: float = 5.0,
    horizon: float = 10.0,
    max_distance: float = 30.0,
    name: str = "local",
    site: str = "",
    period: str = "",
    drop_overlap: bool = True,
) -> ConflictBank:
    """Pick the most severe encounters of ``traj`` and cut a window around each.

    Encounters (:func:`pyssms.process.encounters`) are ranked in three groups:

    * ``A``: on a collision course at some moment, by the smallest TTC reached (window centred
      there);
    * ``B``: never on a collision course but with a finite Time Advantage, by the smallest TAdv;
    * ``C``: the future paths never overlap, by the smallest centre distance.

    ``drop_overlap`` removes pairs whose bodies overlap at some moment (TTC = 0), which in raw
    video trajectories almost always means a measurement error, not a collision. The windows are
    shifted so that the centre of the two road users at the central moment is the origin
    (indicators do not depend on a translation).

    Args:
        traj: Trajectories (several road users over time, SI units).
        n_collision: Number of windows of group ``A``.
        n_crossing: Number of windows of group ``B``.
        n_none: Number of windows of group ``C``.
        half_window: Seconds kept on each side of the central moment.
        horizon: Prediction horizon of the indicators (s).
        max_distance: Candidate-pair distance (m), see :func:`pyssms.process.candidate_pairs`.
        name: Name given to the bank.
        site: Text stored in the table (where the data came from).
        period: Text stored in the table (which recording).
        drop_overlap: Skip pairs with overlapping bodies.

    Returns:
        A :class:`ConflictBank`; empty groups simply contribute no windows.
    """
    pairs = process.candidate_pairs(traj, max_distance=max_distance, horizon=horizon)
    # keep only a score per pair (batches bound the memory), then recompute the chosen pairs
    scored: dict[str, list[tuple[float, int, int, float]]] = {"A": [], "B": [], "C": []}
    for s0 in range(0, len(pairs), _BATCH):
        for e in process.encounters(traj, horizon=horizon, pairs=pairs[s0 : s0 + _BATCH]):
            finite = np.isfinite(e.ttc)
            if drop_overlap and finite.any() and float(np.nanmin(e.ttc)) <= 0.0:
                continue
            if (e.state == "A").any():
                k = int(np.nanargmin(np.where(e.state == "A", e.ttc, np.inf)))
                scored["A"].append((float(e.ttc[k]), e.a, e.b, float(e.t[k])))
            elif np.isfinite(e.tadv).any():
                k = int(np.nanargmin(e.tadv))
                scored["B"].append((float(e.tadv[k]), e.a, e.b, float(e.t[k])))
            else:
                k = int(np.argmin(e.distance))
                scored["C"].append((float(e.distance[k]), e.a, e.b, float(e.t[k])))
    chosen: list[tuple[str, str, int, int, float]] = []
    for lv, n, rule in (
        ("A", n_collision, "smallest TTC"),
        ("B", n_crossing, "smallest Time Advantage"),
        ("C", n_none, "smallest distance"),
    ):
        pool = scored[lv]
        for j in _rank(np.array([p[0] for p in pool]))[:n]:
            chosen.append((lv, rule, pool[j][1], pool[j][2], pool[j][3]))
    enc = process.encounters(traj, horizon=horizon, pairs=[(c[2], c[3]) for c in chosen])
    by_pair = {(e.a, e.b): e for e in enc}
    picks: list[tuple[str, str, int, int]] = []
    enc_sel: list[process.Encounter] = []
    for lv, rule, a_id, b_id, tc in chosen:
        e = by_pair[(a_id, b_id)]
        picks.append((lv, rule, len(enc_sel), int(np.flatnonzero(e.t == tc)[0])))
        enc_sel.append(e)
    enc = enc_sel
    return _cut(traj, enc, picks, half_window, name, site, period)


def _cut(
    traj: Trajectories,
    enc: list[process.Encounter],
    picks: list[tuple[str, str, int, int]],
    half_window: float,
    name: str,
    site: str,
    period: str,
) -> ConflictBank:
    cols: dict[str, list[FloatArray]] = {c: [] for c in (*_COLS, "uid")}
    kinds: list[Any] = []
    starts = [0]
    tab: dict[str, list[Any]] = {k: [] for k in (*_TABLE_NUM, *_TABLE_INT, *_TABLE_STR)}
    for w, (lv, rule, i, k) in enumerate(picks):
        e = enc[i]
        tc = float(e.t[k])
        sel = (e.t >= tc - half_window) & (e.t <= tc + half_window)
        times = e.t[sel]
        origin = np.zeros(2)
        for who, uid in enumerate((e.a, e.b)):
            tr = traj.track(uid)
            m = np.isin(tr.t, times)
            if who == 0:
                c = np.flatnonzero(tr.t == tc)[0]
                origin[0], origin[1] = tr.x[c], tr.y[c]
            for c_name in _COLS:
                arr = getattr(tr, c_name)[m]
                if c_name == "x":
                    arr = arr - origin[0]
                elif c_name == "y":
                    arr = arr - origin[1]
                elif c_name == "t":
                    arr = arr - times[0]
                cols[c_name].append(arr.astype(float))
            cols["uid"].append(np.full(int(m.sum()), 2 * w + who, dtype=float))
            kinds.append(tr.kind[m])
        starts.append(starts[-1] + 2 * int(sel.sum()))
        finite = np.isfinite(e.ttc)
        tab["level"].append(lv)
        tab["selection"].append(rule)
        tab["min_ttc"].append(float(np.nanmin(e.ttc)) if finite.any() else float("nan"))
        tab["min_tadv"].append(e.min_tadv())
        tab["min_distance"].append(e.min_distance())
        tab["t_centre"].append(tc)
        tab["id_a"].append(e.a)
        tab["id_b"].append(e.b)
        tab["site"].append(site)
        tab["period"].append(period)
    if not picks:
        empty = np.zeros(0)
        rows = Trajectories(
            t=empty, uid=empty.astype(np.int64), x=empty, y=empty, heading=empty, vx=empty,
            vy=empty, length=empty, width=empty, kind=np.zeros(0, dtype=str),
        )  # fmt: skip
    else:
        cat = {c: np.concatenate(v) for c, v in cols.items()}
        rows = Trajectories(
            t=cat["t"], uid=cat["uid"].astype(np.int64), x=cat["x"], y=cat["y"],
            heading=cat["heading"], vx=cat["vx"], vy=cat["vy"], length=cat["length"],
            width=cat["width"], kind=np.concatenate(kinds).astype(str),
        )  # fmt: skip
    table: dict[str, Any] = {key: np.array(tab[key]) for key in tab}
    for key in _TABLE_STR:
        table[key] = np.array(tab[key], dtype=str)
    return ConflictBank(
        name=name, table=table, rows=rows, row_start=np.array(starts, dtype=np.int64),
        info=f"{name}: {len(picks)} windows of +-{half_window:g} s; extracted by "
        "pyssms.bank.extract_conflicts",
    )  # fmt: skip


def concat_banks(banks: list[ConflictBank], name: str, info: str = "") -> ConflictBank:
    """Stack several banks into one (window numbers and ``uid`` are renumbered)."""
    if not banks:
        raise ValueError("no banks to join")
    rows_cols: dict[str, list[Any]] = {c: [] for c in (*_COLS, "uid", "kind")}
    starts = [0]
    shift = 0
    for b in banks:
        for c in _COLS:
            rows_cols[c].append(getattr(b.rows, c))
        rows_cols["uid"].append(b.rows.uid + 2 * shift)
        rows_cols["kind"].append(b.rows.kind)
        starts.extend((b.row_start[1:] + starts[-1]).tolist())
        shift += len(b)
    r = {c: np.concatenate(v) for c, v in rows_cols.items()}
    rows = Trajectories(
        t=r["t"], uid=r["uid"], x=r["x"], y=r["y"], heading=r["heading"], vx=r["vx"],
        vy=r["vy"], length=r["length"], width=r["width"], kind=r["kind"], source=name,
    )  # fmt: skip
    table = {k: np.concatenate([np.asarray(b.table[k]) for b in banks]) for k in banks[0].table}
    return ConflictBank(
        name=name, table=table, rows=rows, row_start=np.array(starts, dtype=np.int64),
        info=info or f"{name}: {shift} windows",
    )  # fmt: skip


def save_bank(bank: ConflictBank, path: str | Path, info: str | None = None) -> Path:
    """Write a bank to a compressed ``.npz`` file (no pickles)."""
    r = bank.rows
    out = {f"row_{c}": getattr(r, c) for c in _COLS}
    out["row_uid"] = r.uid
    out["row_kind"] = r.kind
    out["row_start"] = bank.row_start
    out.update({f"tab_{k}": np.asarray(v) for k, v in bank.table.items()})
    out["name"] = np.array(bank.name)
    out["info"] = np.array(info if info is not None else bank.info)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, **out)
    return p


def _read_bank(z: Any) -> ConflictBank:
    rows = Trajectories(
        t=z["row_t"], uid=z["row_uid"], x=z["row_x"], y=z["row_y"], heading=z["row_heading"],
        vx=z["row_vx"], vy=z["row_vy"], length=z["row_length"], width=z["row_width"],
        kind=z["row_kind"], source=str(z["name"]),
    )  # fmt: skip
    table = {k[4:]: z[k] for k in z.files if k.startswith("tab_")}
    return ConflictBank(
        name=str(z["name"]), table=table, rows=rows, row_start=z["row_start"], info=str(z["info"])
    )


def _data_dir() -> Any:
    return resources.files("pyssms").joinpath("data")


def available_banks() -> list[str]:
    """Names of the banks shipped with the package."""
    names = []
    for f in _data_dir().iterdir():
        n = f.name
        if n.startswith("conflict_bank_") and n.endswith(".npz"):
            names.append(n[len("conflict_bank_") : -len(".npz")])
    return sorted(names)


def load_conflict_bank(name: str = "ngsim") -> ConflictBank:
    """Load a bank shipped with the package (see the module docstring for what it is).

    Args:
        name: One of :func:`available_banks` (currently ``"ngsim"``).

    Raises:
        KeyError: if ``name`` is not available. Banks of the LevelX data sets do not exist because
            those data may not be redistributed.
    """
    avail = available_banks()
    if name not in avail:
        raise KeyError(f"no bank {name!r}; available: {avail}")
    f = _data_dir().joinpath(f"conflict_bank_{name}.npz")
    with f.open("rb") as fh, np.load(fh, allow_pickle=False) as z:
        return _read_bank(z)


def load_summary() -> dict[str, Any]:
    """Aggregated counts and prediction-error scales of the five German drone data sets.

    Read from ``pyssms/data/summary_levelx.json``: for each data set and location the number of
    candidate pairs per hierarchy level and the RMS prediction-error scales of unhindered
    vehicles. **Counts only; no trajectory, no per-road-user value.** The counts depend on the
    candidate-pair rule (``docs/diamond_*.md``), and they describe the recordings that were
    processed, not the roads in general.
    """
    f = _data_dir().joinpath("summary_levelx.json")
    out: dict[str, Any] = json.loads(f.read_text(encoding="utf-8"))
    return out
