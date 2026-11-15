"""Plotly figures and the shared 'gnomon' template. Colour is physics: Sun gold, Earth blue, terrain grey,
warnings red. Every figure is built from data; the app only places them."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

SUN, EARTH, TERRAIN, ALARM = "#F6B94A", "#59A8FF", "#A7A9B4", "#FF5A5F"
GO, CAUTION, INK, INK_DIM, VOID = "#5FD4B0", "#FF8A3D", "#ECE9F7", "#A9A6C2", "#070B24"
BAND_COLORS = {"good": EARTH, "marginal": "#9CC9FF", "poor": CAUTION, "none": ALARM}
FONT = "Hanken Grotesk, Inter, system-ui, sans-serif"

TEMPLATE = go.layout.Template(layout=go.Layout(
    font=dict(family=FONT, color=INK, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(7,11,36,0.55)",
    colorway=[SUN, EARTH, TERRAIN, ALARM, "#B58CFF", GO],
    xaxis=dict(gridcolor="rgba(167,169,180,0.10)", zerolinecolor="rgba(167,169,180,0.25)", linecolor="rgba(167,169,180,0.25)"),
    yaxis=dict(gridcolor="rgba(167,169,180,0.10)", zerolinecolor="rgba(167,169,180,0.25)", linecolor="rgba(167,169,180,0.25)"),
    hoverlabel=dict(bgcolor="#11163A", bordercolor="#2A2F5C", font=dict(family=FONT, color=INK)),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.08, x=0, font=dict(color=INK_DIM)),
    margin=dict(l=56, r=20, t=48, b=48),
    title=dict(font=dict(family="Fraunces, Georgia, serif", size=18, color=INK), x=0, xanchor="left"),
))
pio.templates["gnomon"] = TEMPLATE
CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"],
          "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "gnomon"}}


def _wrap_az(az, el):
    """Break a path where azimuth wraps 360 -> 0 so the line doesn't streak across the plot."""
    az, el = np.asarray(az, float) % 360, np.asarray(el, float)
    jump = np.abs(np.diff(az)) > 180
    idx = np.flatnonzero(jump) + 1
    return np.insert(az, idx, np.nan), np.insert(el, idx, np.nan)


def _occluder_text(site, mast_m: float) -> list[str]:
    j = site.mast_row(mast_m)
    out = []
    for k in range(len(site.az)):
        name, rel, d = str(site.occ_name[j, k]), str(site.occ_relation[j, k]), float(site.dist[j, k])
        where = {"rim": f"rim of {name}", "inside": f"inside {name}", "on": name, "near": f"near {name}"}.get(rel, "unnamed terrain")
        if d < 500:
            where = "local slope"
        out.append(f"{where}, {d / 1000:.1f} km" if np.isfinite(d) else "smooth horizon")
    return out


