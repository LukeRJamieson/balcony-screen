"""Visual cutting guide for the balcony screen benches.

Draws every stock length to scale with its pieces laid out in cutting order,
straight from the model's optimised cutting plan, so it always matches the
Cut List and Cutting Plan sheets in the spreadsheet.

    python cutting_guide.py            -> ../Cutting_Guide.pdf

Each length shows:
  - the squaring trim at the start of the length
  - each piece to scale, labelled with its mark, length and module
  - the 3 mm saw kerf between pieces
  - where the store should make its cut (merbau only)
  - the offcut left at the end, with its length
  - a tick box, so you can mark each length off as you cut it
"""
import os
from collections import Counter, OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

import BalconyScreenBench as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "Cutting_Guide.pdf")

BARS_PER_PAGE = 9
PAGE = (11.69, 8.27)                       # A4 landscape, inches
INK, MUTED, RULE = "#1F2B25", "#56645C", "#C9D1CB"
WASTE = "#E6E6E3"
PALETTE = ["#C99A63", "#A9C58E", "#8FB6D1", "#E0A98C", "#C4A6D6", "#D9C77A",
           "#93C9BE", "#D8A0B5", "#B7B28A", "#9FB0D9", "#D1B08C", "#A7CFA0"]

SECTION = {"T90x45": "90 x 45 H3 treated pine", "D90x22": "90 x 22 H3 decking",
           "M42x19": "42 x 19 merbau screening"}


def piece_layout(b, c):
    """Return [(start_mm, length_mm, mark, pid)] in cutting order, plus the
    in-store cut position (or None). Mirrors the packing rules in
    BalconyScreenBench._pack / _store_split exactly."""
    if b["store_cut_at"] is not None:
        _, grp_a, grp_b = S._store_split(b["pieces"], c)
        groups, cut_at = [grp_a, grp_b], b["store_cut_at"]
    else:
        groups, cut_at = [sorted(b["pieces"], key=lambda p: -p[1])], None
    out, x = [], c.end_trim / 2
    for gi, grp in enumerate(groups):
        if gi == 1:
            x = cut_at + c.kerf               # second carry piece starts after the store cut
        for mark, length, pid in grp:
            out.append((x, length, mark, pid))
            x += length + c.kerf
    return out, cut_at


def draw_bar(ax, y, b, c, colours, pid_names):
    stock = b["stock"]
    layout, cut_at = piece_layout(b, c)
    h = 0.62
    # the whole stock length, drawn as offcut; pieces are painted over it
    ax.add_patch(Rectangle((0, y), stock, h, fc=WASTE, ec=MUTED, lw=0.8, hatch="////"))
    # squaring trim at the start
    ax.add_patch(Rectangle((0, y), c.end_trim / 2, h, fc="#FFFFFF", ec=MUTED, lw=0.6))
    for x0, length, mark, pid in layout:
        ax.add_patch(Rectangle((x0, y), length, h, fc=colours[mark], ec=INK, lw=0.9))
        module = pid.split("-")[0]
        label = f"{mark}  {length:.0f}"
        sub = f"{module} · {pid_names[pid]}"
        if length >= 380:
            ax.text(x0 + length / 2, y + h * 0.62, label, ha="center", va="center",
                    fontsize=9.5, fontweight="bold", color=INK)
            ax.text(x0 + length / 2, y + h * 0.26, sub, ha="center", va="center",
                    fontsize=6.8, color=INK)
        else:
            ax.text(x0 + length / 2, y + h * 0.5, label, ha="center", va="center",
                    fontsize=8, fontweight="bold", color=INK, rotation=0)
    # offcut at the end
    end = max(x0 + length for x0, length, _, _ in layout)
    off = stock - end
    if cut_at is not None:
        tail_start = end
        # a group-A-only length leaves its offcut after the store cut
        if all(x0 < cut_at for x0, _, _, _ in layout):
            tail_start = cut_at
        off = stock - tail_start
    if off > 250:
        ax.text(stock - off / 2, y + h / 2, f"offcut {off:.0f}", ha="center", va="center",
                fontsize=8, color=MUTED)
    elif off > 0:
        ax.text(stock, y - 0.03, f"offcut {off:.0f}", ha="right", va="top", fontsize=6.5, color=MUTED)
    # in-store cut (merbau is only sold in 2.7 m, too long to carry)
    if cut_at is not None:
        ax.plot([cut_at, cut_at], [y - 0.14, y + h + 0.14], color="#B3261E", lw=1.8, ls=(0, (4, 2)))
        ax.text(cut_at, y + h + 0.2, f"store cut at {cut_at:.0f}", ha="center", va="bottom",
                fontsize=7, color="#B3261E", fontweight="bold")
    # length number, stock size and tick box
    ax.text(-60, y + h / 2, f"#{b['n']}", ha="right", va="center", fontsize=10, fontweight="bold", color=INK)
    ax.text(-60, y - 0.02, f"{stock / 1000:.1f} m", ha="right", va="top", fontsize=7, color=MUTED)
    ax.add_patch(Rectangle((stock + 60, y + 0.13), 95, h - 0.26, fc="white", ec=INK, lw=1.0))


