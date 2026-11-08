"""Build the English SoftwareX manuscript from the official Elsevier OSP template (elsarticle) and compile it.

    python paper_softwarex/build_en.py [--no-pdf]

Output: latex/manuscript_softwarex.tex, latex/manuscript_softwarex.pdf, manuscript_softwarex.pdf (copy),
        manuscript_softwarex_latex_sources.zip (what the submission system asks for with a LaTeX manuscript).
Checks (stop on failure): parallel text check, citation numbering by first appearance, uncited references, figures cited in order,
        word limits (4,000 words: abstract + text + captions + code; abstract <= 250), every number token resolved.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import check_parallel
import common as K
import content as C

HERE = Path(__file__).resolve().parent
KIT = Path.home() / ".claude" / "research-kit" / "journals" / "softwarex"
OUT = HERE / "latex"
(OUT / "figures").mkdir(parents=True, exist_ok=True)
TEMPLATE = (KIT / "softwarex-osp-template.tex").read_text(encoding="utf8")
L = C.EN
if check_parallel.main():
    raise SystemExit("the English and Persian texts are not parallel")
WORDS = {"abstract": 0, "text": 0, "other": 0}
FIGN = K.figure_numbers(L)
TABN = K.table_numbers(L)

UNI = {"\u03c4": r"$\tau$", "\u03c1": r"$\rho$", "\u00b5": r"$\mu$", "\u2081": r"$_1$", "\u2082": r"$_2$", "\u00b2": r"$^2$",
       "\u2076": r"$^6$", "\u2212": r"$-$", "\u00d7": r"$\times$", "\u2264": r"$\leq$", "\u2265": r"$\geq$", "\u25b2": r"$\blacktriangle$", "\u25bc": r"$\blacktriangledown$"}


def esc(s: str) -> str:
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}")):
        s = s.replace(a, b)
    s = s.replace(" %", chr(1)).replace("%", chr(92) + "%").replace(chr(1), chr(92) + "," + chr(92) + "%")
    s = s.replace("^", r"\^{}").replace("~", r"\textasciitilde{}")
    # ISO dates keep their hyphens and nothing after "https://" is touched (the DOI links of the references were broken by the rule)
    s = re.sub(r"(\d{4})-(\d{2})-(\d{2})", lambda m: m.group(1) + chr(2) + m.group(2) + chr(2) + m.group(3), s)
    head, sep, tail = s.partition("https://")
    s = re.sub(r"(?<=\d)-(?=\d)", "--", head) + sep + tail
    s = re.sub(r'"([^"]*)"', r"``\1''", s)
    for a, b in UNI.items():
        s = s.replace(a, b)
    return s.replace(chr(2), "-")


def tex(text: str, count: str | None = None) -> str:
    text = K.fill(text)
    if count:
        WORDS[count] += len(re.findall(r"\S+", re.sub(r"\{(?:fig|sec|tab):\w+\}", "1", K.CITE.sub("", text))))
    holders: list[str] = []

    def hold(latex: str) -> str:
        holders.append(latex)
        return f"\x00{len(holders) - 1}\x00"

    text = K.CITE.sub(lambda m: hold(r"\cite{" + ",".join(m.group(1).replace("@", "").split(",")) + "}"), text)
    text = K.FIGREF.sub(lambda m: hold(r"Fig.~\ref{fig:" + m.group(1) + "}"), text)
    text = K.SECREF.sub(lambda m: hold(r"Section~\ref{sec:" + m.group(1) + "}"), text)
    text = K.TABREF.sub(lambda m: hold(r"Table~\ref{tab:" + m.group(1) + "}"), text)
    out = esc(text)
    return re.sub(r"\x00(\d+)\x00", lambda m: holders[int(m.group(1))], out)


def blocks(items: list, count: str = "text") -> str:
    out: list[str] = []
    for b in items:
        kind = b[0]
        if kind == "p":
            out.append(tex(b[1], count) + "\n")
        elif kind == "h":
            WORDS[count] += len(b[1].split())
            out.append(r"\textbf{" + esc(b[1]) + "}\n")
        elif kind == "code":
            WORDS[count] += len(re.findall(r"\S+", b[1]))
            out.append("\\begin{footnotesize}\\begin{verbatim}\n" + b[1] + "\n\\end{verbatim}\\end{footnotesize}\n")
        elif kind == "table":
            _, key, cap, header, trows = b
            WORDS[count] += sum(len(c.split()) for r in [header] + trows for c in r) + len(cap.split())
            rows_tex = " \\\\\n".join(" & ".join(esc(c) for c in r) for r in trows)
            head_tex = " & ".join("\\textbf{" + esc(c) + "}" for c in header)
            out.append("\\begin{table}[!ht]\n\\centering\\small\n\\caption{" + tex(cap) + "}\\label{tab:" + key + "}\n"
                       "\\begin{tabular}{p{1.4cm}p{5.2cm}p{3.5cm}p{1.1cm}p{2.5cm}}\n\\hline\n"
                       + head_tex + " \\\\\n\\hline\n" + rows_tex + " \\\\\n\\hline\n\\end{tabular}\n\\end{table}\n")
        elif kind == "fig":
            _, key, fname, cap = b
            shutil.copy(HERE / "figures" / f"{fname}.pdf", OUT / "figures" / f"{fname}.pdf")
            out.append("\\begin{figure}[!htbp]\n\\centering\n"
                       f"\\includegraphics[width=\\textwidth]{{figures/{fname}.pdf}}\n"
                       f"\\caption{{{tex(cap, count)}}}\n\\label{{fig:{key}}}\n\\end{{figure}}\n")
    return "\n".join(out)


head, rest = TEMPLATE.split("\\begin{document}", 1)
head = head.replace("\\usepackage{hyperref}", "\\usepackage{hyperref}\n\\usepackage{url}")
head = head.replace("\\setlength{\\parindent}{0pt}", "\\setlength{\\parindent}{0pt}\n\\setlength{\\parskip}{4pt}")
authors = []
for a in C.AUTHORS:
    cor = r"\corref{cor1}" if a["corresponding"] else ""
    ead = "\n\\ead{" + a["email"].replace("_", r"\_") + "}" if a["email"] else ""
    authors.append(f"\\author[aff{a['aff']}]{{{esc(a['name'])}{cor}}}{ead}")
affs = "\n".join(f"\\address[aff{k}]{{{esc(v)}}}" for k, v in C.AFFILS.items())
front = ("\\begin{document}\n\\renewcommand{\\labelenumii}{\\arabic{enumi}.\\arabic{enumii}}\n\n\\begin{frontmatter}\n\n"
         f"\\title{{{esc(L['title'])}}}\n\n" + "\n".join(authors) + "\n\\cortext[cor1]{Corresponding author}\n\n" + affs + "\n\n"
         "\\begin{abstract}\n" + tex(L["abstract"], "abstract") + "\n\\end{abstract}\n\n"
         "\\begin{keyword}\n" + " \\sep ".join(esc(k) for k in L["keywords"]) + "\n\\end{keyword}\n\n\\end{frontmatter}\n\n")

meta = dict(L["meta"])
rows = {"C1": esc(meta["C1"]), "C2": r"\url{" + meta["C2"] + "}", "C3": esc(meta["C3"]), "C4": esc(meta["C4"]), "C5": esc(meta["C5"]),
        "C6": esc(meta["C6"]), "C7": r"\url{" + meta["C7"] + "}", "C8": esc(meta["C8"])}
names = {"C1": "Current code version", "C2": "Permanent GitHub link to code/repository used for this code version", "C3": "Legal Code License",
         "C4": "Code versioning system used", "C5": "Software code languages, tools, and services used",
         "C6": r"Compilation requirements, operating environments \& dependencies", "C7": "If available Link to developer documentation/manual",
         "C8": "Support email for questions"}
table = ("\\section*{Required Metadata}\n\n\\section*{Current code version}\n\n"
         "\\begin{table}[!h]\n\\begin{tabular}{|l|p{6.5cm}|p{6.5cm}|}\n\\hline\n"
         "\\textbf{Nr.} & \\textbf{Code metadata description} & \\textbf{Please fill in this column} \\\\\n\\hline\n"
         + "".join(f"{k} & {names[k]} & {rows[k]} \\\\\n\\hline\n" for k in rows)
         + "\\end{tabular}\n\\caption{Code metadata (mandatory)}\n\\label{tab:meta}\n\\end{table}\n\n")

S = L["sections"]
arch = S["architecture"]
split = next(i for i, b in enumerate(arch) if b[0] == "h")
usage = next(i for i, b in enumerate(arch) if b[0] == "h" and b[1].startswith("Usage"))
main = ("\\textbf{Main text}\\\\\n\n\\begin{enumerate}\n\n"
        "\\item \\textbf{Motivation and significance}\\label{sec:motivation}\\\\\n\n" + blocks(S["motivation"]) + "\n"
        "\\item \\textbf{Software description}\\label{sec:architecture}\\\\\n\n\\begin{enumerate}\n"
        "\\item \\textbf{Software architecture.} " + blocks(arch[:split]) + "\n"
        "\\item \\textbf{Software functionalities.} " + blocks(arch[split + 1:]) + "\\end{enumerate}\n\n"
        "\\item \\textbf{Illustrative examples}\\label{sec:examples}\\\\\n\n" + blocks(S["examples"]) + "\n"
        "\\item \\textbf{Impact}\\label{sec:impact}\\\\\n\n" + blocks(S["impact"]) + "\n"
        "\\item \\textbf{Conclusions}\\label{sec:conclusions}\\\\\n\n" + blocks(S["conclusions"]) + "\n"
        "\\end{enumerate}\n\n")

decl = [("Acknowledgements", L["ack"]),
        ("Declaration of generative AI and AI-assisted technologies in the manuscript preparation process", L["ai"]),
        ("CRediT authorship contribution statement", L["credit"]), ("Funding", L["funding"]),
        ("Declaration of competing interest", L["competing"]), ("Data availability", L["data"])]
tail = "".join(f"\\section*{{{esc(h)}}}\n\n{tex(t, 'other')}\n\n" for h, t in decl)
bib = "\\begin{thebibliography}{00}\n\n" + "\n\n".join(f"\\bibitem{{{k}}} {esc(C.REFS[k])}".replace(r"\_", "_") for k in K.ORDER) + "\n\n\\end{thebibliography}\n\n"
# URLs inside the references: make them breakable and keep the underscore unescaped
bib = re.sub(r"(https?://[^\s]+?)(\.?)(?=\s|$)", lambda m: r"\url{" + m.group(1).replace(r"\%", "%").replace(r"\{", "{").replace(r"\}", "}") + "}" + m.group(2), bib)
final = "\\section*{Current executable software version}\n\n" + esc(K.fill(L["exec_version"])).replace("(" + esc(C.REPO) + ")", "(\\url{" + C.REPO + "})") + "\n\n\\end{document}\n"
doc = head + front + table + main + tail + bib + final
(OUT / "manuscript_softwarex.tex").write_text(doc, encoding="utf8")

if not set(K.ORDER) == set(C.REFS):
    raise SystemExit("reference list and citations differ")
total = WORDS["abstract"] + WORDS["text"]
print("words:", WORDS, "| counted against the 4,000-word limit:", total)
print("figures:", list(FIGN), "| citations:", len(K.ORDER), "| TODO tags in the text:", len(re.findall(r"\[\[AUTHOR-", doc)))
if total > 4000:
    raise SystemExit("over the journal's 4,000-word limit: cut text, do not squeeze the format")
if WORDS["abstract"] > 250:
    raise SystemExit("abstract over 250 words")
hl = [K.fill(h) for h in L["highlights"]]
bad = [h for h in hl if len(h) > 85]
if bad:
    raise SystemExit(f"highlights over 85 characters: {bad}")
(HERE / "highlights.txt").write_text("\n".join(hl) + "\n", encoding="utf8")

if "--no-pdf" not in sys.argv:
    exe = shutil.which("pdflatex")
    if not exe:
        raise SystemExit("pdflatex not found")
    for _ in range(3):
        r = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", "manuscript_softwarex.tex"], cwd=OUT, capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-3000:])
            raise SystemExit("pdflatex failed")
    log = (OUT / "manuscript_softwarex.log").read_text(encoding="utf8", errors="replace")
    print("LaTeX warnings:", [ln for ln in log.splitlines() if "Warning" in ln and "float" not in ln.lower()][:8])
    shutil.copy(OUT / "manuscript_softwarex.pdf", HERE / "manuscript_softwarex.pdf")
with zipfile.ZipFile(HERE / "manuscript_softwarex_latex_sources.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write(OUT / "manuscript_softwarex.tex", "manuscript_softwarex.tex")
    for f in sorted((OUT / "figures").glob("*.pdf")):
        z.write(f, f"figures/{f.name}")
print("built", HERE / "manuscript_softwarex.pdf")
