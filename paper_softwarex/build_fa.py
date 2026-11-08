"""Build the Persian version of the SoftwareX manuscript: right-to-left HTML (same text blocks, tokens and figures as the English
build) printed to PDF by headless Edge, in the clean style of the methods paper (paper/paper_fa.css).

    python paper_softwarex/build_fa.py

Output: manuscript_softwarex_fa.html, manuscript_softwarex_fa.pdf. Digits are Latin throughout (decision of 2026-11-07, so that the
fidelity check compares the same characters in both languages). Figures are the English-labelled figures of the English paper
(panel letters A, B, C are the same in the caption and in the figure); the architecture figure has no Persian twin yet.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

import check_parallel
import common as K
import content as C

HERE = Path(__file__).resolve().parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
L = C.FA
FIGN = K.figure_numbers(L)
TABN = K.table_numbers(L)

if check_parallel.main():
    raise SystemExit("the Persian text is not parallel to the English text")


def inline(text: str) -> str:
    text = K.digits_latin(K.fill(text))
    holders: list[str] = []

    def hold(h: str) -> str:
        holders.append(h)
        return f"\x00{len(holders) - 1}\x00"

    text = K.CITE.sub(lambda m: hold('<span class="cite" dir="ltr">[' + K.compress([K.NUM[k] for k in m.group(1).replace("@", "").split(",")]) + "]</span>"), text)
    text = K.FIGREF.sub(lambda m: hold(f'<a href="#fig-{m.group(1)}">شکل <span class="num">{FIGN[m.group(1)]}</span></a>'), text)
    text = K.TABREF.sub(lambda m: hold(f'<a href="#tab-{m.group(1)}">جدول <span class="num">{TABN[m.group(1)]}</span></a>'), text)
    out = html.escape(text, quote=False)
    out = re.sub(r"\b(?:TTC[123D]?|TAdv|T2|TG|DRAC|MDRAC|DCIA|PSD|MPSD|SDI|NGSIM|highD|exiD|inD|rounD|uniD|SSAM|SUMO|VISSIM|LevelX|pyssms|NumPy|PyYAML|matplotlib|Python|GitHub|Claude)\b",
                 lambda m: f'<span class="lat">{m.group(0)}</span>', out)
    out = re.sub(r"(?:docs|paper_softwarex)/[\w./-]+", lambda m: f'<span class="lat">{m.group(0)}</span>', out)
    out = re.sub(r"\(([A-Za-z][A-Za-z0-9_/. ,;:+-]*)\)", lambda m: f'<span class="lat">({m.group(1)})</span>', out)
    out = re.sub(r"(?<![\w\x00.])\d[\d.,]*\d|(?<![\w\x00.])\d", lambda m: f'<span class="num">{m.group(0)}</span>', out)
    return re.sub(r"\x00(\d+)\x00", lambda m: holders[int(m.group(1))], out)


def blocks(items: list, start_sub: int = 0) -> str:
    out: list[str] = []
    for b in items:
        kind = b[0]
        if kind == "p":
            out.append(f"<p>{inline(b[1])}</p>")
        elif kind == "h":
            out.append(f"<h3>{inline(b[1])}</h3>")
        elif kind == "code":
            out.append(f'<pre dir="ltr">{html.escape(b[1])}</pre>')
        elif kind == "table":
            _, key, cap, header, trows = b
            head = "".join(f"<th>{inline(c)}</th>" for c in header)
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in trows)
            out.append(f'<table class="tn" id="tab-{key}"><caption><b>جدول <span class="num">{TABN[key]}</span>.</b> {inline(cap)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')
        elif kind == "fig":
            _, key, fname, cap = b
            fname = fname + "_fa" if key == "arch" else fname
            out.append(f'<figure id="fig-{key}"><img src="figures/{fname}.png"><figcaption><b>شکل <span class="num">{FIGN[key]}</span>.</b> {inline(cap)}</figcaption></figure>')
    return "\n".join(out)


S = L["sections"]
arch = S["architecture"]
split = next(i for i, b in enumerate(arch) if b[0] == "h")
meta_names = {"C1": "نسخهٔ فعلی کد", "C2": "پیوند دائمی GitHub به کد این نسخه", "C3": "مجوز قانونی کد", "C4": "سامانهٔ مدیریت نسخه",
              "C5": "زبان‌ها، ابزارها و خدمات به‌کاررفته", "C6": "نیازهای ساخت، محیط‌های اجرا و وابستگی‌ها", "C7": "پیوند مستندات توسعه (در صورت وجود)",
              "C8": "رایانامهٔ پشتیبانی برای پرسش‌ها"}
meta_fa = {"C1": "v" + C.VERSION, "C2": C.ARCHIVE or C.REPO, "C3": "BSD 3-Clause License", "C4": "git", "C5": "Python 3; NumPy, PyYAML; optional: matplotlib",
           "C6": "Python 3.10 or newer; continuous integration on Linux and Windows with Python 3.10 and 3.13", "C7": C.REPO + "/tree/main/docs",
           "C8": C.SUPPORT_EMAIL}
meta_rows = "".join(f'<tr><td>{k}</td><td>{meta_names[k]}</td><td dir="ltr">{html.escape(v)}</td></tr>' for k, v in meta_fa.items())
refs = "".join(f"<li>{html.escape(C.REFS[k])}</li>" for k in K.ORDER)
decl = [("سپاسگزاری", L["ack"]), ("بیانیهٔ استفاده از هوش مصنوعی مولد و فناوری‌های یاری‌شده با هوش مصنوعی در تهیهٔ دست‌نوشته", L["ai"]),
        ("بیانیهٔ مشارکت نویسندگان (CRediT)", L["credit"]), ("تأمین مالی", L["funding"]), ("بیانیهٔ تعارض منافع", L["competing"]),
        ("در دسترس‌بودن داده و کد", L["data"])]
decl_html = "".join(f"<h2>{h}</h2><p>{inline(t)}</p>" for h, t in decl)
kw = "؛ ".join(L["keywords"])
doc = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>{html.escape(L['title'])}</title>
<link rel="stylesheet" href="softwarex_fa.css"></head><body>
<header><h1 class="title">{html.escape(L['title'])}</h1>
<p class="author">سید صابر ناصرعلوی<sup>*،۱</sup> و اکرم مظاهری<sup>۲</sup></p>
<p class="aff"><sup>۱</sup> گروه مهندسی عمران، دانشگاه شهید باهنر کرمان، کرمان، ایران<br><sup>۲</sup> گروه مهندسی عمران و محیط زیست، دانشگاه تربیت مدرس، تهران، ایران<br><span dir="ltr">* {C.SUPPORT_EMAIL}</span></p>
<p class="aff">دست‌نوشتهٔ نرم‌افزاری برای مجلهٔ SoftwareX (انتشارات Elsevier)؛ ترجمهٔ فارسی نسخهٔ انگلیسی؛ بسته: pyssms نسخهٔ <span dir="ltr">{C.VERSION}</span></p></header>
<section class="abstract"><h2>چکیده</h2><p>{inline(L['abstract'])}</p><p><b>واژه‌های کلیدی:</b> {html.escape(kw)}</p></section>
<h2>فرادادهٔ الزامی کد</h2>
<table class="meta"><thead><tr><th>ش.</th><th>شرح فرادادهٔ کد</th><th>مقدار</th></tr></thead><tbody>{meta_rows}</tbody></table>
<h2>۱. انگیزه و اهمیت</h2>
{blocks(S['motivation'])}
<h2>۲. توصیف نرم‌افزار</h2>
<h3 class="sub">۲.۱ معماری نرم‌افزار</h3>
{blocks(arch[:split])}
<h3 class="sub">۲.۲ قابلیت‌های نرم‌افزار</h3>
{blocks(arch[split:])}
<h2>۳. مثال‌های کاربردی</h2>
{blocks(S['examples'])}
<h2>۴. اثرگذاری</h2>
{blocks(S['impact'])}
<h2>۵. نتیجه‌گیری</h2>
{blocks(S['conclusions'])}
{decl_html}
<h2>مراجع</h2>
<ol class="refs" dir="ltr">{refs}</ol>
<h2>نسخهٔ اجرایی فعلی نرم‌افزار</h2>
<p dir="ltr">{html.escape(K.fill(L['exec_version']))}</p>
</body></html>"""
for num_old, num_new, word in (("۱.", "1.", "انگیزه"), ("۲.", "2.", "توصیف"), ("۳.", "3.", "مثال"), ("۴.", "4.", "اثر"), ("۵.", "5.", "نتیجه")):
    doc = doc.replace(f"<h2>{num_old} {word}", f'<h2><span class="hn" dir="ltr">{num_new}</span> {word}')
