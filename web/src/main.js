import { pct, spct, usd, bn, mult, n2, hero } from "./fmt.js";
import { initPanel } from "./panel.js";
import "./app.css";

let echartsP = null;
const loadEcharts = () => (echartsP ??= import("./echarts-setup.js").then((m) => m.default));

// Design tokens, read from tokens.css.
const css = getComputedStyle(document.documentElement);
const tok = (n) => css.getPropertyValue(n).trim();
const T = {
  bg: tok("--c-surface"), fg: tok("--c-fg"), muted: tok("--c-muted"), line: tok("--c-line"), accent: tok("--c-accent"),
  neg: tok("--c-negative"), warn: tok("--c-warning"), mono: tok("--font-mono"), sans: tok("--font-sans"),
  chart: [1, 2, 3, 4, 5, 6, 7].map((i) => tok(`--chart-${i}`)),
  motion: parseInt(tok("--mo-base"), 10) || 0,
};
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const base = (extra = {}) => ({
  backgroundColor: "transparent", color: T.chart, animation: !reduced, animationDuration: T.motion,
  textStyle: { fontFamily: T.sans, color: T.fg },
  tooltip: { trigger: "axis", backgroundColor: tok("--c-surface-2"), borderColor: T.line, textStyle: { color: T.fg, fontFamily: T.mono, fontSize: 12 } },
  grid: { left: 56, right: 24, top: 40, bottom: 64 },
  ...extra,
});
const axis = (o = {}) => ({
  axisLine: { lineStyle: { color: T.line } }, axisLabel: { color: T.muted, fontFamily: T.mono, fontSize: 11 },
  splitLine: { lineStyle: { color: T.line } }, ...o,
});

const el = (id) => document.getElementById(id);
const h = (tag, attrs = {}, html = "") => Object.assign(document.createElement(tag), attrs, { innerHTML: html });

const charts = [];
// Charts are initialised only when their panel approaches the viewport (keeps first paint and main-thread work small).
const lazy = new IntersectionObserver((es) => es.forEach((e) => {
  if (!e.isIntersecting) return;
  lazy.unobserve(e.target);
  e.target._init();
}), { rootMargin: "200px" });
function mount(id, option, after) {
  const box = el(id);
  const proxy = { _c: null, _q: [], on(ev, f) { this._c ? this._c.on(ev, f) : this._q.push(["on", ev, f]); },
    setOption(o, x) { this._c ? this._c.setOption(o, x) : this._q.push(["setOption", o, x]); },
    getOption() { return this._c?.getOption(); }, resize() { this._c?.resize(); } };
  box._init = async () => {
    const echarts = await loadEcharts();
    proxy._c = echarts.init(box, null, { renderer: "canvas" });
    proxy._c.setOption(option);
    proxy._q.forEach(([m, a, b]) => proxy._c[m](a, b));
    after?.();
  };
  lazy.observe(box);
  charts.push(proxy);
  return proxy;
}
addEventListener("resize", () => charts.forEach((c) => c.resize()));

const res = await fetch(`${import.meta.env.BASE_URL}data/pitch.json`);
const D = await res.json();
const S = D.summary;
const V = S.valuation, SC = S.scenarios, BT = S.backtest, FM = S.factor_model, t = D.ticker;
const peers = S.peers;
const years = Object.keys(S.business).sort();
const y1 = years[years.length - 1];
const fy = (d) => `FY${d.slice(0, 4)}`;
const peakFcfYear = years.reduce((a, b) => (S.business[b].fcf > S.business[a].fcf ? b : a));

// ---------- hero (prerendered into index.html at build time; filled here only in dev) ----------
{
  const H = hero(S);
  if (!el("hero-stats").innerHTML.trim()) {
    el("asof").textContent = H.asof;
    el("hero-lede").innerHTML = H.lede;
    el("hero-stats").innerHTML = H.stats;
    el("hero-note").innerHTML = H.note;
  }
}

// ---------- scenario panel ----------
window.__panel = initPanel({ D, el, mount, base, axis, T, tok, reduced });

// ---------- linked state ----------
const state = { peers: new Set(["SPY"]), metric: "pe", focus: t };
const listeners = [];
const emit = () => listeners.forEach((f) => f());