def sky_panorama(site, tl: pd.DataFrame, mast_m: float, frame_hours: int = 6, height: int = 430) -> go.Figure:
    """360-degree sky: terrain skyline (grey fill), Sun and Earth paths over the mission, and their discs to
    scale (vertically) with a play button and time slider (Plotly animation frames)."""
    h = site.horizon(mast_m)
    polar = site.lat < -60
    lo = -2.0
    hi = 10.0 if polar else max(10.0, float(np.nanmax([tl["sun_el"].max(), tl["earth_el"].max()])) + 5)
    if polar:
        hi = max(hi, float(min(np.nanmax(h) + 1, 25)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.r_[site.az, 360.0], y=np.r_[h, h[0]], mode="lines", fill="tozeroy",
                             line=dict(color=TERRAIN, width=1.2), fillcolor="rgba(120,122,134,0.55)",
                             name="Terrain skyline", text=_occluder_text(site, mast_m) + [""],
                             hovertemplate="az %{x:.1f}°<br>horizon %{y:.2f}°<br>%{text}<extra>Terrain</extra>"))
    fig.add_trace(go.Scatter(x=[0, 360], y=[lo, lo], mode="lines", line=dict(width=0), showlegend=False,
                             fill="tonexty", fillcolor="rgba(120,122,134,0.55)", hoverinfo="skip"))
    for body, col, label in (("sun", SUN, "Sun path"), ("earth", EARTH, "Earth path")):
        x, y = _wrap_az(tl[f"{body}_az"], tl[f"{body}_el"])
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=label, line=dict(color=col, width=1.4, dash="dot"),
                                 opacity=0.8, hoverinfo="skip"))
    px_per_deg = (height - 110) / (hi - lo)
    sel = tl.iloc[::frame_hours]

    def discs(r):
        return [go.Scatter(x=[r["sun_az"] % 360], y=[r["sun_el"]], mode="markers", name="Sun",
                           marker=dict(size=max(2 * r["sun_r"] * px_per_deg, 6), color=SUN,
                                       line=dict(color="#FFE3A3", width=1)),
                           hovertemplate="Sun<br>az %{x:.1f}° el %{y:.2f}°<extra></extra>"),
                go.Scatter(x=[r["earth_az"] % 360], y=[r["earth_el"]], mode="markers", name="Earth",
                           marker=dict(size=max(2 * r["earth_r"] * px_per_deg, 6), color=EARTH,
                                       line=dict(color="#CFE6FF", width=1)),
                           hovertemplate="Earth<br>az %{x:.1f}° el %{y:.2f}°<extra></extra>")]

    first = sel.iloc[0]
    for tr in discs(first):
        fig.add_trace(tr)
    n_static = len(fig.data) - 2
    fig.frames = [go.Frame(data=discs(r), traces=[n_static, n_static + 1], name=r["utc"].strftime("%Y-%m-%d %H:%M"))
                  for _, r in sel.iterrows()]
    steps = [dict(method="animate", label=r["utc"].strftime("%-d %b %H:%M"),
                  args=[[r["utc"].strftime("%Y-%m-%d %H:%M")], dict(mode="immediate", frame=dict(duration=0, redraw=False),
                                                                     transition=dict(duration=0))])
             for _, r in sel.iterrows()]
    fig.update_layout(
        template="gnomon", height=height, margin=dict(l=48, r=16, t=40, b=90),
        xaxis=dict(range=[0, 360], tickvals=[0, 45, 90, 135, 180, 225, 270, 315, 360],
                   ticktext=["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"], title=None),
        yaxis=dict(range=[lo, hi], title="Elevation (°)"),
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=-0.2, xanchor="left", yanchor="top",
                          bgcolor="#11163A", bordercolor="#2A2F5C", font=dict(color=INK),
                          buttons=[dict(label="Play", method="animate",
                                        args=[None, dict(frame=dict(duration=120, redraw=False), fromcurrent=True,
                                                         transition=dict(duration=0))]),
                                   dict(label="Pause", method="animate",
                                        args=[[None], dict(mode="immediate", frame=dict(duration=0, redraw=False))])])],
        sliders=[dict(active=0, steps=steps, x=0.12, len=0.88, y=-0.14, yanchor="top", pad=dict(t=0),
                      currentvalue=dict(prefix="UTC ", font=dict(color=INK_DIM, size=12)),
                      font=dict(color=INK_DIM, size=10), bgcolor="#2A2F5C", activebgcolor=SUN, tickcolor="#2A2F5C")],
    )
    return fig


def _runs(t, mask):
    t = pd.DatetimeIndex(t)
    m = np.asarray(mask, bool)
    e = np.diff(np.r_[0, m.astype(int), 0])
    return [(t[a], t[min(b, len(t) - 1)]) for a, b in zip(np.flatnonzero(e == 1), np.flatnonzero(e == -1))]


