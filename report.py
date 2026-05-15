import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

MANUAL_PATH = Path(sys.argv[sys.argv.index("--manual") + 1]) if "--manual" in sys.argv else Path.home() / "riscv-isa-manual"
PDF_OUT = ROOT / "riscv-extensions-landscape.pdf"


def load_json(name):
    return json.loads((ROOT / name).read_text())


def normalize_insn(name):
    return re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9_]", "_", name.replace(".", "_").replace("-", "_"))).strip("_").upper()


def scan_manual_instructions():
    src = MANUAL_PATH / "src"
    counts = Counter()
    if not src.exists():
        return counts
    pattern = re.compile(r"\binsn:([a-zA-Z0-9_.-]+)(?:\[[^\]]*\])?")
    for file in src.rglob("*.adoc"):
        for match in pattern.finditer(file.read_text(errors="ignore")):
            insn = normalize_insn(match.group(1))
            if insn:
                counts[insn] += 1
    return counts


def style_axis(ax, title, ylabel="Count"):
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", pad=12)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color="#d8dee6", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def bar(ax, labels, values, title, colors=None):
    colors = colors or ["#2f6f9f"] * len(labels)
    bars = ax.bar(labels, values, color=colors, width=0.62)
    style_axis(ax, title)
    ax.tick_params(axis="x", labelrotation=18)
    ymax = max(values) if values else 1
    ax.set_ylim(0, ymax * 1.18)
    for rect, value in zip(bars, values):
        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + ymax * 0.025, str(value), ha="center", va="bottom", fontsize=10)


def horizontal_bar(ax, rows, title, color="#2f6f9f"):
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    y = range(len(rows))
    ax.barh(y, values, color=color)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    style_axis(ax, title)
    ax.set_xlabel("Instruction count")
    ax.set_ylabel("")
    xmax = max(values) if values else 1
    ax.set_xlim(0, xmax * 1.15)
    for idx, value in enumerate(values):
        ax.text(value + xmax * 0.015, idx, str(value), va="center", fontsize=9)


def build_report():
    instr = load_json("instr_dict.json")
    output = load_json("output.json")
    compare = load_json("compare_output.json")
    manual_counts = scan_manual_instructions()

    landscape_insns = {normalize_insn(name) for name in instr}
    manual_insns = set(manual_counts)
    common_insns = landscape_insns & manual_insns

    ext_meta = compare["meta"]
    top_extensions = sorted(
        (
            (name, data["uniqueInstructionCount"])
            for name, data in output["normalizedExtensions"].items()
            if data["kind"] == "extension"
        ),
        key=lambda item: item[1],
        reverse=True,
    )[:15]

    with PdfPages(PDF_OUT) as pdf:
        fig, axes = plt.subplots(2, 2, figsize=(11.69, 8.27))
        fig.suptitle("RISC-V Extensions Landscape vs ISA Manual", fontsize=20, fontweight="bold", x=0.06, ha="left")
        fig.text(
            0.06,
            0.925,
            "Counts only. 'Landscape' is instr_dict.json/output.json; manual instruction count is unique insn:* references in the local ISA manual.",
            fontsize=10,
            color="#52616f",
        )

        bar(
            axes[0][0],
            ["Matched", "Landscape only", "Manual only"],
            [ext_meta["matchedCount"], ext_meta["jsonOnlyCount"], ext_meta["manualOnlyCount"]],
            "Extension Coverage",
            ["#2f6f9f", "#d08c2f", "#6b7c93"],
        )
        bar(
            axes[0][1],
            ["Canonical", "Composite", "Pseudo"],
            [output["meta"]["totalExtensions"], output["meta"]["totalCompositeTags"], output["meta"]["totalPseudoTags"]],
            "Landscape Extension Categories",
            ["#2f6f9f", "#8266b5", "#8a97a5"],
        )
        bar(
            axes[1][0],
            ["Landscape", "Manual", "Common"],
            [len(landscape_insns), len(manual_insns), len(common_insns)],
            "Instruction Name Coverage",
            ["#2f6f9f", "#6b7c93", "#3f8f58"],
        )
        horizontal_bar(
            axes[1][1],
            top_extensions,
            "Top Landscape Extensions by Instruction Count",
            "#2f6f9f",
        )

        fig.tight_layout(rect=[0.04, 0.03, 0.98, 0.89])
        pdf.savefig(fig)
        plt.close(fig)

    print(f"Wrote {PDF_OUT}")


if __name__ == "__main__":
    build_report()
