"""Render the README screen section from results/screen.json."""

from __future__ import annotations

START = "<!-- screen:start -->"
END = "<!-- screen:end -->"


def render_section(res: dict) -> str:
    lines = [
        START,
        f"**Chosen stock: {res['chosen']}** (as of {res['as_of']}). Shortlist: {', '.join(res['shortlist'])}.",
        "",
        "| Ticker | Industry | Peers | Coverage | Peer set | Testability | Recognisability | Total | Eligible |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in res["candidates"]:
        s = r["scores"]
        lines.append(
            f"| {r['ticker']} | {r['industry']} | {len(r['verified_peers'])} | {s['coverage']:.2f} | "
            f"{s['peers']:.2f} | {s['testability']:.2f} | {s['recognisability']:.2f} | "
            f"{r['total']:.3f} | {'yes' if r['eligible'] else 'no: ' + r['ineligible_reason']} |"
        )
    lines += ["", f"Excluded (used by the DCF project): {', '.join(res['excluded'])}.", END]
    return "\n".join(lines)


def replace_section(readme: str, section: str) -> str:
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + section + tail