def material_pages(pdf, mat, bins, c, colours, names, pid_names):
    n_pages = (len(bins) + BARS_PER_PAGE - 1) // BARS_PER_PAGE
    per_page = (len(bins) + n_pages - 1) // n_pages      # spread lengths evenly over the pages
    stock_len = max(b["stock"] for b in bins)
    counts = Counter(b["stock"] for b in bins)
    stock_txt = ", ".join(f"{n} x {s / 1000:.1f} m" for s, n in sorted(counts.items()))
    for p in range(n_pages):
        chunk = bins[p * per_page:(p + 1) * per_page]
        fig = plt.figure(figsize=PAGE)
        ax = fig.add_axes([0.07, 0.10, 0.89, 0.74])
        for i, b in enumerate(chunk):
            draw_bar(ax, (BARS_PER_PAGE - 1 - i) * 1.05, b, c, colours, pid_names)
        ax.set_xlim(-420, stock_len + 260)
        ax.set_ylim(-0.4, BARS_PER_PAGE * 1.05)
        ax.axis("off")
        page_txt = f"  (page {p + 1} of {n_pages})" if n_pages > 1 else ""
        fig.text(0.07, 0.93, f"{SECTION.get(mat, mat)}: {stock_txt}{page_txt}",
                 fontsize=15, fontweight="bold", color=INK)
        note = (f"Measure from the squared end. {c.end_trim / 2:.0f} mm squaring trim at the start, "
                f"{c.kerf:.0f} mm saw kerf between pieces. Cut the longest piece first and pencil its mark on it.")
        fig.text(0.07, 0.885, note, fontsize=8.5, color=MUTED)
        if any(b["store_cut_at"] for b in chunk):
            fig.text(0.07, 0.86, "Merbau is only sold in 2.7 m. Ask the store to cut each length at the red "
                     "line so both pieces fit in the car.", fontsize=8.5, color="#B3261E")
        # legend of marks on this page
        used = OrderedDict()
        for b in chunk:
            for mark, length, _ in b["pieces"]:
                used.setdefault(mark, length)
        lx = 0.07
        for mark, length in used.items():
            fig.patches.append(Rectangle((lx, 0.045), 0.012, 0.02, transform=fig.transFigure,
                                         fc=colours[mark], ec=INK, lw=0.6))
            fig.text(lx + 0.016, 0.055, f"{mark}  {length:.0f} mm", fontsize=7.5,
                     va="center", color=INK)
            lx += 0.11
            if lx > 0.9:
                break
        pdf.savefig(fig)
        plt.close(fig)


def summary_page(pdf, bins_by_mat, parts, c):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.07, 0.90, "Cutting guide: balcony screen benches", fontsize=20, fontweight="bold", color=INK)
    fig.text(0.07, 0.86, f"{c.n_top_boards}-board bench, {sum(len(v) for v in bins_by_mat.values())} lengths of timber, "
             f"every piece drawn to scale on the pages that follow.", fontsize=10, color=MUTED)
    y = 0.78
    fig.text(0.07, y, "What to buy", fontsize=13, fontweight="bold", color=INK)
    y -= 0.045
    for mat, bins in bins_by_mat.items():
        counts = Counter(b["stock"] for b in bins)
        for s, n in sorted(counts.items()):
            fig.text(0.09, y, f"{n:>3} x  {SECTION.get(mat, mat)}, {s / 1000:.1f} m", fontsize=11, color=INK,
                     family="monospace")
            y -= 0.038
    y -= 0.03
    fig.text(0.07, y, "Pieces by mark", fontsize=13, fontweight="bold", color=INK)
    y -= 0.045
    tally = OrderedDict()
    for p in sorted(parts, key=lambda q: q.mark):
        key = (p.mark, p.material, round(p.length))
        entry = tally.setdefault(key, [[], 0])
        if p.name not in entry[0]:
            entry[0].append(p.name)
        entry[1] += 1
    col_x, col_y0, row = [0.09, 0.52], y, 0
    for (mark, mat, length), (pnames, n) in tally.items():
        name = " / ".join(pnames)
        cx = col_x[0] if row < 9 else col_x[1]
        cy = col_y0 - (row % 9) * 0.05
        fig.text(cx, cy, f"{mark}", fontsize=11, fontweight="bold", color=INK)
        fig.text(cx + 0.03, cy, f"{n:>2} x {length:>5} mm  {' '.join(SECTION.get(mat, mat).split(' ')[:3])}",
                 fontsize=9.5, color=INK, fontweight="bold")
        fig.text(cx + 0.03, cy - 0.017, name, fontsize=7.5, color=MUTED)
        row += 1
    fig.text(0.07, 0.06, "Tip: set a stop block for the repeat lengths (bearers, legs, boards) and cut all of one "
             "mark in a batch. Seal every cut end as you go.", fontsize=9, color=MUTED)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    m = S.build_model()
    c = m.cfg
    bins = S.optimise_cuts(m)
    parts = [p for p in m.parts if not p.material.startswith("LAT")]
    names = {}
    for p in parts:
        names.setdefault(p.mark, p.name.split("(")[0].strip())
    pid_names = {p.pid: p.name for p in parts}
    marks = sorted(names)
    colours = {mk: PALETTE[i % len(PALETTE)] for i, mk in enumerate(marks)}
    order = ["T90x45", "D90x22", "M42x19"]
    bins_by_mat = OrderedDict((mat, [b for b in bins if b["material"] == mat]) for mat in order)
    with PdfPages(OUT) as pdf:
        summary_page(pdf, bins_by_mat, parts, c)
        for mat, mbins in bins_by_mat.items():
            if mbins:
                material_pages(pdf, mat, mbins, c, colours, names, pid_names)
        info = pdf.infodict()
        info["Title"] = "Balcony screen benches: cutting guide"
        info["Author"] = "Luke Jamieson"
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