def timeline(tl: pd.DataFrame, height: int = 560) -> go.Figure:
    """Three stacked panels over the mission: Sun/Earth clearance with sunlit periods shaded, the comm-quality
    band, and battery state of charge with the 20 % floor. Eclipses are marked."""
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.55, 0.12, 0.33], vertical_spacing=0.05,
                        subplot_titles=("Clearance above the terrain (°)", "Link to Earth", "Battery"))
    t = tl["utc"]
    for a, b in _runs(t, tl["sunlit"]):
        fig.add_vrect(x0=a, x1=b, fillcolor=SUN, opacity=0.09, line_width=0, row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=tl["sun_clear"].clip(-6, 12), name="Sun clearance", line=dict(color=SUN, width=2),
                             hovertemplate="%{x|%-d %b %H:%M}<br>Sun %{y:.2f}° above terrain<extra></extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=tl["earth_clear"].clip(-6, 12), name="Earth clearance",
                             line=dict(color=EARTH, width=2),
                             hovertemplate="%{x|%-d %b %H:%M}<br>Earth %{y:.2f}° above terrain<extra></extra>"), 1, 1)
    fig.add_hline(y=0, line=dict(color=TERRAIN, width=1), row=1, col=1)
    ecl = tl[tl["eclipse"] > 0]
    if len(ecl):
        fig.add_trace(go.Scatter(x=ecl["utc"], y=np.full(len(ecl), 11), mode="markers", name="Eclipse",
                                 marker=dict(symbol="x", color=ALARM, size=9),
                                 hovertemplate="%{x|%-d %b %H:%M}<br>Earth covers the Sun<extra>Eclipse</extra>"), 1, 1)
    order = ["none", "poor", "marginal", "good"]
    z = np.array([[order.index(b) for b in tl["band"]]])
    z = np.where(tl["dsn"].to_numpy()[None, :], z, 0)
    scale = [[0, BAND_COLORS["none"]], [0.25, BAND_COLORS["none"]], [0.25, BAND_COLORS["poor"]],
             [0.5, BAND_COLORS["poor"]], [0.5, BAND_COLORS["marginal"]], [0.75, BAND_COLORS["marginal"]],
             [0.75, BAND_COLORS["good"]], [1, BAND_COLORS["good"]]]
    labels = np.array([["No link", "Poor (multipath)", "Marginal", "Good"][v] for v in z[0]])[None, :]
    fig.add_trace(go.Heatmap(x=t, y=["Link"], z=z, zmin=0, zmax=3, colorscale=scale, showscale=False,
                             customdata=labels, hovertemplate="%{x|%-d %b %H:%M}<br>%{customdata}<extra></extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=t, y=100 * tl["soc"], name="Battery", line=dict(color=INK, width=1.8),
                             fill="tozeroy", fillcolor="rgba(236,233,247,0.06)",
                             hovertemplate="%{x|%-d %b %H:%M}<br>%{y:.0f} %<extra>Battery</extra>"), 3, 1)
    fig.add_hline(y=20, line=dict(color=ALARM, width=1, dash="dash"), row=3, col=1,
                  annotation_text="20 % floor", annotation_font_color=ALARM, annotation_position="bottom right")
    fig.update_yaxes(range=[-6, 12], row=1, col=1)
    fig.update_yaxes(showticklabels=False, row=2, col=1)
    fig.update_yaxes(range=[0, 105], ticksuffix=" %", row=3, col=1)
    fig.update_layout(template="gnomon", height=height, margin=dict(l=56, r=20, t=70, b=40), hovermode="x unified",
                      legend=dict(y=1.1, x=1, xanchor="right"))
    for ann in fig.layout.annotations:
        if ann.text in ("Clearance above the terrain (°)", "Link to Earth", "Battery"):
            ann.update(x=0, xanchor="left", font=dict(size=13, color=INK_DIM))
    return fig


def psr_traces(geojson: dict, min_area_km2: float = 3.0, crs_scale: float = 1.0) -> go.Scatter:
    """All PSR outlines as one line trace (None-separated rings), thinned to the larger ones for speed."""
    xs, ys = [], []
    for f in geojson["features"]:
        if float(f["properties"].get("area_km2") or 0) < min_area_km2:  # stored as text in the shapefile
            continue
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ring = np.asarray(poly[0])
            xs += list(ring[:, 0] / 1000) + [None]
            ys += list(ring[:, 1] / 1000) + [None]
    return go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#B58CFF", width=1), name="Permanently shadowed",
                      hoverinfo="skip")