// ---------- price chart: zoom + brush + linked peer filter ----------
const P = D.prices_weekly;
const dates = P[t].map((r) => r[0]);
const chipBox = el("peer-chips");
["SPY", ...peers].forEach((p) => {
  const b = h("button", { className: "chip", type: "button" }, p);
  b.setAttribute("aria-pressed", state.peers.has(p));
  b.onclick = () => { state.peers.has(p) ? state.peers.delete(p) : state.peers.add(p); emit(); };
  b.dataset.peer = p;
  chipBox.append(b);
});
function rebased(tk, i0) {
  const arr = P[tk];
  let b = null;
  for (let i = i0; i < arr.length && b == null; i++) b = arr[i][1];
  return arr.map((r) => (r[1] == null || b == null ? null : +((100 * r[1]) / b).toFixed(2)));
}
const priceChart = mount("c-price", base({
  legend: { top: 0, textStyle: { color: T.muted } },
  toolbox: { right: 8, feature: { brush: { type: ["lineX", "clear"], title: { lineX: "Brush range", clear: "Clear" } }, restore: { title: "Reset" } }, iconStyle: { borderColor: T.muted } },
  brush: { xAxisIndex: 0, brushStyle: { color: "rgba(16,185,129,.12)", borderColor: T.accent } },
  xAxis: axis({ type: "category", data: dates, boundaryGap: false }),
  yAxis: axis({ type: "value", scale: true, name: "rebased = 100", nameTextStyle: { color: T.muted } }),
  dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 16, borderColor: T.line, textStyle: { color: T.muted }, fillerColor: "rgba(16,185,129,.15)" }],
  series: [],
}));
function drawPrice() {
  const sel = ["SPY", ...peers].filter((p) => state.peers.has(p));
  priceChart.setOption({
    series: [t, ...sel].map((tk, i) => ({
      name: tk, type: "line", showSymbol: false, data: rebased(tk, 0), sampling: "lttb",
      lineStyle: { width: tk === t ? 2.2 : 1.2, color: tk === t ? T.accent : T.chart[(i % 6) + 1] },
      emphasis: { focus: "series" },
    })),
  }, { replaceMerge: ["series"] });
  chipBox.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", state.peers.has(b.dataset.peer)));
}
function windowStats(i0, i1) {
  const s = P[t].slice(i0, i1 + 1).map((r) => r[1]).filter((x) => x != null);
  const spy = P.SPY.slice(i0, i1 + 1).map((r) => r[1]).filter((x) => x != null);
  if (s.length < 3) return;
  const rets = s.slice(1).map((x, i) => x / s[i] - 1);
  const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
  const vol = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length - 1)) * Math.sqrt(52);
  let peak = s[0], dd = 0;
  s.forEach((x) => { peak = Math.max(peak, x); dd = Math.min(dd, x / peak - 1); });
  el("window-stats").innerHTML = [
    [`${dates[i0]} → ${dates[i1]}`, "window"], [spct(s[s.length - 1] / s[0] - 1), `${t} return`],
    [spct(spy[spy.length - 1] / spy[0] - 1), "SPY return"], [`${pct(vol)} · ${pct(dd)}`, `${t} weekly vol (ann.) · max DD`],
  ].map(([b, sp]) => `<div class="card"><b>${b}</b><span>${sp}</span></div>`).join("");
}
priceChart.on("datazoom", () => {
  const z = priceChart.getOption().dataZoom[0];
  windowStats(Math.round((z.start / 100) * (dates.length - 1)), Math.round((z.end / 100) * (dates.length - 1)));
});
priceChart.on("brushSelected", (e) => {
  const a = e.batch[0]?.areas?.[0];
  if (a?.coordRange) windowStats(a.coordRange[0], a.coordRange[1]);
});
listeners.push(drawPrice);
drawPrice();
windowStats(0, dates.length - 1);

