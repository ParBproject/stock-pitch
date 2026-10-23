// M7 scenario panel. All values are looked up in a surface precomputed by the Python DCF (src/pitch/webdata.py);
// nothing is estimated in the browser. Defaults reproduce results/summary.json exactly (pinned by tests).
import { pct, spct, usd, n2 } from "./fmt.js";

export function initPanel({ D, el, mount, base, axis, T, tok, reduced }) {
  const P = D.scenario_panel;
  const S = D.summary;
  const gIdx = (g) => P.growth.indexOf(g);
  const wIdx = (w) => P.wacc.indexOf(w);
  const state = { beta: "5y", gi: gIdx(P.defaults.growth), wi: wIdx(P.defaults.beta["5y"].wacc), preset: "base" };

  const gIn = el("sp-g"), wIn = el("sp-w");
  gIn.max = P.growth.length - 1;
  wIn.max = P.wacc.length - 1;

  // beta choice
  const seg = el("sp-beta");
  Object.entries(P.defaults.beta).forEach(([k, b]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("role", "radio");
    btn.dataset.k = k;
    btn.innerHTML = `${b.label}<br><span class="num">β ${n2(b.beta)} · WACC ${pct(b.wacc)}</span>`;
    btn.onclick = () => { state.beta = k; state.wi = wIdx(b.wacc); state.preset = k === "5y" ? "base" : null; render(); };
    seg.append(btn);
  });
  // presets
  const pre = el("sp-presets");
  [["bear", "Bear"], ["base", "Base"], ["bull", "Bull"], ["reset", "Reset"]].forEach(([k, lab]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = lab;
    btn.dataset.k = k;
    btn.onclick = () => {
      const s = P.scenarios[k === "reset" ? "base" : k];
      state.beta = "5y";
      state.gi = gIdx(s.growth);
      state.wi = wIdx(s.wacc);
      state.preset = k === "reset" ? "base" : k;
      render();
    };
    pre.append(btn);
  });
  gIn.oninput = () => { state.gi = +gIn.value; state.preset = null; render(); };
  wIn.oninput = () => { state.wi = +wIn.value; state.preset = null; render(); };
  el("sp-help").innerHTML = `Every value comes from the notebook's DCF, precomputed over ${P.growth.length} growth × ${P.wacc.length} WACC points.
  Terminal growth is fixed at ${pct(P.terminal_growth)}. Presets match the bear, base and bull cases in <code>summary.json</code>.`;

  // bottom sheet (mobile)
  const sheet = el("sp-sheet"), handle = el("sp-handle");
  const setSheet = (open) => { sheet.classList.toggle("collapsed", !open); handle.setAttribute("aria-expanded", String(open)); };
  if (matchMedia("(max-width: 720px)").matches) setSheet(false);
  handle.onclick = () => {
    const c = sheet.classList.toggle("collapsed");
    handle.setAttribute("aria-expanded", String(!c));
  };
  new IntersectionObserver((es) => es.forEach((e) => document.body.classList.toggle("sp-active", e.isIntersecting)),
    { threshold: 0.4 }).observe(el("p-panel"));

  // animated target
  const out = el("sp-value");
  let shown = null, raf = 0;
  const dur = parseInt(tok("--mo-base"), 10) || 0;
  function animateTo(v) {
    cancelAnimationFrame(raf);
    if (reduced || shown == null || dur === 0) { shown = v; out.textContent = usd(v); return; }
    const from = shown, t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = 1 - (1 - k) ** 3;
      shown = from + (v - from) * e;
      out.textContent = usd(k === 1 ? v : shown);
      if (k < 1) raf = requestAnimationFrame(step); else shown = v;
    };
    raf = requestAnimationFrame(step);
  }

  // fan chart: FCF history + bear..bull band + base + selected path
  const mobile = matchMedia("(max-width: 720px)").matches;
  const hist = D.fcf_history.slice(-6).map(([d, v]) => [String(+d.slice(0, 4)), +(v / 1e9).toFixed(3)]);
  const yrs = [...hist.map((h) => h[0]), ...P.years.map(String)];
  const pathOf = (g) => P.fcf_paths_bn[gIdx(g)];
  const bear = pathOf(P.scenarios.bear.growth), bull = pathOf(P.scenarios.bull.growth), basep = pathOf(P.scenarios.base.growth);
  const padBand = (arr) => [...hist.slice(0, -1).map(() => null), 0, ...arr];
  const pad = (arr) => [...hist.slice(0, -1).map(() => null), hist[hist.length - 1][1], ...arr];
  const fan = mount("c-fan", base({
    legend: { top: 0, textStyle: { color: T.muted }, data: ["History", "Bear to bull", "Base", "Selected"] },
    color: [T.fg, T.muted, "rgba(16,185,129,.35)", T.muted, T.accent],
    grid: { left: 48, right: 16, top: mobile ? 56 : 36, bottom: 32 },
    tooltip: { trigger: "axis", backgroundColor: tok("--c-surface-2"), borderColor: T.line, textStyle: { color: T.fg, fontFamily: T.mono },
      valueFormatter: (v) => (v == null ? "" : `$${(+v).toFixed(1)}B`) },
    xAxis: axis({ type: "category", data: yrs, boundaryGap: false }),
    yAxis: axis({ type: "value", name: "FCF, $B", nameTextStyle: { color: T.muted } }),
    series: [
      { name: "History", type: "line", data: [...hist.map((h) => h[1]), ...P.years.map(() => null)], lineStyle: { color: T.fg, width: 2 }, symbolSize: 5 },
      { name: "bear floor", type: "line", stack: "band", data: pad(bear), lineStyle: { opacity: 0 }, symbol: "none", tooltip: { show: false } },
      { name: "Bear to bull", type: "line", stack: "band", data: padBand(bull.map((b, i) => +(b - bear[i]).toFixed(3))), lineStyle: { opacity: 0 },
        symbol: "none", areaStyle: { color: "rgba(16,185,129,.16)" }, tooltip: { show: false } },
      { name: "Base", type: "line", data: pad(basep), lineStyle: { color: T.muted, type: "dashed" }, symbol: "none" },
      { name: "Selected", type: "line", data: pad(pathOf(P.growth[state.gi])), lineStyle: { color: T.accent, width: 2.4 }, symbol: "none" },
    ],
  }));

  // sensitivity heatmap with the selection marked
  const cells = [];
  P.growth.forEach((g, i) => P.wacc.forEach((w, j) => cells.push([i, j, P.values[i][j]])));
  const sens = mount("c-sens", base({
    grid: { left: 56, right: 16, top: 16, bottom: 64 },
    tooltip: { trigger: "item", backgroundColor: tok("--c-surface-2"), borderColor: T.line, textStyle: { color: T.fg, fontFamily: T.mono },
      formatter: (p) => `growth ${pct(P.growth[p.value[0]])}, WACC ${pct(P.wacc[p.value[1]], 2)}<br>${usd(p.value[2])} (${spct(p.value[2] / P.price - 1)})` },
    xAxis: axis({ type: "category", data: P.growth.map((g) => pct(g)), name: "stage-1 growth", nameLocation: "middle", nameGap: 26 }),
    yAxis: axis({ type: "category", data: P.wacc.map((w) => pct(w, 2)) }),
    visualMap: { type: "piecewise", orient: "horizontal", left: "center", bottom: 0, textStyle: { color: T.muted },
      pieces: [{ lt: P.price, label: "below price", color: T.neg }, { gte: P.price, lt: P.price * 1.25, label: "0 to +25%", color: tok("--c-accent-tint") },
        { gte: P.price * 1.25, label: "above +25%", color: T.accent }], seriesIndex: 0 },
    series: [
      { type: "heatmap", data: cells, progressive: 0 },
      { type: "scatter", data: [[state.gi, state.wi]], symbol: "rect", symbolSize: 14, itemStyle: { color: "transparent", borderColor: T.fg, borderWidth: 2 },
        tooltip: { show: false }, z: 10 },
    ],
  }));
  sens.on("click", (p) => { if (p.seriesIndex === 0) { state.gi = p.value[0]; state.wi = p.value[1]; state.preset = null; render(); } });

  function render() {
    const g = P.growth[state.gi], w = P.wacc[state.wi], v = P.values[state.gi][state.wi];
    gIn.value = state.gi; wIn.value = state.wi;
    el("sp-g-out").textContent = pct(g);
    el("sp-w-out").textContent = pct(w, 2);
    el("sp-handle-sum").textContent = `growth ${pct(g)} · WACC ${pct(w, 2)} · ${state.beta === "5y" ? "5y" : "full-sample"} beta`;
    animateTo(v);
    const up = v / P.price - 1;
    const badge = el("sp-up");
    badge.textContent = spct(up);
    badge.className = up >= 0 ? "badge" : "badge neg";
    el("sp-vs").textContent = `vs as-of price ${usd(P.price)}`;
    seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.k === state.beta)));
    pre.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === state.preset)));
    fan.setOption({ series: [{}, {}, {}, {}, { data: pad(pathOf(g)) }] });
    sens.setOption({ series: [{}, { data: [[state.gi, state.wi]] }] });
  }
  render();
  return { state, P, S };
}
