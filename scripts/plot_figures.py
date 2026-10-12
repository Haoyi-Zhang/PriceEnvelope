#!/usr/bin/env python3
"""Render retained theorem and controller tables as Matplotlib vector PDFs.

The existing export_figures module remains the scientific table producer.
No controller, evaluator, or experiment is executed by this drawing script.
Computer Modern TTF fonts are bundled by Matplotlib; no TeX is required.
"""
from pathlib import Path
import csv
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt

ARTIFACT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ARTIFACT))
from export_figures import export



def correct_cm_unicode():
    """Keep legacy CM glyphs but write their real Unicode PDF text mappings.

    Matplotlib's CM math fonts use TeX character slots, not Unicode slots.
    Correct only ToUnicode streams; vector paths, glyph shapes, and metrics
    remain untouched. FontTools is already a Matplotlib dependency.
    """
    from fontTools import agl
    from fontTools.ttLib import TTFont
    from matplotlib.backends.backend_pdf import PdfFile

    embed = PdfFile.embedTTF
    output = PdfFile.outputStream

    def write_stream(pdf, reference, data, *args, **kwargs):
        mapping = getattr(pdf, "_cm_text_mapping", None)
        if mapping is not None and isinstance(data, bytes) and b"begincmap" in data:
            entries = [
                f"<{code:04x}> <{value.encode('utf-16-be').hex()}>"
                for code, value in sorted(mapping.items())
            ]
            groups = [
                f"{len(entries[i:i+100])} beginbfchar\n"
                + "\n".join(entries[i:i+100]) + "\nendbfchar"
                for i in range(0, len(entries), 100)
            ]
            data = (
                "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
                "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
                "/CMapName /ComputerModernUnicode def\n/CMapType 2 def\n"
                "1 begincodespacerange\n<0000> <ffff>\nendcodespacerange\n"
                + "\n".join(groups)
                + "\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
            ).encode("ascii")
        return output(pdf, reference, data, *args, **kwargs)

    def embed_font(pdf, filename, characters):
        mapping = None
        if Path(filename).name in ("cmr10.ttf", "cmmi10.ttf", "cmsy10.ttf", "cmex10.ttf"):
            with TTFont(filename) as font:
                cmap = font.getBestCmap()
                mapping = {code: agl.toUnicode(cmap[code]) for code in characters}
                if any(not value for value in mapping.values()):
                    raise ValueError("No Unicode name for a used Computer Modern glyph")
        pdf._cm_text_mapping = mapping
        try:
            return embed(pdf, filename, characters)
        finally:
            pdf._cm_text_mapping = None

    PdfFile.embedTTF = embed_font
    PdfFile.outputStream = write_stream

def configure_fonts():
    correct_cm_unicode()
    fonts = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for name in ("cmr10.ttf", "cmmi10.ttf", "cmsy10.ttf", "cmex10.ttf"):
        path = fonts / name
        if not path.is_file():
            raise FileNotFoundError(f"Matplotlib's bundled Computer Modern font: {name}")
        font_manager.fontManager.addfont(str(path))
    plt.rcParams.update({"font.family": "cmr10", "font.size": 9.96,
                         "mathtext.fontset": "cm", "axes.formatter.use_mathtext": True,
                         "axes.unicode_minus": False, "text.usetex": False,
                         "pdf.fonttype": 42, "pdf.use14corefonts": False,
                         "axes.linewidth": 1.1, "xtick.labelsize": 9.96,
                         "ytick.labelsize": 9.96})


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def save(fig, destination, name):
    target = destination / f"{name}.pdf"
    fig.savefig(target, metadata={"Creator": None, "Producer": None,
                                  "CreationDate": None, "ModDate": None})
    plt.close(fig)
    consumer = ARTIFACT.parent / "paper" / "figures"
    if consumer.is_dir():
        shutil.copyfile(target, consumer / target.name)
    print(f"Rendered vector figure: {target}")


