// Number formatting shared by the runtime app and the build-time prerender (vite.config.js).
export const pct = (x, d = 1) => (x == null ? "n/a" : `${(x * 100).toFixed(d)}%`);
export const spct = (x) => (x == null ? "n/a" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)}%`);
export const usd = (x) => (x == null ? "n/a" : `$${x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
export const bn = (x) => (x == null ? "n/a" : `$${(x / 1e9).toFixed(1)}B`);
export const mult = (x) => (x == null ? "n/a" : `${x.toFixed(1)}x`);
export const n2 = (x) => (x == null ? "n/a" : x.toFixed(2));

export function hero(S) {
  const V = S.valuation, SC = S.scenarios, B = S.beta_sensitivity;
  return {
    asof: `· as of ${S.as_of}`,
    lede: `Base-case DCF value <span class="num">${usd(V.implied_value)}</span> per share against an as-of price of
<span class="num">${usd(V.price)}</span>: <span class="num">${spct(V.upside)}</span>.`,
    stats: ["bear", "base", "bull"].map((k) =>
      `<div class="stat${k === "base" ? " hl" : ""}"><b>${usd(SC[k].target)}</b><span>${k} (${spct(SC[k].upside)})</span></div>`).join(""),
    note: `The bear case is <b>${spct(SC.bear.upside)}</b>. The ${pct(V.wacc_inputs.wacc.value)} WACC rests on a 5y beta of
${n2(V.wacc_inputs.beta.value)}. With the full-sample beta of ${n2(B.beta)}, the value is ${usd(B.implied_value)}
(${spct(B.upside)}). Intrinsic-value estimate, not a dated price target.`,
  };
}
