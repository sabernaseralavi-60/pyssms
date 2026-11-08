"""Shared helpers of the two builders: number tokens, citation numbering, figure numbering, checks on the parallel texts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import content as C

HERE = Path(__file__).resolve().parent
RES = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
RES["fig2"] = json.loads((HERE / "fig_numbers.json").read_text(encoding="utf-8"))
_lr = HERE / "listing_result.json"
if _lr.exists():
    _l = json.loads(_lr.read_text(encoding="utf-8"))
    RES["listing"] = {"minutes": _l["seconds"] / 60.0, "n_enc": _l["n_enc"]}

TOKEN = re.compile(r"\{\{([\w./+-]+?)(?::([^}|]*))?\}\}")
CITE = re.compile(r"\[@([\w@,]+)\]")
FIGREF = re.compile(r"\{fig:(\w+)\}")
SECREF = re.compile(r"\{sec:(\w+)\}")
TABREF = re.compile(r"\{tab:(\w+)\}")
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
                               "01234567890123456789")


def lookup(path: str):
    cur = RES
    for part in path.split("/"):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def fill(text: str) -> str:
    """Replace ``{{path:fmt}}`` by the formatted number; stop if a token cannot be resolved."""

    def one(m: re.Match) -> str:
        try:
            v = lookup(m.group(1))
        except (KeyError, IndexError, ValueError) as err:
            raise SystemExit(f"unresolved number token {m.group(0)}: {err!r}")
        return format(v, m.group(2)) if m.group(2) else str(v)

    return TOKEN.sub(one, text)


def blocks_of(lang: dict):
    for key in ("motivation", "architecture", "examples", "impact", "conclusions"):
        yield key, lang["sections"][key]


def cite_order() -> list[str]:
    """Citation keys in order of first appearance in the document (the English text; the Persian one is parallel)."""
    order: list[str] = []

    def scan(t: str) -> None:
        for m in CITE.finditer(t):
            for k in m.group(1).replace("@", "").split(","):
                if k not in order:
                    order.append(k)

    scan(C.EN["abstract"])
    for _, bl in blocks_of(C.EN):
        for b in bl:
            if b[0] in ("p", "h"):
                scan(b[1])
            elif b[0] == "fig":
                scan(b[3])
            elif b[0] == "table":
                scan(b[2])
    for k in ("ack", "ai", "credit", "funding", "competing", "data"):
        scan(C.EN[k])
    return order


ORDER = cite_order()
NUM = {k: i + 1 for i, k in enumerate(ORDER)}


def compress(nums: list[int]) -> str:
    """[1,2,3,5] -> '1-3,5' (numbers sorted)."""
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"{nums[i]}-{nums[j]}" if j - i >= 2 else ",".join(str(n) for n in nums[i:j + 1]))
        i = j + 1
    return ",".join(out)


def figure_numbers(lang: dict) -> dict[str, int]:
    keys = [b[1] for _, bl in blocks_of(lang) for b in bl if b[0] == "fig"]
    return {k: i + 1 for i, k in enumerate(keys)}


def table_numbers(lang: dict) -> dict[str, int]:
    """Table 1 is the code-metadata table of the journal; the tables of the text follow."""
    keys = [b[1] for _, bl in blocks_of(lang) for b in bl if b[0] == "table"]
    return {k: i + 2 for i, k in enumerate(keys)}


def figure_order_of_citation(lang: dict) -> list[str]:
    """Figure keys in order of their first textual reference (must equal the order of the figures themselves)."""
    seen: list[str] = []
    for _, bl in blocks_of(lang):
        for b in bl:
            if b[0] in ("p", "h"):
                for m in FIGREF.finditer(b[1]):
                    if m.group(1) not in seen:
                        seen.append(m.group(1))
    return seen


def tokens_of(text: str) -> list[str]:
    return [m.group(0) for m in TOKEN.finditer(text)]


def all_texts(lang: dict):
    yield "abstract", lang["abstract"]
    for sec, bl in blocks_of(lang):
        for i, b in enumerate(bl):
            if b[0] == "fig":
                yield f"{sec}/{i}/caption", b[3]
            elif b[0] == "table":
                yield f"{sec}/{i}/caption", b[2]
            elif b[0] in ("p", "h"):
                yield f"{sec}/{i}", b[1]
    for k in ("ack", "ai", "credit", "funding", "competing", "data"):
        yield k, lang[k]
    for i, h in enumerate(lang["highlights"]):
        yield f"highlight/{i}", h


def digits_latin(s: str) -> str:
    return s.translate(PERSIAN_DIGITS).replace("٫", ".").replace("٬", ",")