def map_figure(layer: dict, body: str, sites: pd.DataFrame, psr: go.Scatter | None, selected: str | None = None,
               marker_xy: tuple | None = None, height: int = 680) -> go.Figure:
    """NASA's long-run visibility (PGDA 69) in polar stereographic km, PSR outlines, and the catalog sites."""
    if body == "sun":  # dark -> ember -> gold -> pale gold: long-run sunlight is mostly 0-50 %, so spend contrast there
        scale = [[0, "#05071A"], [0.12, "#2A1F48"], [0.3, "#6E3F4E"], [0.5, "#C2793A"], [0.75, SUN], [1, "#FFF1C9"]]
    else:
        scale = [[0, "#05071A"], [0.2, "#14234F"], [0.5, "#2F64B5"], [0.8, EARTH], [1, "#E3F0FF"]]
    fig = go.Figure(go.Heatmap(x=layer["x"] / 1000, y=layer["y"] / 1000, z=layer[body], colorscale=scale, zmin=0,
                               zmax=100, colorbar=dict(title=dict(text="% of time", side="right"), thickness=10,
                                                       tickfont=dict(color=INK_DIM)),
                               hovertemplate="x %{x:.0f} km, y %{y:.0f} km<br>%{z} % of time<extra>NASA</extra>"))
    if psr is not None:
        fig.add_trace(psr)
    sel = sites["id"] == selected if selected else np.zeros(len(sites), bool)
    labels = np.where(sel, sites["short"], "")  # crowded near the pole: name only the selected site, hover the rest
    fig.add_trace(go.Scatter(x=sites["x_km"], y=sites["y_km"], mode="markers+text", text=labels,
                             hovertext=sites["short"], textposition="top center",
                             textfont=dict(color=INK, size=13, family="Fraunces, serif"), customdata=sites["id"],
                             marker=dict(size=np.where(sel, 16, 10), color=np.where(sel, SUN, INK), symbol="diamond",
                                         line=dict(color=VOID, width=1.5)),
                             name="Sites", hovertemplate="%{hovertext}<extra>click to plan</extra>"))
    if marker_xy is not None:
        fig.add_trace(go.Scatter(x=[marker_xy[0] / 1000], y=[marker_xy[1] / 1000], mode="markers+text",
                                 text=[marker_xy[2]], textposition="bottom center", textfont=dict(color=ALARM),
                                 marker=dict(symbol="x-thin", size=18, color=ALARM, line=dict(width=3, color=ALARM)),
                                 name="Occluder", hoverinfo="text"))
    fig.update_layout(template="gnomon", height=height, xaxis=dict(title="km", scaleanchor="y", constrain="domain"),
                      yaxis=dict(title="km"), margin=dict(l=50, r=10, t=30, b=40), dragmode="pan")
    return fig


def compare_bars(df: pd.DataFrame) -> go.Figure:
    """% sunlit / link / both per scenario as grouped bars."""
    fig = go.Figure()
    for col, name, colour in (("pct_sunlit", "Sunlit", SUN), ("pct_link", "Link", EARTH), ("pct_both", "Both", INK)):
        fig.add_trace(go.Bar(x=df["label"], y=df[col], name=name, marker_color=colour,
                             hovertemplate="%{x}<br>%{y:.0f} %<extra>" + name + "</extra>"))
    fig.update_layout(template="gnomon", barmode="group", height=360, yaxis=dict(range=[0, 100], ticksuffix=" %"))
    return fig


