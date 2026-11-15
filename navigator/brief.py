"""One-page decision brief (HTML, print to PDF from the browser): scenario, verdicts with reasons, Plan B, assumptions
and sources. A plain f-string template; charts are embedded as Plotly HTML."""

from __future__ import annotations

import html

import pandas as pd

STYLE = """
body{font-family:Geist,system-ui,sans-serif;color:#15172B;max-width:900px;margin:32px auto;padding:0 20px;line-height:1.5}
h1{font-family:'Instrument Serif',Georgia,serif;font-weight:400;font-size:2.1rem;margin:0}
h2{font-family:'Instrument Serif',Georgia,serif;font-weight:400;font-size:1.3rem;margin:1.6rem 0 .4rem;border-bottom:1px solid #DDD}
.meta{color:#555;font-size:.92rem}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.card{border:1px solid #DDD;border-radius:12px;padding:12px}.card b{font-size:1.4rem;font-weight:500}
.good{color:#0F7B5F}.caution{color:#B45309}.bad{color:#C0262D}table{border-collapse:collapse;width:100%;font-size:.9rem}
td,th{border-bottom:1px solid #EEE;padding:4px 6px;text-align:left}small{color:#666}
@media print{.chart{page-break-inside:avoid}}
"""
WORD = {"good": "✓ Go", "caution": "⚠ Caution", "bad": "✗ No-go"}


def _ul(items) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(str(i))}</li>" for i in items) + "</ul>"


def render(scenario: dict, summary: dict, verdict: dict, light: dict, odds: dict | None, plan_b: list[dict],
           charts: list[str], assumptions: list[str], sources: list[str]) -> str:
    """`scenario`: site name, lat, lon, start, days, mast, lander name, horizon source. `charts`: Plotly HTML divs."""
    s = scenario
    card = lambda title, rating, big, reasons: (f"<div class='card'><div>{title}</div>"
                                                f"<div class='{rating}'>{WORD[rating]}</div><b>{big}</b>{_ul(reasons)}</div>")
    odds_html = ("" if odds is None else
                 f"<h2>Landing-zone odds</h2><p><b>{100 * odds['p_success']:.0f}%</b> of {odds['n']} landing points "
                 f"pass slope ≤ 10°, battery, link ≥ 50% and touchdown light. Per test: "
                 + ", ".join(f"{k} {100 * v:.0f}%" for k, v in odds["rates"].items()) + ".</p>")
    pb = "".join(f"<tr><td>{html.escape(p['title'])}</td><td>{html.escape(p['site'])}</td><td>{html.escape(p['date'])}</td>"
                 f"<td>{p['pct_both']:.0f}%</td><td>{html.escape(p['changed'])}</td></tr>" for p in plan_b)
    pb_html = ("" if not plan_b else "<h2>Plan B</h2><table><tr><th></th><th>Site</th><th>Landing (UTC)</th>"
               f"<th>Sun + link</th><th>What changed</th></tr>{pb}</table>")
    start = pd.Timestamp(s["start"]).strftime("%-d %b %Y %H:%M UTC")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gnomon brief: {html.escape(s['name'])}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{STYLE}</style></head><body>
<h1>{html.escape(s['name'])}</h1>
<div class="meta">{abs(s['lat']):.3f}° S, {s['lon']:.3f}° E · landing {start} · {s['days']} days · {s['mast']:g} m mast ·
{html.escape(s['lander'])} · terrain: {html.escape(s['horizon_source'])}</div>
<p>Gnomon, Lunar Landing Site Navigator. Generated {pd.Timestamp.now(tz='UTC'):%-d %b %Y %H:%M UTC}. Print to PDF from your browser.</p>
<h2>Verdict</h2><div class="cards">
{card("Power", verdict['power'], f"{summary['pct_sunlit']:.0f}% sunlit", [r for r in summary['reasons'] if r.startswith(('Sunlit', 'Longest night', 'Battery', 'Earth eclipses'))])}
{card("Comms", verdict['comms'], f"{summary['pct_link']:.0f}% link", [r for r in summary['reasons'] if r.startswith(('Direct', 'Longest comms', 'Earth skims'))])}
{card("Landing light", light['rating'], f"Sun {light['sun_el']:.1f}°", light['reasons'])}
</div>
{odds_html}{pb_html}
<h2>Charts</h2>{''.join(f"<div class='chart'>{c}</div>" for c in charts)}
<h2>Assumptions</h2>{_ul(assumptions)}
<h2>Sources</h2>{_ul(sources)}
<p><small>Numbers labelled illustrative (lander presets, comm thresholds, region centres) are placeholders to edit.
Method and limits: docs/METHOD.md in the project repository.</small></p>
</body></html>"""
