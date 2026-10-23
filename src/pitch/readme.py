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


def _pitch_bullets(s: dict) -> list[str]:
    v, fm, bt, sc = s["valuation"], s["factor_model"], s["backtest"], s["scenarios"]
    w = v["wacc_inputs"]
    t = s["ticker"]
    betas = ", ".join(f"{k} {b:+.2f} (t {fm['t_stats'][k]:.1f})" for k, b in fm["betas"].items())
    return [
        f"- **DCF (base):** {v['implied_value']:.2f} per share vs as-of price {v['price']:.2f}, so upside is **{_pct(v['upside'])}**. "
        f"WACC {_pct(w['wacc']['value'])}, stage-1 growth {_pct(v['stage1_growth'])}, terminal growth "
        f"{_pct(s['assumptions']['terminal_growth']['value'])}.",
        f"- **Reverse DCF:** the price implies {_pct(v['reverse_dcf_stage1_growth'])} stage-1 FCF growth, fading to terminal "
        f"over {s['assumptions']['fade_years']['value']} years.",
        f"- **Scenarios:** bear {sc['bear']['target']:.2f} ({_pct(sc['bear']['upside'])}), base {sc['base']['target']:.2f} "
        f"({_pct(sc['base']['upside'])}), bull {sc['bull']['target']:.2f} ({_pct(sc['bull']['upside'])}).",
        f"- **Factor betas** ({fm['window']['start']} to {fm['window']['end']}, R² {fm['r_squared']:.2f}): {betas}. "
        f"Alpha {_pct(fm['alpha_annual'])} a year (t {fm['alpha_t']:.2f}).",
        f"- **Backtest** ({bt['oos_start']} to {bt['oos_end']}, out-of-sample, net of costs), Sharpe with rf = 0: "
        f"trend strategy {bt['strategy']['sharpe_rf0']:.2f}, buy-and-hold {t} {bt['buy_hold']['sharpe_rf0']:.2f}, "
        f"SPY {bt['SPY']['sharpe_rf0']:.2f}.",
    ]