def hillshade(z: np.ndarray, cell_m: float, az_deg: float = 315.0, alt_deg: float = 20.0) -> np.ndarray:
    """0-1 shaded relief of a height grid (rows north-up), Sun from az_deg at alt_deg."""
    zz = np.nan_to_num(z, nan=np.nanmean(z))
    gy, gx = np.gradient(zz, cell_m)
    gy = -gy  # rows go south
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, -gy)
    az, alt = np.radians(az_deg), np.radians(alt_deg)
    return np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)


def odds_scatter(relief: dict, odds: dict, extra_points: list | None = None, height: int = 520) -> go.Figure:
    """Landing-ellipse points over the 20 m relief: pass = gold circle, fail = red cross. Axes in metres from the
    site (polar stereographic)."""
    sx, sy = float(relief["site_x"]), float(relief["site_y"])
    hs = hillshade(relief["z"], float(relief["cell_m"]))
    fig = go.Figure(go.Heatmap(x=relief["x"] - sx, y=relief["y"] - sy, z=hs, colorscale=[[0, "#0B0D1A"], [1, "#B9BBC6"]],
                               showscale=False, hoverinfo="skip"))
    pts = odds["points"]
    for ok, name, sym, col in ((True, "Passes all four", "circle", SUN), (False, "Fails at least one", "x", ALARM)):
        p = pts[pts["pass_all"] == ok]
        why = p.apply(lambda r: ", ".join(k for k, c in (("slope", "pass_slope"), ("power", "pass_power"),
                                                         ("comms", "pass_comms"), ("light", "pass_light"))
                                         if not r[c]) or "all pass", axis=1)
        fig.add_trace(go.Scatter(x=p["x"] - sx, y=p["y"] - sy, mode="markers", name=name,
                                 marker=dict(symbol=sym, size=9 if ok else 8, color=col,
                                             line=dict(color=VOID if ok else col, width=1)),
                                 customdata=np.c_[p["slope_deg"], p["pct_both"], why],
                                 hovertemplate="slope %{customdata[0]:.1f}°<br>Sun + link %{customdata[1]:.0f} %"
                                               "<br>fails: %{customdata[2]}<extra></extra>"))
    for x, y, label, col in extra_points or []:
        fig.add_trace(go.Scatter(x=[x - sx], y=[y - sy], mode="markers+text", text=[label], textposition="top center",
                                 marker=dict(symbol="diamond", size=14, color=col, line=dict(color=VOID, width=1.5)),
                                 textfont=dict(color=INK), name=label, hoverinfo="text"))
    fig.update_layout(template="gnomon", height=height, xaxis=dict(title="metres east (map x)", scaleanchor="y",
                                                                     constrain="domain"),
                      yaxis=dict(title="metres north (map y)"), margin=dict(l=60, r=10, t=40, b=50))
    return fig


def criteria_bars(rates: dict) -> go.Figure:
    names = {"slope": "Slope ≤ 10°", "power": "Battery survives", "comms": "Link ≥ 50 %", "light": "Sun at touchdown"}
    keys = list(rates)
    vals = [100 * rates[k] for k in keys]
    fig = go.Figure(go.Bar(x=vals, y=[names[k] for k in keys], orientation="h",
                           marker_color=[GO if v >= 90 else CAUTION if v >= 50 else ALARM for v in vals],
                           text=[f"{v:.0f} %" for v in vals], textposition="outside",
                           hovertemplate="%{y}: %{x:.0f} % of landing points<extra></extra>"))
    fig.update_layout(template="gnomon", height=230, xaxis=dict(range=[0, 115], ticksuffix=" %"),
                      margin=dict(l=130, r=20, t=20, b=30), yaxis=dict(autorange="reversed"))
    return fig