// ---------- comps: metric filter + drill-down, linked to peer chips ----------
const metrics = { pe: ["P/E", mult], ev_ebitda: ["EV/EBITDA", mult], fcf_yield: ["FCF yield", (x) => pct(x)] };
const mBox = el("metric-chips");
Object.entries(metrics).forEach(([k, [lab]]) => {
  const b = h("button", { className: "chip", type: "button" }, lab);
  b.dataset.m = k;
  b.onclick = () => { state.metric = k; emit(); };
  mBox.append(b);
});
const compsChart = mount("c-comps", base({
  tooltip: { trigger: "item", backgroundColor: tok("--c-surface-2"), borderColor: T.line, textStyle: { color: T.fg, fontFamily: T.mono } },
  grid: { left: 64, right: 24, top: 16, bottom: 32 },
  xAxis: axis({ type: "value" }), yAxis: axis({ type: "category", inverse: true }), series: [],
}));
function drawComps() {
  const [lab, f] = metrics[state.metric];
  const rows = Object.entries(S.comps).filter(([, c]) => c[state.metric] != null).sort((a, b) => b[1][state.metric] - a[1][state.metric]);
  compsChart.setOption({
    yAxis: { data: rows.map((r) => r[0]) },
    tooltip: { formatter: (p) => `${p.name}: ${f(p.value)}` },
    series: [{
      type: "bar", name: lab, data: rows.map(([k, c]) => ({
        value: c[state.metric],
        itemStyle: { color: k === t ? T.accent : state.peers.has(k) ? T.chart[1] : T.line, borderRadius: 4,
          borderColor: k === state.focus ? T.fg : "transparent", borderWidth: 1 },
      })),
      markLine: { symbol: "none", lineStyle: { color: T.warn, type: "dashed" }, label: { color: T.warn, formatter: "peer median", position: "insideEndTop" },
        data: S.comps_peer_median[state.metric] == null ? [] : [{ xAxis: S.comps_peer_median[state.metric] }] },
    }],
  });
  mBox.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", b.dataset.m === state.metric));
  const c = S.comps[state.focus];
  const missing = Object.keys(S.comps).filter((k) => S.comps[k][state.metric] == null);
  el("comp-detail").innerHTML = `<h3>${state.focus}</h3><dl>
    <dt>Fiscal year</dt><dd class="num">${fy(c.fiscal_year_end)}</dd><dt>Market cap</dt><dd class="num">${bn(c.market_cap)}</dd>
    <dt>EV/EBITDA</dt><dd class="num">${mult(c.ev_ebitda)}</dd><dt>P/E</dt><dd class="num">${mult(c.pe)}</dd>
    <dt>FCF yield</dt><dd class="num">${pct(c.fcf_yield)}</dd></dl>
    <p class="note">${c.gaps ? "Gaps: " + c.gaps : "No data gaps."}${missing.length ? ` Not shown for ${lab}: ${missing.join(", ")} (gap, not estimated).` : ""}</p>
    <p class="note">Click a bar to inspect it. Peers you open here are added to the price chart.</p>`;
}
compsChart.on("click", (p) => {
  state.focus = p.name;
  if (p.name !== t) state.peers.add(p.name);
  emit();
});
listeners.push(drawComps);
drawComps();

// ---------- DCF heatmap: hover + click drill-down ----------
const G = D.dcf_grid;
const gl = G.growth.map((g) => pct(g)), wl = G.wacc.map((w) => pct(w));
const cells = G.values.map(([g, w, v]) => [G.growth.indexOf(g), G.wacc.indexOf(w), v]);
const vals = cells.map((c) => c[2]);
const dcfChart = mount("c-dcf", base({
  tooltip: { trigger: "item", backgroundColor: tok("--c-surface-2"), borderColor: T.line, textStyle: { color: T.fg, fontFamily: T.mono },
    formatter: (p) => `growth ${gl[p.value[0]]}, WACC ${wl[p.value[1]]}<br>value ${usd(p.value[2])} (${spct(p.value[2] / V.price - 1)})` },
  grid: { left: 64, right: 24, top: 16, bottom: 72 },
  xAxis: axis({ type: "category", data: gl, name: "stage-1 growth", nameLocation: "middle", nameGap: 28, splitArea: { show: false } }),
  yAxis: axis({ type: "category", data: wl, name: "WACC", splitArea: { show: false } }),
  visualMap: { type: "piecewise", orient: "horizontal", left: "center", bottom: 0, textStyle: { color: T.muted },
    pieces: [{ lt: V.price, label: "below price", color: T.neg }, { gte: V.price, lt: V.price * 1.25, label: "0 to +25%", color: tok("--c-accent-tint") },
      { gte: V.price * 1.25, label: "above +25%", color: T.accent }], min: Math.min(...vals), max: Math.max(...vals) },
  series: [{ type: "heatmap", data: cells, itemStyle: { borderColor: T.bg, borderWidth: 1 },
    emphasis: { itemStyle: { borderColor: T.fg, borderWidth: 2 } } }],
}));
function dcfDetail(gi, wi, v) {
  el("dcf-detail").innerHTML = `<h3>Selected cell</h3><dl><dt>Stage-1 growth</dt><dd class="num">${gl[gi]}</dd><dt>WACC</dt><dd class="num">${wl[wi]}</dd>
  <dt>Value</dt><dd class="num">${usd(v)}</dd><dt>vs price</dt><dd class="num">${spct(v / V.price - 1)}</dd></dl>
  <p class="note">Base case: growth ${pct(V.stage1_growth)}, WACC ${pct(V.wacc_inputs.wacc.value)} → ${usd(V.implied_value)}. The price implies
  ${pct(V.reverse_dcf_stage1_growth)} growth at the base WACC. Grid values come from the same DCF code as notebook 04.</p>`;
}
dcfChart.on("click", (p) => dcfDetail(...p.value));
const nearest = (arr, x) => arr.reduce((bi, v, i) => (Math.abs(v - x) < Math.abs(arr[bi] - x) ? i : bi), 0);
{
  const gi = nearest(G.growth, V.stage1_growth), wi = nearest(G.wacc, V.wacc_inputs.wacc.value);
  dcfDetail(gi, wi, cells.find((c) => c[0] === gi && c[1] === wi)[2]);
}

