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


M3_START = "<!-- m3:start -->"
M3_END = "<!-- m3:end -->"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render_m3(s: dict) -> str:
    v, fm, bt, sc = s["valuation"], s["factor_model"], s["backtest"], s["scenarios"]
    w = v["wacc_inputs"]
    betas = ", ".join(f"{k} {b:+.2f} (t {fm['t_stats'][k]:.1f})" for k, b in fm["betas"].items())
    lines = [
        M3_START,
        f"- **DCF (base):** {v['implied_value']:.2f} per share vs as-of price {v['price']:.2f}, so upside is **{_pct(v['upside'])}**. "
        f"WACC {_pct(w['wacc']['value'])}, stage-1 growth {_pct(v['stage1_growth'])}, terminal growth "
        f"{_pct(s['assumptions']['terminal_growth']['value'])}.",
        f"- **Reverse DCF:** the price implies {_pct(v['reverse_dcf_stage1_growth'])} stage-1 FCF growth, fading to terminal over "
        f"{s['assumptions']['fade_years']['value']} years.",
        f"- **Scenarios:** bear {sc['bear']['target']:.2f} ({_pct(sc['bear']['upside'])}), base {sc['base']['target']:.2f} "
        f"({_pct(sc['base']['upside'])}), bull {sc['bull']['target']:.2f} ({_pct(sc['bull']['upside'])}).",
        f"- **Factor betas** ({fm['window']['start']} to {fm['window']['end']}, R² {fm['r_squared']:.2f}): {betas}. "
        f"Alpha {_pct(fm['alpha_annual'])} a year (t {fm['alpha_t']:.2f}).",
        f"- **Backtest** ({bt['oos_start']} to {bt['oos_end']}, out-of-sample, net of costs), Sharpe with rf = 0: "
        f"trend strategy {bt['strategy']['sharpe_rf0']:.2f}, buy-and-hold V {bt['buy_hold_V']['sharpe_rf0']:.2f}, "
        f"SPY {bt['SPY']['sharpe_rf0']:.2f}.",
        M3_END,
    ]
    return "\n".join(lines)