def render_m3(files: dict) -> str:
    active = files["results/summary.json"]
    lines = [
        M3_START,
        "| Ticker | Price | DCF value | Upside | Bear | Base | Bull | WACC | Price-implied growth | Sharpe B&H | Supports long? |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t, c in active["comparison"].items():
        lines.append(
            f"| {t} | {c['price']:.2f} | {c['implied_value']:.2f} | {_pct(c['upside'])} | {c['bear']:.2f} | {c['base']:.2f} | "
            f"{c['bull']:.2f} | {_pct(c['wacc'])} | {_pct(c['reverse_dcf_stage1_growth'])} | {c['sharpe_buy_hold']:.2f} | "
            f"{'yes (base case)' if c['supports_long'] else 'no'} |"
        )
    lines += ["", f"### {active['ticker']} (active pitch)", *_pitch_bullets(active)]
    for t, path in active["compared_with"].items():
        lines += ["", f"### {t} (compared, same methods; [`{path}`]({path}))", *_pitch_bullets(files[path])]
    for t, info in active["archived"].items():
        lines += ["", f"### {t} (archived first pick; [`{info['summary_file']}`]({info['summary_file']}))", f"*{info['reason']}*"]
        lines += _pitch_bullets(files[info["summary_file"]])
    lines.append(M3_END)
    return "\n".join(lines)


PITCH_START = "<!-- pitch:start -->"
PITCH_END = "<!-- pitch:end -->"


def _bn(x: float) -> str:
    return f"${x / 1e9:.1f}B"


def render_pitch(s: dict) -> str:
    """Headline numbers and honest risks for the employer-facing README, all from results/summary.json."""
    v, sc, bt, bs, fm = s["valuation"], s["scenarios"], s["backtest"], s["beta_sensitivity"], s["factor_model"]
    w = v["wacc_inputs"]
    t = s["ticker"]
    years = sorted(s["business"])
    peak = max(years, key=lambda y: s["business"][y]["fcf"])
    last = years[-1]
    rk = s["risk"]["full"]
    rec = "Long" if s["verdict"]["supports_long"] else "No position"
    lines = [
        PITCH_START,
        f"**{rec} {t}** at an as-of price of **${v['price']:.2f}** ({s['as_of']}). "
        f"Base-case DCF value **${v['implied_value']:.2f}** ({_pct(v['upside'])} upside); "
        f"target range ${sc['bear']['target']:.2f} to ${sc['bull']['target']:.2f}.",
        "",
        "| | Bear | Base | Bull |",
        "|---|---|---|---|",
        f"| Stage-1 FCF growth | {_pct(sc['bear']['stage1_growth'])} | {_pct(sc['base']['stage1_growth'])} | {_pct(sc['bull']['stage1_growth'])} |",
        f"| WACC | {sc['bear']['wacc'] * 100:.2f}% | {sc['base']['wacc'] * 100:.2f}% | {sc['bull']['wacc'] * 100:.2f}% |",
        f"| Value per share | ${sc['bear']['target']:.2f} | ${sc['base']['target']:.2f} | ${sc['bull']['target']:.2f} |",
        f"| vs price | {_pct(sc['bear']['upside'])} | {_pct(sc['base']['upside'])} | {_pct(sc['bull']['upside'])} |",
        "",
        f"- **What the price implies:** a reverse DCF says the market prices in {_pct(v['reverse_dcf_stage1_growth'])} stage-1 FCF growth, "
        f"against {_pct(v['stage1_growth'])} in the base case (the median of the stock's rolling 5-year FCF CAGRs).",
        f"- **Discount rate:** CAPM with rf {_pct(w['risk_free']['value'])}, 5-year beta {w['beta']['value']:.2f}, "
        f"ERP {_pct(w['equity_risk_premium']['value'])}, giving WACC {w['wacc']['value'] * 100:.2f}%. "
        f"Terminal growth {_pct(s['assumptions']['terminal_growth']['value'])}, {s['assumptions']['fade_years']['value']}-year fade.",
        f"- **Backtest** ({bt['oos_start']} to {bt['oos_end']}, walk-forward, out-of-sample, net of "
        f"{s['assumptions']['trading_cost_bps']['value']} bp costs), Sharpe with rf = 0: trend signal {bt['strategy']['sharpe_rf0']:.2f}, "
        f"buy-and-hold {bt['buy_hold']['sharpe_rf0']:.2f}, {s['benchmark']} {bt['SPY']['sharpe_rf0']:.2f}.",
        "",
        "### Honest risks",
        "",
        f"- **The call depends on beta.** The 5-year beta of {w['beta']['value']:.2f} gives WACC {w['wacc']['value'] * 100:.2f}% and "
        f"${v['implied_value']:.2f}. The full-sample beta ({bs['beta']:.2f}) gives WACC {bs['wacc'] * 100:.2f}% and "
        f"**${bs['implied_value']:.2f} ({_pct(bs['upside'])})**, below the price. The low recent beta reflects a period when "
        f"{t}'s own news dominated its returns (factor-model R² {fm['r_squared']:.2f}).",
        f"- **The bear case is below the price** (${sc['bear']['target']:.2f}, {_pct(sc['bear']['upside'])}): this is a long with "
        "downside, not a margin of safety in every scenario.",
        f"- **FCF is falling:** {_bn(s['business'][peak]['fcf'])} in FY{peak[:4]} to {_bn(s['business'][last]['fcf'])} in FY{last[:4]}, "
        "while base-case growth uses the long-run median.",
        f"- **Margins:** operating margin {_pct(s['business'][last]['operating_margin'])} in FY{last[:4]} vs "
        f"{_pct(s['business'][peak]['operating_margin'])} in FY{peak[:4]}. The upside needs a recovery that is not yet in the numbers.",
        f"- **Risk and signals trail the market:** max drawdown {_pct(rk[t]['max_drawdown'])} vs {_pct(rk['SPY']['max_drawdown'])} for "
        f"{s['benchmark']} since {s['risk']['full']['start']}; both the trend signal and buy-and-hold trail {s['benchmark']} on Sharpe.",
        PITCH_END,
    ]
    return "\n".join(lines)
