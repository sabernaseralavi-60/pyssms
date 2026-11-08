"""Gate: the set of all numbers written in the body of the English manuscript equals the set in the Persian one.

Compares the generated sources (LaTeX of the English build, HTML of the Persian build; the PDFs are their prints). Figure
labels, citations numbers, figure numbers and code listings are excluded because they are not prose; the parallel check
(check_parallel.py) already guarantees the same tokens and citations. Any difference stops the release.

    python paper_softwarex/check_pdf_numbers.py
"""

from __future__ import annotations

import html
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")


def english() -> str:
    t = (HERE / "latex" / "manuscript_softwarex.tex").read_text(encoding="utf8")
    t = t[t.index("Motivation and significance}"):t.index("\\section*{Acknowledgements}")]
    t = re.sub(r"\\label\{[^}]*\}|\\ref\{[^}]*\}|\\includegraphics\[[^\]]*\]\{[^}]*\}|\\cite\{[^}]*\}", " ", t)
    t = re.sub(r"\\begin\{verbatim\}.*?\\end\{verbatim\}", " ", t, flags=re.S)
    t = re.sub(r"\\begin\{tabular\}\{(?:p\{[^}]*\})+\}", " ", t)  # column widths of the tables are layout, not prose
    t = re.sub(r"\\begin\{enumerate\}|\\end\{enumerate\}|\\item", " ", t)
    t = re.sub(r"\$[^$]*\$", " ", t)  # math-mode symbols (tau_1, m/s^2, 10^6) are single unicode characters in the Persian text
    return t.replace("\\,", "").replace("\\%", "%")


def persian() -> str:
    t = (HERE / "manuscript_softwarex_fa.html").read_text(encoding="utf8")
    t = t[t.index('<h2><span class="hn" dir="ltr">1.'):t.index("<h2>سپاسگزاری")]
    t = re.sub(r"<pre.*?</pre>", " ", t, flags=re.S)
    t = re.sub(r'<span class="cite".*?</span>', " ", t)
    t = re.sub(r'<a href="#(?:fig|tab)-\w+">.*?</a>', " ", t)
    t = re.sub(r"<img[^>]*>", " ", t)
    t = re.sub(r'<span class="hn"[^>]*>[^<]*</span>', " ", t)
    t = re.sub(r"<b>(?:شکل|جدول) .*?</b>", " ", t)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


def numbers(s: str) -> Counter:
    s = re.sub(r"(?<=\d)--(?=\d)", "-", s)
    s = re.sub(r"\\textbf\{\d+\.\d*\}", " ", s)
    return Counter(NUM.findall(s.replace("\u2212", "-")))


def main() -> int:
    a, b = numbers(english()), numbers(persian())
    only_en, only_fa = a - b, b - a
    print(f"numbers in the English body: {sum(a.values())}; in the Persian body: {sum(b.values())}")
    if only_en or only_fa:
        print("DIFFERENCE  English only:", dict(only_en), "| Persian only:", dict(only_fa))
        return 1
    print("number sets identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