// ---------- scenarios ----------
const scenChart = mount("c-scen", base({
  tooltip: { trigger: "item", backgroundColor: tok("--c-surface-2"), borderColor: T.line, textStyle: { color: T.fg, fontFamily: T.mono },
    formatter: (p) => `${p.name}: ${usd(p.value)} (${spct(p.value / V.price - 1)})` },
  grid: { left: 64, right: 24, top: 24, bottom: 32 },
  xAxis: axis({ type: "category", data: ["bear", "base", "bull"] }), yAxis: axis({ type: "value" }),
  series: [{ type: "bar", barWidth: "50%", data: ["bear", "base", "bull"].map((k, i) => ({ value: SC[k].target,
    itemStyle: { color: [T.neg, T.muted, T.accent][i], borderRadius: [6, 6, 0, 0] } })),
    markLine: { symbol: "none", lineStyle: { color: T.warn, type: "dashed" }, label: { color: T.warn, formatter: `price ${usd(V.price)}` }, data: [{ yAxis: V.price }] } }],
}));
function scenDetail(k) {
  el("scen-detail").innerHTML = `<h3>${k[0].toUpperCase() + k.slice(1)}</h3><dl><dt>Stage-1 growth</dt><dd class="num">${pct(SC[k].stage1_growth)}</dd>
  <dt>WACC</dt><dd class="num">${pct(SC[k].wacc)}</dd><dt>Value</dt><dd class="num">${usd(SC[k].target)}</dd><dt>vs price</dt><dd class="num">${spct(SC[k].upside)}</dd></dl>
  <p class="note">The bear case is ${spct(SC.bear.upside)}, below the price. No probability weights are applied. All three cases use the 5y beta.
  The full-sample beta alone takes the base case to ${spct(S.beta_sensitivity.upside)}.</p>`;
}
scenChart.on("click", (p) => scenDetail(p.name));
scenDetail("base");

// ---------- factors ----------
const RB = D.rolling_betas;
mount("c-factors", base({
  legend: { top: 0, textStyle: { color: T.muted } },
  xAxis: axis({ type: "time" }), yAxis: axis({ type: "value" }),
  dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 16, borderColor: T.line, textStyle: { color: T.muted } }],
  series: Object.entries(RB).map(([f, s]) => ({ name: f, type: "line", showSymbol: false, data: s, emphasis: { focus: "series" } })),
}));
el("factor-note").innerHTML = `Full-sample OLS (${FM.window.start} to ${FM.window.end}), R² ${n2(FM.r_squared)}: ` +
  Object.entries(FM.betas).map(([k, b]) => `${k} <span class="num">${b >= 0 ? "+" : ""}${b.toFixed(2)}</span> (t ${FM.t_stats[k].toFixed(1)})`).join(", ") +
  `. Alpha ${pct(FM.alpha_annual)} a year (t ${FM.alpha_t.toFixed(2)}), not significant.`;

