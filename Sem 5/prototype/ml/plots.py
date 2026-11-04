"""Shared chart styling for report figures (light, print-oriented)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#ffffff"

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING_NEG = "#2a78d6"   # pushes towards legitimate
DIVERGING_POS = "#e34948"   # pushes towards fraud
STATUS = {"AUTO_APPROVE": "#0ca30c", "MANUAL_REVIEW": "#fab219", "AUTO_BLOCK": "#d03b3b"}


def apply_style():
    plt.rcParams.update({
        "font.family": "Times New Roman",
        "font.size": 11,
        "axes.edgecolor": TEXT_2,
        "axes.labelcolor": TEXT,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXT,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "legend.frameon": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