doc = doc.replace("۲.۱ معماری", '<span class="hn" dir="ltr">2.1</span> معماری').replace("۲.۲ قابلیت", '<span class="hn" dir="ltr">2.2</span> قابلیت')
doc = doc.replace("هٔ", "ۀ")  # precomposed heh with hamza: the combining mark was drawn detached by the font fallback
(HERE / "manuscript_softwarex_fa.html").write_text(doc, encoding="utf-8")
(HERE / "softwarex_fa.css").write_text(r"""
@page { size: A4; margin: 22mm 20mm 22mm 20mm;
  @top-right { content: "pyssms: نرم‌افزار سنجه‌های جانشین ایمنی"; font: 9pt 'B Nazanin', 'Vazirmatn', serif; color: #444; }
  @top-left { content: "ناصرعلوی"; font: 9pt 'B Nazanin', 'Vazirmatn', serif; color: #444; }
  @bottom-center { content: counter(page); font: 10pt 'Times New Roman', serif; color: #222; } }
@page :first { @top-left { content: none; } @top-right { content: none; } }
html { hyphens: manual; }
body { font-variant-ligatures: none; direction: rtl; font-family: 'B Nazanin', 'Vazirmatn', 'Times New Roman', serif; font-size: 12pt; line-height: 1.7; margin: 0; color: #000; }
header { text-align: center; margin-bottom: 6pt; }
h1.title { font-size: 18pt; line-height: 1.5; margin: 0 0 8pt 0; }
p.author { font-size: 13pt; margin: 0; text-align: center; }
p.aff { font-size: 10pt; color: #333; margin: 1pt 8mm; text-align: center; line-height: 1.55; }
section.abstract { border-top: 1pt solid #000; border-bottom: 1pt solid #000; margin: 6pt 0 8pt 0; padding: 2pt 0 4pt 0; }
section.abstract h2 { margin: 3pt 0 1pt 0; font-size: 12.4pt; }
section.abstract p { font-size: 10.8pt; line-height: 1.6; margin: 2pt 0; }
h2 { font-size: 14pt; margin: 14pt 0 3pt 0; break-after: avoid; }
h3 { font-size: 11.8pt; margin: 7pt 0 1pt 0; display: inline; font-weight: bold; }
h3.sub { display: block; font-size: 12.4pt; margin: 9pt 0 2pt 0; }
h3 + p { display: inline; }
p { margin: 0 0 4pt 0; text-align: justify; orphans: 2; widows: 2; }
.hn { font-family: 'Segoe UI', Arial, sans-serif; unicode-bidi: isolate; }
.lat { direction: ltr; unicode-bidi: isolate; font-family: 'Segoe UI', Arial, sans-serif; font-size: 0.93em; }
.num { font-family: 'Segoe UI', Arial, sans-serif; font-size: 0.93em; unicode-bidi: isolate; direction: ltr; }
.cite { font-family: 'Times New Roman', serif; font-size: 10pt; }
a { color: #000; text-decoration: none; }
pre { direction: ltr; text-align: left; font-family: Consolas, 'Courier New', monospace; font-size: 8.6pt; line-height: 1.32; background: #f5f6f8; border: 0.6pt solid #c8ced6; padding: 5pt 7pt; margin: 4pt 0 8pt 0; break-inside: avoid; white-space: pre; }
figure { margin: 8pt 0 10pt 0; break-inside: avoid; page-break-inside: avoid; }
img { display: block; margin: 3pt auto; max-width: 100%; }
figcaption { font-size: 10.2pt; line-height: 1.5; text-align: center; margin: 2pt 6mm 0 6mm; }
table.tn { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 6pt 0; border-top: 1pt solid #000; border-bottom: 1pt solid #000; break-inside: avoid; }
table.tn caption { caption-side: top; text-align: right; font-size: 9.4pt; padding-bottom: 3pt; }
table.tn th, table.tn td { padding: 2pt 5pt; text-align: right; vertical-align: top; border-bottom: 0.4pt solid #bbb; }
table.tn th { border-bottom: 0.8pt solid #000; }
table.meta { border-collapse: collapse; width: 100%; font-size: 9.6pt; margin: 3pt 0 6pt 0; border-top: 1pt solid #000; border-bottom: 1pt solid #000; break-inside: avoid; }
table.meta th, table.meta td { padding: 2pt 6pt; text-align: right; vertical-align: top; border-bottom: 0.4pt solid #bbb; }
table.meta td[dir=ltr] { text-align: left; font-family: 'Times New Roman', serif; word-break: break-all; }
ol.refs { font-size: 8.4pt; line-height: 1.3; font-family: 'Times New Roman', serif; text-align: left; padding-left: 20pt; margin: 2pt 0; }
ol.refs li { margin: 0 0 2pt 0; word-break: break-word; }
""", encoding="utf-8")
pdf = HERE / "manuscript_softwarex_fa.pdf"
subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", (HERE / "manuscript_softwarex_fa.html").as_uri()],
               check=False, capture_output=True)
print("built", pdf, pdf.exists())