def reserve_factors(destination):
    rows = read_rows(destination / "reserve-factors.csv")
    x = [float(row["theta"]) for row in rows]
    fig = plt.figure(figsize=(328 / 72, 190 / 72))
    # Preserve both panels and the original ~162 pt / ~84 pt axis-width ratio.
    full = fig.add_axes((39 / 328, 30 / 190, 162 / 328, 103 / 190))
    detail = fig.add_axes((242 / 328, 30 / 190, 84 / 328, 103 / 190))
    styles = ("-", "--", "-.", ":", (0, (5, 1, 1, 1)))
    labels = ("One stamp", "Two stamps", "Three stamps", "Four stamps", "Five stamps")
    for key, style, label in zip(("K21", "K22", "K23", "K24", "K25"), styles, labels):
        y = [float(row[key]) for row in rows]
        full.plot(x, y, color="black", linewidth=1.1, linestyle=style, label=label)
        if key in ("K24", "K25"):
            detail.plot(x, y, color="black", linewidth=1.1, linestyle=style)
    full.set(xlim=(0, 0.95), ylim=(1, 4), xlabel=r"Relative radius $\theta$",
             ylabel=r"Sharp factor $K_{2,r}$")
    full.set_xticks((0, 0.2, 0.4, 0.6, 0.8), ("0", "0.2", "0.4", "0.6", "0.8"))
    full.set_yticks((1, 1.5, 2, 2.5, 3, 3.5, 4), ("1", "1.5", "2", "2.5", "3", "3.5", "4"))
    detail.set(xlim=(0, 0.95), ylim=(1, 1.21), xlabel=r"$\theta$")
    detail.set_xticks((0, 0.4, 0.8), ("0", "0.4", "0.8"))
    detail.set_yticks((1, 1.1, 1.2), ("1", "1.1", "1.2"))
    full.set_title("(a) All stamps", fontsize=8.97, pad=8)
    detail.set_title("(b) Low-factor detail", fontsize=8.97, pad=8)
    for ax in (full, detail):
        ax.tick_params(direction="out", width=1.1, length=3, pad=3)
    # A shared top legend keeps all five original meanings without curve overlap.
    fig.legend(*full.get_legend_handles_labels(), loc="upper right", ncol=3,
               bbox_to_anchor=(1, 1.01), frameon=False, fontsize=8.97,
               handlelength=1.8, columnspacing=1.0, labelspacing=0.3)
    save(fig, destination, "reserve-factors")


def controller_errors(destination):
    rows = read_rows(destination / "controller-errors.csv")
    if len(rows) != 64:
        raise ValueError("Expected the retained 64-slot controller trajectory")
    # Retain the existing controller PDF's 324 x 128 pt physical size and scale.
    fig = plt.figure(figsize=(324 / 72, 128 / 72))
    ax = fig.add_axes((46 / 324, 28 / 128, 271 / 324, 91 / 128))
    for key, style, label in (("constant", "-", "Fixed grid"),
                              ("vanishing", "--", "Refining grid")):
        ax.plot([float(row["slot"]) for row in rows],
                [float(row[key]) for row in rows], color="black",
                linewidth=1.1, linestyle=style, label=label)
    ax.set(xlim=(0, 64), ylim=(1e-6, 0.2), yscale="log",
           xlabel="Logical update slot", ylabel="Virtual price error")
    ax.set_xticks((0, 16, 32, 48, 64))
    ax.set_yticks((1e-5, 1e-3, 1e-1), (r"$10^{-5}$", r"$10^{-3}$", r"$10^{-1}$"))
    ax.minorticks_off()
    # The previous controller renderer used boxed axes and no tick strokes/grid.
    ax.tick_params(length=0, pad=3)
    ax.legend(loc="upper right", frameon=False, borderaxespad=0.3,
              handlelength=1.8, handletextpad=0.4, labelspacing=0.25)
    save(fig, destination, "controller-errors")


def main():
    configure_fonts()
    destination = ARTIFACT / "figures"
    # Reuse the rational exporter and the retained control_pipeline.json.
    export(destination)
    for name in ("reserve-factors.csv", "controller-errors.csv"):
        retained = ARTIFACT / "results" / name
        if read_rows(destination / name) != read_rows(retained):
            raise ValueError(f"Export differs from the retained scientific table: {name}")
        consumer = ARTIFACT.parent / "paper" / "figures"
        if consumer.is_dir():
            shutil.copyfile(destination / name, consumer / name)
    reserve_factors(destination)
    controller_errors(destination)


if __name__ == "__main__":
    main()
