"""Figures of the SoftwareX paper, drawn by code from results.json and from the package itself.

    python paper_softwarex/make_figures.py        # writes figures/*.pdf and figures/*.png (300 dpi)

The file names follow the printed figure numbers (figure N is fig<N>_*). Rules followed: Okabe-Ito colour-blind-safe palette; panel
letters (A, B, C) identical to the caption; text of at least 7 pt except in the architecture diagram; every number comes from
results.json or is computed by pyssms; the geometry is computed by pyssms, not drawn by hand. Figure 1 also exists in Persian
(fig1_architecture_fa), drawn from the same coordinates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from matplotlib.path import Path as MPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
import figkit as fk  # noqa: E402

from pyssms import conflict_polygon, rectangle  # noqa: E402
from pyssms.contact import avoided_contact_faces  # noqa: E402

R = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
OI = fk.OI
fk.style(8.2)
plt.rcParams.update({"savefig.bbox": "standard", "xtick.labelsize": 7.6, "ytick.labelsize": 7.6, "legend.fontsize": 7.6})
plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "svg.fonttype": "none"})
INK = "#26323d"
S = 7.0  # smallest text of the data figures (pt at the drawn size; the figures are drawn at about their printed width)
LANG = "en"


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=300)
    plt.close(fig)
    import struct
    with open(FIG / f"{name}.png", "rb") as fh:
        fh.seek(16)
        w_px, h_px = struct.unpack(">II", fh.read(8))
    print("saved", name, f"{w_px / 300:.2f} x {h_px / 300:.2f} in (page text width 5.42 in)")


def T(en: str, fa: str | None = None) -> str:
    """Text in the language of the figure being drawn."""
    # matplotlib 3.11 shapes and reorders Arabic-script text itself (raqm); reshaping it again would break the letters
    return en if (LANG == "en" or fa is None) else fa


# =========================================================================================================== Fig 1
FW = 5.4   # printed width of every figure (inches): the figures are placed at the text width, so point sizes are printed sizes
S = 7.6    # smallest text of the data figures (pt, printed size)
FS = 7.4   # text inside the boxes of the flowchart


def box(ax, x, y, w, h, text, fc="#ffffff", ec=INK, fs=None, bold=False, lw=0.9, r=0.05, color=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs or FS, color=color, fontweight="bold" if bold else "normal",
            zorder=3, linespacing=1.12)


def diamond(ax, cx, cy, w, h, text, fs=None, fc="#FFF6DA"):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)], closed=True, fc=fc, ec=INK, lw=0.9, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs or FS, color=INK, zorder=3, linespacing=1.1)


def arrow(ax, p, q, text=None, tpos=(0, 0), color=INK, ls="-", rad=0.0, fs=None, lw=0.9):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, lw=lw, color=color, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=1, shrinkA=0, shrinkB=0))
    if text:
        ax.text((p[0] + q[0]) / 2 + tpos[0], (p[1] + q[1]) / 2 + tpos[1], text, fontsize=fs or S, color=color, fontweight="bold",
                ha="center", va="center", zorder=4, bbox=dict(fc="white", ec="none", pad=0.5))


def line(ax, xs, ys, color="#7a8794", lw=0.9):
    ax.plot(xs, ys, color=color, lw=lw, zorder=1, solid_capstyle="butt")


def fig1(lang: str = "en"):
    global LANG
    LANG = lang
    if lang == "fa":
        plt.rcParams["font.family"] = ["Tahoma", "DejaVu Sans"]
    H = 7.8
    fig = plt.figure(figsize=(FW, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, FW)
    ax.set_ylim(0, H)
    ax.axis("off")
    ax.grid(False)
    col = {"in": "#E8F1F8", "core": "#FDEBD3", "out": "#E7F3EC", "ver": "#F1ECF5"}
    X0, X1 = 0.34, 5.38
    # stage labels, rotated, on the left
    for yc, t in ((7.35, T("1  READ", "1  خواندن")), (6.3, T("2  PREPARE", "2  آماده‌سازی")), (3.75, T("3  COMPUTE", "3  محاسبه")), (1.2, T("4  REPORT", "4  گزارش"))):
        ax.text(0.14, yc, t, rotation=90, ha="center", va="center", fontsize=8.2, fontweight="bold", color=OI["blue"])
    for y0, y1 in ((6.95, 7.75), (5.95, 6.65), (1.75, 5.82), (0.9, 1.5)):
        ax.plot([0.3, 0.3], [y0, y1], color=OI["blue"], lw=1.2)
    # 1 READ
    ins = [T("SSAM .trj\n(read, write)", "SSAM .trj\n(خواندن، نوشتن)"), T("SUMO FCD;\nVISSIM .fzp", "SUMO FCD\nVISSIM .fzp"),
           "LevelX: inD,\nrounD, uniD,\nexiD, highD", "NGSIM: US-101,\nI-80,\nLankershim,\nPeachtree", T("generic table;\nsynthetic\nscenarios", "جدول عمومی\nسناریوهای\nمصنوعی")]
    bw, gap = 0.94, 0.09
    cx = []
    for i, t in enumerate(ins):
        x = X0 + i * (bw + gap)
        box(ax, x, 7.0, bw, 0.75, t, fc=col["in"])
        line(ax, [x + bw / 2, x + bw / 2], [7.0, 6.85])
        cx.append(x + bw / 2)
    line(ax, [cx[0], cx[-1]], [6.85, 6.85])
    # 2 PREPARE
    pw = 1.6
    px = [X0, X0 + pw + 0.13, X0 + 2 * (pw + 0.13)]
    box(ax, px[0], 5.95, pw, 0.7, T("Trajectories\nid, t, x, y, heading,\nvelocity, body size", "Trajectories\nشناسه، زمان،\nمکان، جهت،\nسرعت، ابعاد"), fc=col["in"])
    box(ax, px[1], 5.95, pw, 0.7, T("preprocessing\ncausal or centred\nsmoothing", "preprocessing\nهموارسازی علّی\nیا مرکزی"), fc=col["in"])
    box(ax, px[2], 5.95, pw, 0.7, T("process\ncandidate pairs;\nper-frame series", "process\nجفت‌های نامزد\nو سری هر قاب"), fc=col["in"])
    arrow(ax, (cx[0] + 0.33, 6.85), (cx[0] + 0.33, 6.65))
    arrow(ax, (px[0] + pw, 6.3), (px[1], 6.3))
    arrow(ax, (px[1] + pw, 6.3), (px[2], 6.3))
    # trunk from process to K and to ssm1d
    tx = px[2] + pw / 2
    line(ax, [tx, tx], [5.95, 5.82], color=INK)
    line(ax, [1.62, tx], [5.82, 5.82], color=INK)
    arrow(ax, (1.62, 5.82), (1.62, 5.7), color=INK)
    arrow(ax, (tx, 5.82), (tx, 5.7), color=INK)
    # 3 COMPUTE
    ax.add_patch(FancyBboxPatch((X0, 5.0), 2.76, 0.7, boxstyle="round,pad=0,rounding_size=0.05", fc=col["core"], ec=INK, lw=0.9, zorder=2))
    ax.text(X0 + 1.38, 5.52, T("conflict polygon K  (timetime)", "چندضلعی تداخل K  (timetime)"), ha="center", va="center", fontsize=FS + 0.2, fontweight="bold", zorder=3)
    ax.text(X0 + 1.38, 5.22, T("Minkowski difference of the bodies in\nthe plane of the predicted arrival times (τ₁, τ₂)",
                               "تفاضل مینکوفسکی دو بدنه در صفحهٔ\nزمان‌های رسیدن پیش‌بینی‌شده (τ₁, τ₂)"),
            ha="center", va="center", fontsize=S - 0.4, zorder=3, linespacing=1.1)
    dcx = 1.32
    diamond(ax, dcx, 4.2, 1.95, 0.9, T("K meets the\ndiagonal τ₁ = τ₂?", "آیا K قطر\nτ₁ = τ₂ را\nقطع می‌کند؟"))
    arrow(ax, (dcx, 5.0), (dcx, 4.65))
    box(ax, 2.5, 3.8, 1.15, 0.8, T("state A\ncollision\ncourse: TTC", "حالت A\nمسیر برخورد\nTTC"), fc="#F8D6C9")
    arrow(ax, (dcx + 0.975, 4.2), (2.5, 4.2), T("yes", "بله"), (0.0, 0.15))
    diamond(ax, dcx, 3.05, 1.95, 0.9, T("K non-empty\nwithin the horizon?", "K درون افق\nناتهی است؟"))
    arrow(ax, (dcx, 3.75), (dcx, 3.5), T("no", "خیر"), (0.17, 0.0))
    box(ax, 2.5, 2.65, 1.15, 0.8, T("state B\ncrossing course:\nTAdv, T2, TG", "حالت B\nمسیر متقاطع\nTAdv, T2, TG"), fc="#FBE7B8")
    arrow(ax, (dcx + 0.975, 3.05), (2.5, 3.05), T("yes", "بله"), (0.0, 0.15))
    box(ax, X0, 1.85, 1.95, 0.42, T("state C: no overlap", "حالت C: بدون هم‌پوشانی"), fc="#E9ECEF")
    arrow(ax, (dcx, 2.6), (dcx, 2.27), T("no", "خیر"), (0.17, 0.0))
    # right column
    box(ax, 3.85, 4.15, 1.53, 1.55, T("ssm1d, stories\nten car-following\nmeasures\n(1-D, no polygon)", "ssm1d, stories\nده سنجهٔ دنباله‌روی\nیک‌بعدی\nبدون چندضلعی"), fc=col["core"])
    box(ax, 3.85, 2.6, 1.53, 1.35, T("further readings\nof K: contact,\ndisturbance,\nmargins, escape,\nseverity", "خوانش‌های دیگر K\ncontact, disturbance,\nmargins, escape,\nseverity"), fc=col["core"], fs=FS - 0.2)
    # feeders to the report row
    line(ax, [3.65, 3.75], [4.2, 4.2])
    line(ax, [3.65, 3.75], [3.05, 3.05])
    line(ax, [3.85, 3.75], [4.9, 4.9])
    line(ax, [3.85, 3.75], [3.3, 3.3])
    line(ax, [3.75, 3.75], [4.9, 1.66])
    line(ax, [0.8, 4.9], [1.66, 1.66])
    # 4 REPORT
    outs = [T("hierarchy\nA, B, C", "hierarchy\nA, B, C"), T("calibration\nerror scales", "calibration\nمقیاس خطا"), T("scenario\nsummaries", "scenario\nخلاصه‌ها"),
            T("bank, datasets\nNGSIM windows", "bank, datasets\nپنجره‌های NGSIM"), T("viz\nplots", "viz\nنمودارها")]
    for i, t in enumerate(outs):
        x = X0 + i * (bw + gap)
        box(ax, x, 0.9, bw, 0.6, t, fc=col["out"], fs=FS - 0.2)
        arrow(ax, (x + bw / 2, 1.66), (x + bw / 2, 1.5), lw=0.9, color="#7a8794")
    ax.add_patch(FancyBboxPatch((X0, 0.12), X1 - X0, 0.58, boxstyle="round,pad=0,rounding_size=0.05", fc=col["ver"], ec=OI["pink"], lw=0.9, zorder=2))
    e = R["equiv"]
    ax.text((X0 + X1) / 2, 0.41, T(f"verification: {R['tests']['total']} automated tests | {e['compared']:,} random encounters\ncompared with the printed procedure: "
                                   f"{e['disagree_total']} disagreements | simulations of the stories",
                                   f"راستی‌آزمایی: {R['tests']['total']} آزمون خودکار | {e['compared']:,} رویارویی تصادفی با روش چاپ‌شده\n"
                                   f"سنجیده شد: {e['disagree_total']} ناهم‌خوانی | شبیه‌سازی گام‌به‌گام داستان‌ها"),
            ha="center", va="center", fontsize=S - 0.4, zorder=3, linespacing=1.15)
    save(fig, "fig1_architecture" + ("_fa" if lang == "fa" else ""))
    LANG = "en"
    plt.rcParams["font.family"] = "DejaVu Sans"


# =========================================================================================================== Fig 2
def _scene(angle2: float, p1, p2, horizon: float = 12.0):
    """Conflict polygon of road user 1 (along +x) and road user 2 heading ``angle2`` (rad); both 10 m/s, 4.5 x 1.8 m."""
    sh1, sh2 = rectangle(0.0, 4.5, 1.8), rectangle(angle2, 4.5, 1.8)
    v1 = np.array([[10.0, 0.0]])
    v2 = 10.0 * np.array([[np.cos(angle2), np.sin(angle2)]])
    return conflict_polygon(sh1, np.array([p1], float), v1, sh2, np.array([p2], float), v2, horizon=horizon)


def fig2():
    sh1, sh2 = rectangle(0.0, 4.5, 1.8), rectangle(np.pi / 2, 4.5, 1.8)
    d1, d2, speed, ln, wd = 20.0, 30.0, 10.0, 4.5, 1.8
    p1, v1 = np.array([[-d1, 0.0]]), np.array([[speed, 0.0]])
    p2, v2 = np.array([[0.0, -d2]]), np.array([[0.0, speed]])
    K = conflict_polygon(sh1, p1, v1, sh2, p2, v2, horizon=10.0)
    ac = avoided_contact_faces(sh1, p1, v1, sh2, p2, v2, horizon=10.0)
    tau1, tau2, tadv = float(ac.tau1[0]), float(ac.tau2[0]), float(ac.tadv[0])
    fig = plt.figure(figsize=(FW, 5.7))
    gs = fig.add_gridspec(2, 6, height_ratios=[1.0, 1.12], hspace=0.42, wspace=2.0, left=0.12, right=0.97, top=0.95, bottom=0.07)
    # ---- A: plan view
    ax = fig.add_subplot(gs[0, 0:3])
    ax.set_aspect("equal")
    ax.grid(False)
    for p, v, sh, c, nm in ((p1[0], v1[0], sh1[0], OI["blue"], "1"), (p2[0], v2[0], sh2[0], OI["orange"], "2")):
        ax.add_patch(Polygon(sh + p, closed=True, fc="none", ec=c, lw=0.9, ls=(0, (2, 2)), zorder=2))
        end = p + v * (tau1 if nm == "1" else tau2)
        ax.plot([p[0], end[0]], [p[1], end[1]], color=c, lw=0.8, ls=":", zorder=1)
        ax.add_patch(Polygon(sh + end, closed=True, fc=c, ec=INK, lw=0.9, alpha=0.8, zorder=3))
    ax.text(-27, 3.6, "road user 1", fontsize=S, color=OI["blue"], ha="left")
    ax.text(3.0, -29.5, "road user 2", fontsize=S, color=OI["orange"], ha="left")
    ax.annotate("", xy=(-3.5, 0.0), xytext=(-13, 0.0), arrowprops=dict(arrowstyle="-|>", color=OI["blue"], lw=1.0))
    ax.annotate("", xy=(0.0, -13), xytext=(0.0, -22), arrowprops=dict(arrowstyle="-|>", color=OI["orange"], lw=1.0))
    ax.plot([0.9], [-0.9], "o", ms=5.5, mfc="white", mec=OI["pink"], mew=1.6, zorder=6)
    ax.text(-27, -9.0, "corners\ntouch,\nno overlap", fontsize=S, color=INK, ha="left", va="center")
    ax.plot([-15.5, -0.6], [-7.2, -1.4], color=INK, lw=0.6)
    ax.set_xlim(-28, 10)
    ax.set_ylim(-34, 8)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    fk.letter(ax, "A", dx=0.0, dy=1.02)
    # ---- B: polygon K, zoomed
    ax = fig.add_subplot(gs[0, 3:6])
    lo = min(K[:, 0].min(), K[:, 1].min()) - 0.28
    hi = max(K[:, 0].max(), K[:, 1].max()) + 0.28
    ax.add_patch(Polygon(K, closed=True, fc=fk.HL, ec=OI["orange"], lw=1.4, zorder=2))
    ax.plot([lo, hi], [lo, hi], color=INK, lw=1.0, ls="--", zorder=1)
    ax.text(hi - 0.05, hi - 0.34, "τ₁ = τ₂", fontsize=S, color=INK, ha="right", va="center", rotation=45, rotation_mode="anchor",
            bbox=dict(fc="white", ec="none", pad=0.8, alpha=0.9))
    ax.plot([tau1], [tau2], "o", ms=5.5, mfc="white", mec=OI["pink"], mew=1.6, zorder=6)
    ax.annotate("", xy=(tau2, tau2), xytext=(tau1, tau2), arrowprops=dict(arrowstyle="|-|", color=OI["blue"], lw=1.3, shrinkA=0, shrinkB=0,
                                                                          mutation_scale=3.5), zorder=5)
    ax.text(tau2 + 0.1, tau2 - 0.1, f"TAdv = {tadv:.2f} s", fontsize=S, color=OI["blue"], ha="center", va="top", fontweight="bold",
            bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85), zorder=8)
    ax.plot([lo, tau1], [tau2, tau2], color=OI["green"], lw=1.0, ls=":", zorder=3)
    ax.plot([lo], [tau2], marker=">", color=OI["green"], ms=5, clip_on=False, zorder=7)
    ax.text(lo + 0.04, tau2 + 0.07, f"T2 = {tau2:.3f} s", fontsize=S, color=OI["green"], va="bottom", ha="left",
            bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85), zorder=8)
    ax.text(float(K[:, 0].mean()), float(K[:, 1].mean()) + 0.12, "K", fontsize=12, fontweight="bold", color=OI["orange"], ha="center", va="center", zorder=7)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("τ₁ (s)")
    ax.set_ylabel("τ₂ (s)")
    fk.letter(ax, "B", dx=0.0, dy=1.02)
    # ---- C: three encounters in one plane
    H = 5.0
    ax = fig.add_subplot(gs[1, 1:5])
    ax.add_patch(Rectangle((0.3, 0.3), H - 0.3, H - 0.3, fc="#f3f5f7", ec="#9aa5b0", lw=0.8, zorder=0))
    ax.plot([0.3, 6.8], [0.3, 6.8], color=INK, lw=1.0, ls="--", zorder=1)
    ax.text(0.4, H - 0.08, "horizon", fontsize=S, color="#55606b", ha="left", va="top")
    scenes = [
        ("A", _scene(np.pi / 2, (-20.0, 0.0), (0.0, -20.0)), "#F8D6C9", OI["orange"]),
        ("B", _scene(np.radians(60.0), (-42.0, 0.0), tuple(-10.0 * np.array([np.cos(np.radians(60.0)), np.sin(np.radians(60.0))]))), "#FBE7B8", OI["yellow"]),
        ("C", _scene(np.pi / 2, (-20.0, 0.0), (0.0, -60.0)), "#E9ECEF", OI["grey"]),
    ]
    info = {}
    for nm, Kc, fc, ec in scenes:
        ax.add_patch(Polygon(Kc, closed=True, fc=fc, ec=ec, lw=1.3, zorder=3))
        cx, cy = float(Kc[:, 0].mean()), float(Kc[:, 1].mean())
        ax.text(cx - 0.4 if nm == "A" else cx + 0.4, cy + (0.45 if nm == "B" else 0.0), nm, fontsize=11, fontweight="bold", color=INK, ha="right" if nm == "A" else "left", va="center", zorder=7)
        if nm == "A":
            t = np.linspace(0.0, H, 6001)
            inside = MPath(Kc).contains_points(np.c_[t, t])
            ttc = float(t[inside][0])
            info["ttc_a"] = ttc
            ax.plot([ttc], [ttc], "o", ms=5, mfc="white", mec=OI["pink"], mew=1.5, zorder=8)
            ax.text(ttc + 0.35, ttc + 2.45, f"TTC = {ttc:.2f} s", fontsize=S, color=INK, ha="left", va="bottom")
            ax.plot([ttc + 0.05, ttc + 0.55], [ttc + 0.05, ttc + 2.4], color=INK, lw=0.6, zorder=7)
        if nm == "B":
            k = int(np.argmin(np.abs(Kc[:, 0] - Kc[:, 1])))
            v1_, v2_ = float(Kc[k, 0]), float(Kc[k, 1])
            info["tadv_b"] = abs(v1_ - v2_)
            ax.annotate("", xy=(v2_, v2_), xytext=(v1_, v2_), arrowprops=dict(arrowstyle="|-|", color=OI["blue"], lw=1.3, shrinkA=0, shrinkB=0,
                                                                              mutation_scale=3.5), zorder=8)
            ax.text((v1_ + v2_) / 2 + 0.1, v2_ - 0.2, f"TAdv = {abs(v1_ - v2_):.2f} s", fontsize=S, color=OI["blue"], ha="center", va="top", fontweight="bold",
                    bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.85), zorder=9)
    ax.set_xlim(0.3, 6.8)
    ax.set_ylim(0.3, 6.8)
    ax.set_aspect("equal")
    ax.set_xlabel("τ₁ (s)")
    ax.set_ylabel("τ₂ (s)")
    fk.letter(ax, "C", dx=0.0, dy=1.02)
    save(fig, "fig2_polygon")
    return {"tau1": tau1, "tau2": tau2, "tadv": tadv, "len": ln, "wid": wd, "speed": speed, "d1": d1, "d2": d2, **info}


# =========================================================================================================== Fig 4 (ten measures)
TIME = [("ttc1", "TTC1  constant speeds"), ("ttc2", "TTC2  constant accelerations"), ("ttc3", "TTC3  constant jerks"), ("ttcd", "TTCD  leader brakes to a stop")]
DS = [("highd", "highD"), ("exid", "exiD"), ("ngsim", "NGSIM")]
DCOL = {"highd": OI["blue"], "exid": OI["green"], "ngsim": OI["orange"]}


def fig4():
    fig = plt.figure(figsize=(FW, 6.3))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.45, 1.0], hspace=0.38, left=0.27, right=0.90, top=0.91, bottom=0.07)
    ax = fig.add_subplot(gs[0])
    H = R["params"]["horizon"]
    ypos, ylab = [], []
    y = 0.0
    for m, lab in TIME:
        for key, nm in DS:
            q = R[key]["m"][m]
            ax.plot([q["p5"], q["p95"]], [y, y], color=DCOL[key], lw=1.0, solid_capstyle="round", zorder=2)
            ax.plot([q["p25"], q["p75"]], [y, y], color=DCOL[key], lw=5.5, solid_capstyle="butt", zorder=3)
            ax.plot([q["p50"]], [y], "|", color="white", ms=7, mew=1.6, zorder=4)
            ax.text(10.45, y, f"{q['defined']:.0f}%", fontsize=S, va="center", ha="left", color="#444")
            y += 1
        ylab.append((y - 2.0, lab))
        y += 0.9
    ax.axvline(H, color="#9aa5b0", lw=1.0, ls=":", zorder=1)
    ax.text(H - 0.08, -0.9, "horizon", fontsize=S, color="#55606b", ha="right", va="bottom")
    ax.set_yticks([p for p, _ in ylab])
    ax.set_yticklabels([l.replace("  ", "\n", 1) for _, l in ylab], fontsize=S)
    ax.invert_yaxis()
    ax.set_xlim(0, 10.3)
    ax.axvline(3.0, color=INK, lw=0.8, ls="--")
    ax.text(3.08, -0.9, "3 s", fontsize=S, color=INK, va="bottom")
    ax.text(10.45, -0.9, "defined", fontsize=S, color="#444", va="bottom")
    ax.set_xlabel("time to collision (s)")
    ax.grid(axis="y", visible=False)
    for key, nm in DS:
        ax.plot([], [], color=DCOL[key], lw=5, label=nm)
    ax.legend(loc="lower left", fontsize=S, ncol=3, bbox_to_anchor=(0.0, 1.03), columnspacing=1.0, handlelength=1.2)
    fk.letter(ax, "A", dx=-0.02, dy=1.1)
    # B: share of rows with a time measure <= 3 s
    ax = fig.add_subplot(gs[1])
    w = 0.26
    ypos_hd = {}
    for j, (key, nm) in enumerate(DS):
        vals = [max(R[key]["m"][m]["crit"], 0.02) for m, _ in TIME]
        xs = np.arange(len(TIME)) + (j - 1) * w
        ax.barh(xs, vals, height=w * 0.92, color=DCOL[key], zorder=3)
        for xv, v in zip(xs, vals):
            ax.text(v * 1.18, xv, f"{v:.2f}" if v < 1 else f"{v:.1f}", fontsize=S, va="center", ha="left", color=INK)
        if key == "highd":
            ypos_hd = {"ttc1": xs[0], "ttcd": xs[3]}
    ax.set_xscale("log")
    ax.set_xlim(0.02, 2000)
    ax.set_xticks([0.1, 1, 10, 100])
    ax.set_xticklabels(["0.1", "1", "10", "100"])
    ax.set_yticks(np.arange(len(TIME)))
    ax.set_yticklabels([m.upper() for m, _ in TIME], fontsize=S)
    ax.invert_yaxis()
    ax.set_xlabel("sampled rows with the time measure ≤ 3 s (%, log scale)")
    ax.grid(axis="y", visible=False)
    r = R["highd"]["ratio_ttcd_ttc1"]
    xb = 260.0
    ax.annotate("", xy=(xb, ypos_hd["ttc1"]), xytext=(xb, ypos_hd["ttcd"]),
                arrowprops=dict(arrowstyle="<->", color=fk.HL_EDGE, lw=1.4, shrinkA=0, shrinkB=0, mutation_scale=7), annotation_clip=False)
    ax.text(xb * 1.35, (ypos_hd["ttc1"] + ypos_hd["ttcd"]) / 2, f"×{r:.0f}\nhighD,\nsame\nrows", fontsize=S, color=fk.HL_EDGE, fontweight="bold",
            ha="left", va="center", linespacing=1.1)
    fk.letter(ax, "B", dx=-0.02, dy=1.03)
    save(fig, "fig4_ten_measures")


# =========================================================================================================== Fig 5 (correlations)
ROWS = [("ttc1", "TTC1", "▼"), ("ttc2", "TTC2", "▼"), ("ttc3", "TTC3", "▼"), ("ttcd", "TTCD", "▼"), ("drac", "DRAC", "▲"), ("mdrac", "MDRAC", "▲"),
        ("dcia", "DCIA", "▲"), ("psd", "PSD", "▼"), ("mpsd", "MPSD", "▼"), ("sdi", "SDI", "▲")]
GROUPS = [3, 4]  # separators after TTC3 (constant motion) and after TTCD (leader brakes); the rest: the follower brakes


def fig5():
    colkeys = [("k_ttc", "TTC\npoly"), ("k_tadv", "TAdv"), ("k_t2", "T2"), ("k_tg", "TG"), ("req_brake", "req.\nbrak.")]
    fig, axes = plt.subplots(1, 3, figsize=(FW, 4.6), gridspec_kw=dict(wspace=0.06, left=0.135, right=0.885, top=0.86, bottom=0.17))
    cmap = plt.get_cmap("RdBu_r")
    for ax, (key, nm) in zip(axes, DS):
        M = np.array([[R[key]["rho"][m][c] for c, _ in colkeys] for m, _, _ in ROWS])
        im = ax.imshow(M, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
        ax.grid(False)
        ax.set_xticks(range(len(colkeys)))
        ax.set_xticklabels([l for _, l in colkeys], fontsize=S - 0.4)
        ax.set_yticks(range(len(ROWS)))
        ax.set_yticklabels([f"{l} {d}" for _, l, d in ROWS] if key == "highd" else [], fontsize=S)
        ax.set_title(nm, fontsize=8.5, fontweight="bold", pad=24)
        ax.xaxis.tick_top()
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                v = M[i, j]
                txt = f"{v:.2f}".replace("0.", ".") if v >= 0 else f"{v:.2f}".replace("0.", ".")
                ax.text(j, i, txt, ha="center", va="center", fontsize=S - 0.8, color="white" if abs(v) > 0.6 else INK)
                if round(abs(v), 2) >= 0.90:
                    ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="black", lw=1.8, zorder=5))
        for g in GROUPS:
            ax.axhline(g - 0.5, color="black", lw=0.9)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(length=0)
    for yy, lab in ((1.0, "constant\nmotion"), (3.0, "leader\nbrakes"), (6.5, "follower\nbrakes")):
        axes[2].text(4.62, yy, lab, fontsize=S - 0.4, color="#55606b", ha="left", va="center", transform=axes[2].transData, clip_on=False)
    cax = fig.add_axes([0.30, 0.075, 0.42, 0.022])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_ticks([-1, -0.5, 0, 0.5, 1])
    cb.ax.tick_params(labelsize=S, length=2)
    cb.set_label("Spearman rank correlation", fontsize=S)
    cb.outline.set_visible(False)
    for ax, let in zip(axes, "ABC"):
        fk.letter(ax, let, dx=0.0, dy=1.3)
    save(fig, "fig5_correlations")


# =========================================================================================================== Fig 6 (hierarchy)
def fig6():
    fig = plt.figure(figsize=(FW, 5.4))
    gsA = fig.add_gridspec(1, 1, left=0.115, right=0.685, top=0.90, bottom=0.50)
    gsB = fig.add_gridspec(1, 1, left=0.115, right=0.43, top=0.37, bottom=0.12)
    ax = fig.add_subplot(gsA[0, 0])
    order = sorted(R["hier"], key=lambda n: -R["hier"][n]["A"])
    parts = [("A_lt15", "A  TTC < 1.5 s", "#9E2A0F"), ("A_15_3", "A  1.5–3 s", "#D55E00"), ("A_3_6", "A  3–6 s", "#E8946B"), ("A_gt6", "A  > 6 s", "#F4C7B0"),
             ("B_lt1", "B  TAdv < 1 s", "#B58200"), ("B_1_2", "B  1–2 s", "#E69F00"), ("B_2_4", "B  2–4 s", "#F2CB6B"), ("B_gt4", "B  > 4 s", "#FAE6B5")]
    for i, nm in enumerate(order):
        h = R["hier"][nm]
        left = 0.0
        for k, lab, c in parts:
            v = 100 * h[k] / h["overlap"]
            ax.barh(i, v, left=left, color=c, ec="white", lw=0.5, height=0.7, zorder=3, label=lab if i == 0 else None)
            left += v
        ax.text(101.5, i, f"A {h['A']:.0f}%, A or B {h['overlap']:.0f}%,\nC {h['C']:.0f}%, {h['pairs'] / 1000:,.0f}k pairs", fontsize=S - 0.4, va="center", ha="left",
                color=INK, linespacing=1.15)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=S)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("pairs whose future paths overlap (A or B), split by level (%)")
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=4, fontsize=S - 0.8, loc="lower left", bbox_to_anchor=(0.0, 1.0), columnspacing=0.7, handlelength=0.9, borderaxespad=0.2)
    fk.letter(ax, "A", dx=-0.1, dy=1.14)
    ax = fig.add_subplot(gsB[0, 0])
    s = R["smooth"]
    xs = np.array([0, 1])
    vals = [s["raw_ttc15"], s["smoothed_ttc15"]]
    ax.bar(xs, vals, color=[OI["grey"], OI["orange"]], width=0.55, zorder=3)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.18, f"{v:.1f}%", ha="center", fontsize=8.4, fontweight="bold")
    ax.set_xticks(xs)
    ax.set_xticklabels(["own\npositions,\nspeeds", "smoothed\npositions"], fontsize=S)
    ax.set_ylim(0, 9.6)
    ax.set_ylabel("pairs with TTC < 1.5 s (%)")
    ax.set_title("NGSIM, Peachtree Street", fontsize=S)
    fk.letter(ax, "B", dx=-0.2, dy=1.1)
    save(fig, "fig6_hierarchy")


# =========================================================================================================== Fig 3 (verification)
def fig3():
    fig = plt.figure(figsize=(FW, 6.2))
    gs = fig.add_gridspec(3, 1, height_ratios=[0.8, 1.15, 1.15], hspace=0.72, left=0.31, right=0.96, top=0.95, bottom=0.07)
    # A: agreement with the printed procedure
    ax = fig.add_subplot(gs[0])
    e = R["equiv"]
    ax.barh([0], [100], color=OI["blue"], height=0.62, zorder=3)
    ax.text(50, 0, f"{e['disagree_total']} disagreements in {5 * e['compared']:,} comparisons", ha="center", va="center", color="white", fontsize=S + 0.2,
            fontweight="bold", zorder=4)
    miss = 100 * e["axis_literal_ttc_misses"] / e["axis_compared"]
    ax.barh([1], [miss], color=OI["pink"], height=0.62, zorder=3)
    ax.barh([1], [100 - miss], left=[miss], color=OI["light"], height=0.62, zorder=3)
    ax.text(miss + 2, 1, f"TTC missed: {e['axis_literal_ttc_misses']:,} of {e['axis_compared']:,}", ha="left", va="center", fontsize=S, color=INK, zorder=4)
    ax.set_yticks([0, 1])
    ax.set_yticklabels([f"polygon vs printed\nprocedure ({e['compared']:,}\ncompared encounters)", "axis-parallel cases,\nliteral in-section\ntest"], fontsize=S)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of the compared cases (%)")
    ax.set_ylim(1.5, -0.5)
    ax.grid(axis="y", visible=False)
    fk.letter(ax, "A", dx=-0.3, dy=1.02)
    # B: timing
    ax = fig.add_subplot(gs[1])
    b = R["bench"]
    names = ["polygon K, 8-row form", "32 combinations,\nvectorised", "polygon K, general\n12-row form", "32 combinations, pure-\nPython loop (not like-for-like)"]
    v = [b["us_per"], b["vector32_us"], 1e6 * b["general12_s"] / b["n"], b["loop_us"]]
    bars = ax.barh(range(4), v, color=[OI["orange"], OI["sky"], "#F0B27A", OI["light"]], height=0.62, zorder=3)
    bars[3].set_hatch("///")
    bars[3].set_edgecolor("white")
    ax.set_xscale("log")
    ax.set_xlim(1, 4e4)
    ax.set_xticks([1, 10, 100, 1000, 10000])
    ax.set_xticklabels(["1", "10", "100", "1k", "10k"])
    for i, x in enumerate(v):
        ax.text(x * 1.25, i, f"{x:,.1f}" if x < 100 else f"{x:,.0f}", fontsize=S, va="center")
    ax.set_yticks(range(4))
    ax.set_yticklabels(names, fontsize=S)
    ax.invert_yaxis()
    ax.set_xlabel("microseconds per encounter (log scale)")
    ax.grid(axis="y", visible=False)
    fk.letter(ax, "B", dx=-0.3, dy=1.05)
    # C: tests
    ax = fig.add_subplot(gs[2])
    t = R["tests"]
    keys = ["geometry", "stories", "contact", "severity", "data", "other"]
    labs = ["time-time geometry," + chr(10) + "margins", "stories, ssm1d," + chr(10) + "escape", "contact faces", "severity", "readers, process," + chr(10) + "NGSIM bank", "other"]
    vals = [t[k] for k in keys]
    ax.barh(range(len(keys)), vals, color=OI["green"], height=0.62, zorder=3)
    for i, x in enumerate(vals):
        ax.text(x + 0.8, i, str(x), fontsize=S, va="center")
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels(labs, fontsize=S)
    ax.invert_yaxis()
    ax.set_xlim(0, 58)
    ax.set_xlabel(f"automated tests (total {t['total']})")
    ax.grid(axis="y", visible=False)
    fk.letter(ax, "C", dx=-0.3, dy=1.05)
    save(fig, "fig3_verification")


if __name__ == "__main__":
    fig1("en")
    fig1("fa")
    info = fig2()
    fig3()
    fig4()
    fig5()
    fig6()
    (HERE / "fig_numbers.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
