"""Step 3 - Charts (PNG, for the README) and an interactive network map (HTML)."""
from pathlib import Path

import folium
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
FIG = HERE / "figures"

# Reference palette (light mode) - categorical slots in fixed order
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlelocation": "left",
    "axes.axisbelow": True,
})

# Colour follows the hub's region, so a hub keeps its colour across all k panels.
REGION_SLOT = {"SP": 0, "SE": 1, "AL": 1, "BA": 1, "PE": 1, "MG": 2, "RS": 3, "GO": 4, "DF": 4, "RJ": 5}
HALO = [__import__("matplotlib.patheffects", fromlist=["x"]).withStroke(linewidth=3, foreground=SURFACE)]


def hub_color(state):
    return SERIES[REGION_SLOT.get(state, 0)]


def tradeoff_chart(summary):
    """Three small multiples (one measure each - no dual axis) vs. number of FCs."""
    asis, sc = summary.iloc[0], summary.iloc[1:]
    panels = [
        ("avg_km", "Avg. distance to customer (km)", "{:.0f}"),
        ("pct_within_300km", "Orders within 300 km (%)", "{:.0f}%"),
        ("est_delivery_days", "Est. delivery time (days)", "{:.1f}"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, (col, title, fmt) in zip(axes, panels):
        ax.axhline(asis[col], color=MUTED, lw=1.5, ls="--")
        ax.text(6.6, asis[col], "As-is (direct from seller)", color=INK_2, va="bottom", ha="right",
                fontsize=8.5, path_effects=HALO)
        ax.plot(sc.k, sc[col], color=SERIES[0], lw=2, marker="o", ms=7,
                markeredgecolor=SURFACE, markeredgewidth=2)
        hi = sc[sc.k == 3].iloc[0]
        ax.scatter([3], [hi[col]], s=160, facecolor="none", edgecolor=INK, lw=1.2, zorder=5)
        for _, r in sc[sc.k.isin([1, 3, 6])].iterrows():
            ax.annotate(fmt.format(r[col]), (r.k, r[col]), textcoords="offset points",
                        xytext=(0, 10), ha="center", fontsize=9, color=INK)
        ax.set_title(title)
        ax.set_xticks(sc.k)
        ax.set_xlabel("Number of fulfilment centres")
        ax.set_xlim(0.6, 6.7)
        ax.margins(y=0.2)
    fig.suptitle("Service level improves fast up to 3 FCs, then flattens", x=0.01, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "tradeoff_curves.png", dpi=160)
    plt.close(fig)


def marginal_chart(summary):
    sc = summary[summary.k >= 2]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars = ax.bar(sc.k, sc.marginal_freight_saving_per_year / 1000, width=0.6, color=SERIES[0])
    for b, v in zip(bars, sc.marginal_freight_saving_per_year / 1000):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"R$ {v:.0f}k", ha="center", fontsize=9)
    ax.set_title("Freight saved per year by adding the k-th FC")
    ax.set_xlabel("FC added (k)")
    ax.set_ylabel("R$ thousand / year")
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, sc.marginal_freight_saving_per_year.max() / 1000 * 1.2)
    fig.text(0.01, 0.01, "An extra FC pays off on freight alone only if it costs less than this per year.",
             fontsize=8.5, color=INK_2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "marginal_freight_saving.png", dpi=160)
    plt.close(fig)


def network_maps(assign, sites):
    """Small multiples: demand zones coloured by the FC that serves them, k = 1..6."""
    fig, axes = plt.subplots(2, 3, figsize=(12, 8.6))
    for ax, k in zip(axes.flat, range(1, 7)):
        a, s = assign[assign.k == k], sites[sites.k == k].reset_index(drop=True)
        color_of = {z: hub_color(st) for z, st in zip(s.zone, s.state)}
        ax.scatter(a.lng, a.lat, s=a.orders.clip(upper=2000) / 12 + 2,
                   c=a.fc_zone.map(color_of), alpha=0.75, linewidths=0)
        for _, r in s.iterrows():
            ax.scatter(r.lng, r.lat, marker="*", s=260, color=hub_color(r.state), edgecolor=INK, lw=0.8, zorder=5)
            # Rio sits right next to Sao Paulo, so its label goes above the star
            dy = 8 if r.state == "RJ" else -4
            ax.annotate(f"{r.city.title()} ({r.share_pct:.0f}%)", (r.lng, r.lat), xytext=(10, dy),
                        textcoords="offset points", fontsize=8, color=INK, zorder=6, path_effects=HALO)
        ax.set_title(f"{k} FC{'s' if k > 1 else ''}")
        ax.set_aspect("equal")
        ax.set_xticks([]), ax.set_yticks([])
        ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.suptitle("Optimal FC networks - dot = demand zone (size = orders), star = FC, % = share of orders served",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "network_maps_k1_to_k6.png", dpi=150)
    plt.close(fig)


def interactive_map(assign, sites):
    m = folium.Map(location=[-15.5, -50], zoom_start=4, tiles="OpenStreetMap")
    for k in range(1, 7):
        layer = folium.FeatureGroup(name=f"{k} FC{'s' if k > 1 else ''}", show=(k == 3))
        a, s = assign[assign.k == k], sites[sites.k == k].reset_index(drop=True)
        color_of = {z: hub_color(st) for z, st in zip(s.zone, s.state)}
        for _, r in a.iterrows():
            folium.CircleMarker(
                [r.lat, r.lng], radius=max(2, min(r.orders, 2000) ** 0.5 / 4),
                color=color_of[r.fc_zone], fill=True, fill_opacity=0.6, weight=0,
                tooltip=f"Zone {r.zone} ({r.state}) - {r.orders:,} orders - {r.road_km:.0f} km to FC",
            ).add_to(layer)
        for i, r in s.iterrows():
            folium.Marker(
                [r.lat, r.lng],
                tooltip=(f"<b>FC {r.city.title()}-{r.state}</b><br>{r.orders_served:,} orders "
                         f"({r.share_pct:.1f}%)<br>avg {r.avg_km_served:.0f} km to customer"),
                icon=folium.Icon(color="black", icon="home"),
            ).add_to(layer)
        layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(FIG / "network_map_interactive.html")


def main() -> None:
    FIG.mkdir(exist_ok=True)
    summary = pd.read_csv(OUT / "scenario_summary.csv")
    sites = pd.read_csv(OUT / "selected_sites.csv", dtype={"zone": str})
    assign = pd.read_csv(OUT / "zone_assignment.csv", dtype={"zone": str, "fc_zone": str})
    tradeoff_chart(summary)
    marginal_chart(summary)
    network_maps(assign, sites)
    interactive_map(assign, sites)
    print("Figures written to", FIG)


if __name__ == "__main__":
    main()
