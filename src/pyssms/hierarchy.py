"""Severity hierarchy ("diamond") of the encounters of a site or scenario.

Hyden (1987) and Svensson (1998) order traffic events from undisturbed passages through potential
and slight conflicts to serious conflicts and collisions; Laureshyn, Svensson and Hyden (2010) draw
the frequency of each level as the width of a pyramid. :func:`build_hierarchy` produces the data of
such a figure from the encounters of a recording:

* each encounter gets a **level**: ``A`` = on a collision course at some time stamp, split by the
  smallest TTC it reached (``a_edges``; a constant-velocity collision course 8 s ahead is a weak
  event, one 1 s ahead a strong one); then, for encounters never on a collision course, the bins of
  the smallest Time Advantage it reached (TAdv, the delay of one road user that would put them on
  a collision course; ``edges``, state B); and ``C`` = the future paths never overlap within the
  horizon;
* optionally a **severity class** from the (extended) closing speed at the moment of smallest TAdv.

Whether the counts bulge in the middle (a diamond) or taper (a pyramid) is a result for the data in
hand, not something this function imposes. The frequencies count *pairs* that came within
``max_distance`` of each other (:func:`pyssms.process.candidate_pairs`), so the base of the figure
depends on that radius; it is returned, not hidden.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from pyssms.geometry import FloatArray, IntArray
from pyssms.process import Encounter
from pyssms.severity import extended_closing_speed

__all__ = ["Hierarchy", "build_hierarchy", "closing_speed_at_minimum", "plot_hierarchy"]


@dataclass(frozen=True)
class Hierarchy:
    """Counts of encounters per level and severity class.

    Attributes:
        levels: Labels from the most to the least severe (``'A'``, bins, ``'C'``).
        severity_classes: Labels of the severity classes (a single ``'all'`` if none was given).
        counts: ``(len(levels), len(severity_classes))`` integer counts.
        level_index: Level of each encounter (index into ``levels``).
        edges: The TAdv bin edges (s) used.
    """

    levels: list[str]
    severity_classes: list[str]
    counts: IntArray
    level_index: IntArray
    edges: tuple[float, ...]

    @property
    def totals(self) -> IntArray:
        """Number of encounters per level."""
        out: IntArray = self.counts.sum(axis=1)
        return out

    def table(self) -> str:
        """Markdown table of the counts."""
        head = "| level | " + " | ".join(self.severity_classes) + " | total |"
        sep = "|---|" + "---|" * (len(self.severity_classes) + 1)
        rows = [
            f"| {lv} | " + " | ".join(str(int(c)) for c in row) + f" | {int(row.sum())} |"
            for lv, row in zip(self.levels, self.counts, strict=True)
        ]
        return "\n".join([head, sep, *rows])


def closing_speed_at_minimum(enc: Encounter, decel: float = 0.0) -> float:
    """(Extended) closing speed in km/h at the time stamp of smallest TAdv (ties: smallest T2).

    ``decel`` > 0 reduces both speeds by braking for T2 seconds as in the Extended Delta-V
    (:func:`pyssms.severity.extended_closing_speed`). NaN if TAdv is never defined.
    """
    if not np.isfinite(enc.tadv).any():
        return float("nan")
    key = np.where(np.isfinite(enc.tadv), enc.tadv, np.inf)
    best = key.min()
    cand = np.flatnonzero(key <= best + 1e-9)
    i = int(cand[np.argmin(np.where(np.isfinite(enc.t2[cand]), enc.t2[cand], np.inf))])
    t2 = float(enc.t2[i]) if np.isfinite(enc.t2[i]) else 0.0
    v = extended_closing_speed(enc.vel_a[i : i + 1], enc.vel_b[i : i + 1], t2, decel)
    return float(v[0])


def build_hierarchy(
    enc: Sequence[Encounter],
    edges: Sequence[float] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0),
    severity: Sequence[float] | FloatArray | None = None,
    severity_edges: Sequence[float] = (20.0, 40.0),
    a_edges: Sequence[float] = (1.5, 3.0, 6.0),
) -> Hierarchy:
    """Level counts of ``enc`` (see the module docstring).

    Args:
        enc: Encounters from :func:`pyssms.process.encounters`.
        edges: Increasing TAdv edges (s) separating the state-B levels; the last bin is open
            above the last edge up to the horizon.
        severity: One severity value per encounter (for example
            :func:`closing_speed_at_minimum`, km/h); ``None`` for no severity split.
        severity_edges: Edges between severity classes (same unit as ``severity``).
        a_edges: Increasing TTC edges (s) separating the state-A levels; the last bin is open
            above the last edge up to the horizon.

    Returns:
        :class:`Hierarchy`.
    """
    e = tuple(float(x) for x in edges)
    ae = tuple(float(x) for x in a_edges)
    levels = []
    lo = 0.0
    for hi in ae:
        levels.append(f"A: TTC {lo:g}-{hi:g} s")
        lo = hi
    levels.append(f"A: TTC > {lo:g} s")
    n_a = len(levels)
    lo = 0.0
    for hi in e:
        levels.append(f"B: TAdv {lo:g}-{hi:g} s")
        lo = hi
    levels += [f"B: TAdv > {lo:g} s", "C (no overlap)"]
    idx = np.empty(len(enc), dtype=np.int64)
    for k, x in enumerate(enc):
        if np.any(x.state == "A"):
            idx[k] = int(np.searchsorted(np.array(ae), x.min_ttc(), side="right"))
        elif np.any(x.state == "B"):
            idx[k] = n_a + int(np.searchsorted(np.array(e), x.min_tadv(), side="right"))
        else:
            idx[k] = len(levels) - 1
    if severity is None:
        classes = ["all"]
        cls: IntArray = np.zeros(len(enc), dtype=np.int64)
    else:
        se = tuple(float(x) for x in severity_edges)
        bounds = [-np.inf, *se, np.inf]
        classes = [f"{bounds[i]:g}..{bounds[i + 1]:g}" for i in range(len(bounds) - 1)]
        sev = np.asarray(severity, dtype=float)
        raw = np.searchsorted(np.array(se), np.where(np.isfinite(sev), sev, -np.inf), side="right")
        cls = np.where(np.isfinite(sev), raw, 0).astype(np.int64)
    counts = np.zeros((len(levels), len(classes)), dtype=np.int64)
    np.add.at(counts, (idx, cls), 1)
    return Hierarchy(
        levels=levels, severity_classes=classes, counts=counts, level_index=idx, edges=e
    )


def plot_hierarchy(h: Hierarchy, ax: Any = None, log: bool = False) -> Any:
    """Horizontal, mirrored bars: the width of each level is its count (a pyramid or a diamond).

    Needs matplotlib (not a dependency of the package: ``pip install matplotlib``). Returns
    the axes.
    """
    import matplotlib.pyplot as plt  # lazy: optional dependency

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    y = np.arange(len(h.levels))[::-1]
    tot = h.totals.astype(float)
    if log:
        tot = np.log10(np.maximum(tot, 1.0))
    ax.barh(y, tot, left=-tot / 2, color="#4C78A8", edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(h.levels)
    for yi, c in zip(y, h.totals, strict=True):
        ax.text(0, yi, f"{int(c)}", ha="center", va="center", color="white", fontsize=9)
    ax.set_xticks([])
    ax.set_xlabel("number of encounters" + (" (log10 width)" if log else " (width)"))
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    return ax
