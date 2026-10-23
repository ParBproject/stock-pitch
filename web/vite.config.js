import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import { hero } from "./src/fmt.js";

// Prerender the hero from the same data and formatter the app uses, so first paint needs no JavaScript.
function prerenderHero() {
  return {
    name: "prerender-hero",
    transformIndexHtml(html) {
      const S = JSON.parse(readFileSync(new URL("./public/data/pitch.json", import.meta.url))).summary;
      const H = hero(S);
      return html
        .replace('<span class="muted" id="asof"></span>', `<span class="muted" id="asof">${H.asof}</span>`)
        .replace('<p class="lede" id="hero-lede"></p>', `<p class="lede" id="hero-lede">${H.lede}</p>`)
        .replace('<div class="stats" id="hero-stats"></div>', `<div class="stats" id="hero-stats">${H.stats}</div>`)
        .replace('<p class="note" id="hero-note"></p>', `<p class="note" id="hero-note">${H.note}</p>`);
    },
  };
}

// Served from https://parbproject.github.io/stock-pitch/
export default defineConfig({
  base: "/stock-pitch/",
  plugins: [prerenderHero()],
  build: { target: "es2022", outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 900 },
});
