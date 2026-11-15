// Story charts with Plotly.js (loaded only when a chart scrolls near). Same template as the app's Plotly theme.
import Plotly from "plotly.js-dist-min";

const SUN = "#F4B860", EARTH = "#6FB1FF", TERRAIN = "#8C8A86", ALARM = "#FF5C5C", INK = "#EDEAE2", DIM = "#A3A09A";
const FONT = { family: "Geist Variable, system-ui, sans-serif", color: INK, size: 12 };
const axis = { gridcolor: "rgba(232,228,216,.07)", zerolinecolor: "rgba(232,228,216,.22)", linecolor: "rgba(232,228,216,.18)",
  tickfont: { family: "Geist Mono Variable, ui-monospace, monospace", color: DIM, size: 11 }, title: { font: { color: DIM, size: 12 } } };
const base = (extra = {}) => ({
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: FONT, margin: { l: 56, r: 16, t: 24, b: 44 },
  xaxis: { ...axis }, yaxis: { ...axis }, showlegend: false, hoverlabel: { bgcolor: "#0B0D17", bordercolor: "rgba(244,184,96,.4)", font: FONT },
  ...extra,
});
const cfg = { displaylogo: false, responsive: true, displayModeBar: "hover", modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines", "hoverClosestCartesian", "hoverCompareCartesian"] };

function earth(el, d) {
  const e = d.earth;
  const t = e.t;
  const hidden = e.earth_el.map((v, i) => (e.visible[i] ? null : v));
  Plotly.newPlot(el, [
    { x: t, y: e.earth_h, type: "scatter", mode: "lines", line: { color: TERRAIN, width: 1 }, fill: "tozeroy",
      fillcolor: "rgba(140,138,134,.32)", name: "Terrain in Earth's direction", hovertemplate: "terrain %{y:.1f}°<extra></extra>" },
    { x: t, y: e.earth_el, type: "scatter", mode: "lines", line: { color: EARTH, width: 2.5 }, name: "Earth",
      hovertemplate: "%{x|%-d %b %H:%M} UTC<br>Earth %{y:.1f}°<extra></extra>" },
    { x: t, y: hidden, type: "scatter", mode: "lines", line: { color: ALARM, width: 3 }, name: "Hidden",
      hovertemplate: "Earth hidden<extra></extra>" },
  ], base({ yaxis: { ...axis, title: "Elevation (°)", range: [-8, 12] }, xaxis: { ...axis, tickformat: "%-d %b" } }), cfg);
}

function ridge(el, d) {
  const r = d.ridge;
  const circle = { type: "circle", x0: -r.radius_m, x1: r.radius_m, y0: -r.radius_m, y1: r.radius_m,
    line: { color: INK, width: 1.5, dash: "dot" } };
  Plotly.newPlot(el, [
    { type: "heatmap", x: r.x, y: r.y, z: r.pct, zmin: 0, zmax: 70,
      colorscale: [[0, "#05060B"], [0.2, "#1E1A24"], [0.45, "#5A4030"], [0.7, "#B9803F"], [0.9, SUN], [1, "#FFE9C2"]],
      colorbar: { title: { text: "% of time lit", side: "right" }, thickness: 10, tickfont: { color: DIM } },
      hovertemplate: "%{x} m, %{y} m<br>sunlit %{z:.1f}% of 18.6 years<extra>NASA</extra>" },
    { x: [0], y: [0], mode: "markers", marker: { symbol: "diamond", size: 13, color: SUN, line: { color: "#05060B", width: 1.5 } },
      hovertemplate: `Blue Moon MK1 target<br>NASA ${r.nasa_here}%, ours ${r.ours}%<extra></extra>` },
  ], base({ shapes: [circle], xaxis: { ...axis, title: "metres", scaleanchor: "y", constrain: "domain" },
    yaxis: { ...axis, title: "metres" }, margin: { l: 56, r: 10, t: 16, b: 44 } }), cfg);
}

function athena(el, d) {
  const a = d.athena;
  Plotly.newPlot(el, [
    { type: "heatmap", x: a.relief.x, y: a.relief.y, z: a.relief.shade, colorscale: [[0, "#07080E"], [1, "#D9D3C4"]],
      showscale: false, hoverinfo: "skip" },
    { x: a.points.x, y: a.points.y, mode: "markers", marker: { size: 5, color: "rgba(236,233,247,.55)" }, hoverinfo: "skip" },
    { x: [a.target[0]], y: [a.target[1]], mode: "markers+text", text: ["Target"], textposition: "top center",
      marker: { symbol: "diamond", size: 15, color: EARTH, line: { color: "#05060B", width: 1.5 } }, textfont: { color: INK },
      hovertemplate: "Target (LROC, two decimals)<extra></extra>" },
    { x: [0], y: [0], mode: "markers+text", text: ["Athena"], textposition: "bottom center",
      marker: { symbol: "diamond", size: 15, color: ALARM, line: { color: "#05060B", width: 1.5 } }, textfont: { color: INK },
      hovertemplate: "Athena's resting spot (LROC)<extra></extra>" },
  ], base({
    shapes: [{ type: "circle", x0: -a.crater_m / 2, x1: a.crater_m / 2, y0: -a.crater_m / 2, y1: a.crater_m / 2, line: { color: ALARM, width: 2 } },
      { type: "line", x0: 0, y0: 0, x1: a.target[0], y1: a.target[1], line: { color: INK, width: 1, dash: "dot" } }],
    xaxis: { ...axis, title: "metres", scaleanchor: "y", constrain: "domain" }, yaxis: { ...axis, title: "metres" },
    margin: { l: 56, r: 10, t: 16, b: 44 },
  }), cfg);
}

// Row labels: drop the parenthetical ("(Artemis III region)", "(Shackleton rim)") so names never clip.
const short = (n) => n.replace(/\s*\(.*?\)\s*/g, " ").replace(/^Peak near /, "").trim();

function slip(el, d) {
  const s = d.slip;
  const fails = { x: [], y: [] };
  s.survives.forEach((row, j) => row.forEach((ok, i) => { if (!ok) { fails.x.push(s.dates[i]); fails.y.push(short(s.names[j])); } }));
  const shape = (t) => [{ type: "line", x0: t, x1: t, yref: "paper", y0: 0, y1: 1, line: { color: INK, width: 2 } }];
  Plotly.newPlot(el, [
    { type: "heatmap", x: s.dates, y: s.names.map(short), z: s.pct_both, zmin: 0, zmax: 100,
      colorscale: [[0, "#0B0D17"], [0.3, "#2E2826"], [0.6, "#B9803F"], [0.85, SUN], [1, "#FFE9C2"]],
      colorbar: { title: { text: "Sun + link %", side: "right" }, thickness: 10, tickfont: { color: DIM } },
      hovertemplate: "%{y}<br>land %{x|%-d %b %Y}<br>Sun + link %{z:.0f}%<extra></extra>" },
    { x: fails.x, y: fails.y, mode: "markers", marker: { symbol: "circle", size: 3, color: ALARM, opacity: 0.55 },
      hovertemplate: "%{y}, %{x|%-d %b}: battery runs flat<extra></extra>" },
  ], base({ margin: { l: 12, r: 16, t: 16, b: 44 }, yaxis: { ...axis, autorange: "reversed", automargin: true, tickfont: { ...axis.tickfont, family: FONT.family, size: 11 } }, xaxis: { ...axis, tickformat: "%-d %b" },
    shapes: shape(new Date(Date.parse(s.planned) + s.slip_days * 864e5).toISOString()) }), cfg);
  document.addEventListener("slip", (e) => Plotly.relayout(el, { shapes: shape(new Date(e.detail).toISOString()) }));
}

const DRAW = { "earth-chart": earth, "ridge-chart": ridge, "athena-chart": athena, "slip-chart": slip };
export function draw(id, data) {
  const el = document.getElementById(id);
  DRAW[id]?.(el, data);
}
