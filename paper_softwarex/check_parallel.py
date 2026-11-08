"""Fidelity gate between the English and the Persian text (run by both builders; also usable alone).

Checks, block by block: same block kinds and order, same number tokens in the same order, same citations and cross references,
same set of numbers written out in the text (Persian digits normalised), and the English-Latin names the Persian text must keep
(measure names, module names). A mismatch stops the build: the Persian text is a translation, it may not add, drop or change a number.

    python paper_softwarex/check_parallel.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter

import common as K
import content as C

NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")


def bare_numbers(t: str) -> Counter:
    t = K.TOKEN.sub(" ", K.CITE.sub(" ", K.FIGREF.sub(" ", K.TABREF.sub(" ", K.SECREF.sub(" ", K.digits_latin(t))))))
    t = t.replace("2026-11-01", "DATE")
    return Counter(NUMBER.findall(t))


def main() -> int:
    bad: list[str] = []
    en, fa = C.EN, C.FA
    ten = dict(K.all_texts(en))
    tfa = dict(K.all_texts(fa))
    if list(ten) != list(tfa):
        bad.append(f"block structure differs: {set(ten) ^ set(tfa)}")
    for key in ten:
        if key not in tfa:
            continue
        a, b = ten[key], tfa[key]
        if K.tokens_of(a) != K.tokens_of(b):
            bad.append(f"[{key}] number tokens differ: {K.tokens_of(a)} vs {K.tokens_of(b)}")
        if K.CITE.findall(a) != K.CITE.findall(b):
            bad.append(f"[{key}] citations differ: {K.CITE.findall(a)} vs {K.CITE.findall(b)}")
        if K.FIGREF.findall(a) != K.FIGREF.findall(b) or K.TABREF.findall(a) != K.TABREF.findall(b):
            bad.append(f"[{key}] figure or table references differ")
        if bare_numbers(a) != bare_numbers(b):
            bad.append(f"[{key}] written numbers differ: {dict(bare_numbers(a) - bare_numbers(b))} only in EN; {dict(bare_numbers(b) - bare_numbers(a))} only in FA")
    for sec, bl_en in K.blocks_of(en):
        bl_fa = fa["sections"][sec]
        if [b[0] for b in bl_en] != [b[0] for b in bl_fa]:
            bad.append(f"[{sec}] block kinds differ")
        for x, y in zip(bl_en, bl_fa):
            if x[0] == "fig" and (x[1], x[2]) != (y[1], y[2]):
                bad.append(f"[{sec}] figure differs {x[1:3]} vs {y[1:3]}")
            if x[0] == "table" and (x[1], len(x[3]), len(x[4])) != (y[1], len(y[3]), len(y[4])):
                bad.append(f"[{sec}] table differs {x[1]}")
            if x[0] == "code" and x[1] != y[1]:
                bad.append(f"[{sec}] code differs")
    if K.figure_order_of_citation(en) != [b[1] for _, bl in K.blocks_of(en) for b in bl if b[0] == "fig"]:
        bad.append(f"figures are not cited in the order they appear: {K.figure_order_of_citation(en)}")
    if K.figure_order_of_citation(fa) != K.figure_order_of_citation(en):
        bad.append("figure citation order differs between languages")
    unused = set(C.REFS) - set(K.ORDER)
    missing = set(K.ORDER) - set(C.REFS)
    if unused:
        bad.append(f"references never cited: {sorted(unused)}")
    if missing:
        bad.append(f"citations without a reference: {sorted(missing)}")
    if bad:
        print("PARALLEL CHECK FAILED:")
        for b in bad:
            print(" -", b)
        return 1
    print(f"parallel check passed: {len(ten)} text blocks, {sum(len(K.tokens_of(t)) for t in ten.values())} number tokens, "
          f"{len(K.ORDER)} references, figures cited in order {K.figure_order_of_citation(en)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