def mast_curve(df: pd.DataFrame, current: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["mast_m"], y=df["pct_sunlit"], name="Sunlit", mode="lines+markers",
                             line=dict(color=SUN, width=2.5)))
    fig.add_trace(go.Scatter(x=df["mast_m"], y=df["pct_link"], name="Link usable", mode="lines+markers",
                             line=dict(color=EARTH, width=2.5)))
    fig.add_vline(x=10, line=dict(color=INK_DIM, dash="dash"), annotation_text="NASA VSAT mast class (10 m)",
                  annotation_font_color=INK_DIM, annotation_position="top left")
    fig.add_vline(x=current, line=dict(color=INK, width=1), annotation_text="this plan", annotation_font_color=INK)
    fig.update_layout(template="gnomon", height=330, xaxis=dict(title="Mast height (m)"),
                      yaxis=dict(title="% of the mission", range=[0, 105]))
    return fig


def pareto_front(x, y) -> np.ndarray:
    """Indices of points not dominated when x is minimised and y maximised, sorted by x."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    order = np.lexsort((-y, x))
    best, keep = -np.inf, []
    for i in order:
        if y[i] > best:
            keep.append(i)
            best = y[i]
    return np.array(keep, int)


def pareto_figure(df: pd.DataFrame) -> go.Figure:
    """Science (close to permanent shadow, where the ice is) vs engineering (Sun + link): frontier highlighted."""
    front = df.iloc[pareto_front(df["psr_km"], df["pct_both"])]
    fig = go.Figure()
    for kind, col, sym in (("Landing point", TERRAIN, "circle"), ("Catalog site", INK, "diamond")):
        d = df[df["kind"] == kind]
        fig.add_trace(go.Scatter(x=d["psr_km"], y=d["pct_both"], mode="markers", name=kind, text=d["label"],
                                 marker=dict(color=col, symbol=sym, size=7 if kind == "Landing point" else 11, opacity=0.8),
                                 hovertemplate="%{text}<br>%{x:.1f} km to permanent shadow<br>Sun + link %{y:.0f} %<extra></extra>"))
    fig.add_trace(go.Scatter(x=front["psr_km"], y=front["pct_both"], mode="lines+markers", name="Best trade-offs",
                             line=dict(color=SUN, width=2), marker=dict(color=SUN, size=9), text=front["label"],
                             hovertemplate="%{text}<extra>Pareto frontier</extra>"))
    fig.update_layout(template="gnomon", height=380, xaxis=dict(title="Distance to the nearest permanently shadowed region (km)"),
                      yaxis=dict(title="Sun and link at once (% of mission)", range=[0, 105]))
    return fig


def replan_heatmap(df: pd.DataFrame, landing, original_site: str, height: int = 560) -> go.Figure:
    """Rows = sites, columns = landing dates; colour = % Sun and link; crosses where the battery fails."""
    piv = df.pivot_table(index="name", columns="date", values="pct_both", sort=False)
    fail = df[~df["survives"]]
    scale = [[0, "#0B0F2E"], [0.3, "#3B3150"], [0.6, "#C2793A"], [0.85, SUN], [1, "#FFF1C9"]]
    fig = go.Figure(go.Heatmap(x=piv.columns, y=piv.index, z=piv.values, colorscale=scale, zmin=0, zmax=100,
                               colorbar=dict(title=dict(text="Sun + link %", side="right"), thickness=10),
                               hovertemplate="%{y}<br>land %{x|%-d %b %Y}<br>Sun + link %{z:.0f} %<extra></extra>"))
    fig.add_trace(go.Scatter(x=fail["date"], y=fail["name"], mode="markers", name="Battery fails",
                             marker=dict(symbol="x-thin", size=6, color=ALARM, line=dict(width=1.5, color=ALARM)),
                             hovertemplate="%{y}, %{x|%-d %b}: battery fails<extra></extra>"))
    fig.add_vline(x=pd.Timestamp(landing), line=dict(color=INK, width=1.5, dash="dot"))
    fig.add_annotation(x=pd.Timestamp(landing), y=1.02, yref="paper", text="slipped landing", showarrow=False,
                       font=dict(color=INK, size=12), xanchor="left")
    fig.update_layout(template="gnomon", height=height, margin=dict(l=210, r=20, t=40, b=40),
                      yaxis=dict(autorange="reversed"), legend=dict(y=1.08, x=1, xanchor="right"))
    return fig
