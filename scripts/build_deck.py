"""Render deck/index.html from results/summary.json and copy the committed figures (offline)."""

from pitch.deck import build

if __name__ == "__main__":
    for i, t in enumerate(build(), 1):
        print(f"{i:2d}. {t}")
