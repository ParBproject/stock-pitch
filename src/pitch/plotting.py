"""Chart theme for every figure, read from design/tokens.json (Inter text, tabular JetBrains Mono ticks)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from pitch.design import FONT_DIR, TOKENS  # noqa: E402

C = TOKENS["color"]
BG, FG, GRID, ACCENT, MUTED = C["bg"], C["fg"], C["line"], C["accent"], C["muted"]
PALETTE = TOKENS["chart"]
FIG_DIR = Path(__file__).resolve().parents[2] / "figures"
SCALE = TOKENS["font"]["scale"]


def apply_theme() -> None:
    for f in ("Inter.ttf", "JetBrainsMono.ttf"):
        font_manager.fontManager.addfont(str(FONT_DIR / f))
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "axes.edgecolor": GRID,
            "axes.labelcolor": MUTED,
            "axes.titlecolor": FG,
            "axes.titlesize": SCALE[3] * 0.75,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "text.color": FG,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.grid": True,
            "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
            "font.family": TOKENS["font"]["sans"],
            "font.size": SCALE[1] * 0.72,
            "legend.frameon": False,
            "lines.linewidth": 1.6,
            "figure.dpi": 110,
        }
    )


def save(fig, name: str) -> Path:
    for ax in fig.axes:
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_fontfamily(TOKENS["font"]["mono"])
    path = FIG_DIR / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    return path
