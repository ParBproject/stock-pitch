"""Dark chart theme shared by every figure (site palette: #06080b background, #10B981 accent)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BG, FG, GRID, ACCENT = "#06080b", "#e5e7eb", "#1f2937", "#10B981"
PALETTE = [ACCENT, "#60a5fa", "#f59e0b", "#f472b6", "#a78bfa", "#94a3b8", "#f87171"]
FIG_DIR = Path(__file__).resolve().parents[2] / "figures"


def apply_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "axes.edgecolor": GRID,
            "axes.labelcolor": FG,
            "text.color": FG,
            "xtick.color": FG,
            "ytick.color": FG,
            "grid.color": GRID,
            "axes.grid": True,
            "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
            "font.size": 10,
            "figure.dpi": 110,
        }
    )


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    return path
