"""Honest validation against published results: targets, status rule, comparison table.

A *target* is one published number. Each target carries the status the package is expected to
produce (``reproduced``, ``estimate_only`` or ``not_reproduced``) and a note explaining every gap.
Tests assert ``status == expected`` for every target, so a gap can neither be hidden nor silently
open up. Gaps are never "fixed" by tuning the package to the number; they are documented.

Pattern distilled from the pynhts project (2026-10): see ~/.claude/skills/package-validate.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml

STATUSES = ("reproduced", "estimate_only", "not_reproduced")


@dataclass(frozen=True)
class Target:
    """One published figure to reproduce."""

    id: str
    table: str
    label: str
    scale: float
    decimals: int
    published: float
    moe: float | None
    compute: str
    expected: str
    note: str = ""

    @property
    def estimate_tolerance(self) -> float:
        """Half a unit in the last printed digit."""
        return 0.5 * 10.0**-self.decimals + 1e-9


@dataclass(frozen=True)
class Spec:
    """A packaged set of targets from one publication."""

    source: str
    title: str
    citation: str
    targets: tuple[Target, ...]


def load_spec(name: str, package: str = "pyssms") -> Spec:
    """Load ``validation/data/<name>.yaml`` shipped inside ``package``."""
    ref = resources.files(package) / "validation" / "data" / f"{name}.yaml"
    if not ref.is_file():
        raise ValueError(f"unknown validation set {name!r}")
    raw: dict[str, Any] = yaml.safe_load(ref.read_text(encoding="utf-8"))
    targets = tuple(
        Target(
            id=t["id"],
            table=str(t["table"]),
            label=t["label"],
            scale=float(t["scale"]),
            decimals=int(t["decimals"]),
            published=float(t["published"]),
            moe=None if t["moe"] is None else float(t["moe"]),
            compute=t["compute"],
            expected=t["expected"],
            note=str(t.get("note", "")).strip(),
        )
        for t in raw["targets"]
    )
    for t in targets:
        if t.expected not in STATUSES:
            raise ValueError(f"{t.id}: invalid expected status {t.expected!r}")
        if t.expected != "reproduced" and not t.note:
            raise ValueError(f"{t.id}: every known gap needs a note")
    return Spec(raw["source"], raw["title"], raw["citation"], targets)


def classify(target: Target, estimate: float, moe: float | None) -> str:
    """Status rule: estimate within rounding; margin of error within rounding or 0.1 percent."""
    if abs(estimate - target.published) > target.estimate_tolerance:
        return "not_reproduced"
    if target.moe is None or moe is None:
        return "reproduced"
    tol = max(target.estimate_tolerance, 0.001 * target.moe)
    return "reproduced" if abs(moe - target.moe) <= tol else "estimate_only"


def run(
    spec: Spec, compute: dict[str, Callable[[Any], tuple[float, float | None]]], context: Any
) -> list[dict[str, Any]]:
    """Compute every target and return one comparison row per target."""
    rows = []
    for t in spec.targets:
        est, moe = compute[t.compute](context)
        est, moe = est / t.scale, None if moe is None else moe / t.scale
        rows.append(
            {
                "id": t.id,
                "table": t.table,
                "label": t.label,
                "published": t.published,
                "published_moe": t.moe,
                "decimals": t.decimals,
                "estimate": est,
                "moe": moe,
                "status": classify(t, est, moe),
                "expected": t.expected,
                "note": t.note,
            }
        )
    return rows


def to_markdown(rows: list[dict[str, Any]]) -> str:
    """Render comparison rows as a GitHub-flavoured Markdown table."""
    head = "| Table | Quantity | Published | Estimate | Status |\n|---|---|---:|---:|---|\n"
    body = [
        f"| {r['table']} | {r['label']} | {r['published']:,.{r['decimals']}f} "
        f"| {r['estimate']:,.{r['decimals']}f} | {r['status']} |"
        for r in rows
    ]
    return head + "\n".join(body) + "\n"