// ---------- backtest ----------
const BW = D.backtest_weekly;
const btNames = { strategy: "Trend signal", buy_hold: `Buy-and-hold ${t}`, SPY: "SPY" };
mount("c-bt", base({
  legend: { top: 0, textStyle: { color: T.muted } },
  toolbox: { right: 8, feature: { dataZoom: { title: { zoom: "Zoom", back: "Back" } }, restore: { title: "Reset" } }, iconStyle: { borderColor: T.muted } },
  xAxis: axis({ type: "time" }), yAxis: axis({ type: "log", name: "growth of $1", nameTextStyle: { color: T.muted } }),
  dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 16, borderColor: T.line, textStyle: { color: T.muted } }],
  series: Object.entries(BW).map(([k, s], i) => ({ name: btNames[k], type: "line", showSymbol: false, data: s,
    lineStyle: { color: [T.accent, T.chart[1], T.warn][i], width: k === "buy_hold" ? 2 : 1.4 } })),
}));
el("bt-table").innerHTML = `<table class="sm"><thead><tr><th>Series</th><th>CAGR</th><th>Sharpe (rf = 0)</th><th>Max DD</th></tr></thead><tbody>` +
  Object.entries(btNames).map(([k, lab]) => `<tr${k === "buy_hold" ? ' class="hl"' : ""}><td>${lab}</td><td class="num">${pct(BT[k].cagr)}</td>
  <td class="num">${n2(BT[k].sharpe_rf0)}</td><td class="num">${pct(BT[k].max_drawdown)}</td></tr>`).join("") +
  `</tbody></table><p class="note">Out-of-sample ${BT.oos_start} to ${BT.oos_end}, walk-forward window choice, next-day execution,
  ${S.assumptions.trading_cost_bps.value} bp per switch. Both the signal and buy-and-hold ${t} trail SPY on Sharpe.</p>`;

// ---------- risks + rejected ----------
const w = V.wacc_inputs;
el("risk-list").innerHTML = [
  `<b>The bear case loses money:</b> ${usd(SC.bear.target)} is ${spct(SC.bear.upside)} vs the price.`,
  `<b>The discount rate rests on a low beta:</b> the 5y beta of ${n2(w.beta.value)} gives the ${pct(w.wacc.value)} WACC. The full-sample beta of ${n2(S.beta_sensitivity.beta)}
   gives ${pct(S.beta_sensitivity.wacc)} and ${usd(S.beta_sensitivity.implied_value)} (${spct(S.beta_sensitivity.upside)}). <em>On that beta the long case disappears.</em>`,
  `<b>FCF is falling:</b> ${bn(S.business[peakFcfYear].fcf)} (${fy(peakFcfYear)}) to ${bn(S.business[y1].fcf)} (${fy(y1)}). Operating margin went from
   ${pct(S.business[peakFcfYear].operating_margin)} to ${pct(S.business[y1].operating_margin)}.`,
  `<b>The track record is weak:</b> buy-and-hold Sharpe of ${n2(BT.buy_hold.sharpe_rf0)} vs SPY's ${n2(BT.SPY.sharpe_rf0)}, and a ${pct(S.risk.full[t].max_drawdown)} max drawdown.`,
  `<b>I would drop the long</b> if the next 10-K shows FCF still falling, or a re-estimated beta pushes the base value below the price.`,
].map((x) => `<li>${x}</li>`).join("");
const C = S.comparison.COST;
el("rejected").innerHTML = `<div class="grid3"><div class="card"><b>V</b><span>First pick, archived. The base DCF was far below the price,
the bull case still showed a loss, and the price implied far more FCF growth than V's history.</span></div>
<div class="card"><b>COST ${spct(C.upside)}</b><span>DCF ${usd(C.implied_value)} vs ${usd(C.price)}. Bull ${usd(C.bull)} is still below the price,
and the price implies ${pct(C.reverse_dcf_stage1_growth)} growth.</span></div></div>`;

// ---------- navigation: section links, keyboard, swipe dots ----------
const panels = [...document.querySelectorAll(".panel")];
const toc = el("toc");
const dots = h("div", { className: "dots", ariaHidden: "true" });
panels.forEach((p) => {
  toc.append(h("a", { href: `#${p.id}` }, p.dataset.title));
  dots.append(h("i"));
});
document.body.append(dots);
const io = new IntersectionObserver((es) => es.forEach((e) => {
  if (!e.isIntersecting) return;
  const i = panels.indexOf(e.target);
  toc.querySelectorAll("a").forEach((a, j) => a.classList.toggle("on", i === j));
  dots.querySelectorAll("i").forEach((d, j) => d.classList.toggle("on", i === j));
  charts.forEach((c) => c.resize());
}), { threshold: 0.55 });
panels.forEach((p) => io.observe(p));
addEventListener("keydown", (e) => {
  if (!["ArrowRight", "ArrowLeft"].includes(e.key) || e.target.closest(".chart")) return;
  const cur = toc.querySelector("a.on");
  const i = Math.max(0, [...toc.children].indexOf(cur));
  const n = panels[Math.min(panels.length - 1, Math.max(0, i + (e.key === "ArrowRight" ? 1 : -1)))];
  n.scrollIntoView({ behavior: reduced ? "auto" : "smooth", inline: "start", block: "start" });
});
