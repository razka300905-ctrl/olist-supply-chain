"""Step 3 - Figures for the README: cost per order by scenario, and route maps."""
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
FIG = HERE / "figures"

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
TYPE_COLOR = {"van": SERIES[0], "motorbike": SERIES[1]}
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
HALO = [pe.withStroke(linewidth=3, foreground=SURFACE)]
FLEET_LABEL = {"van_only": "Van only", "motorbike_only": "Motorbike only", "mixed": "Mixed fleet"}
DAY_LABEL = {"normal": "Normal day", "black_friday": "Black Friday"}

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlelocation": "left",
})


def cost_chart(sc):
    sc = sc[sc.fleet.isin(FLEET_LABEL)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, day in zip(axes, ["normal", "black_friday"]):
        d = sc[sc.day == day].set_index("fleet").loc[list(FLEET_LABEL)]
        best = d.cost_per_order.idxmin()
        colors = [SERIES[0] if f == best else "#b7d3f6" for f in d.index]
        bars = ax.bar([FLEET_LABEL[f] for f in d.index], d.cost_per_order, color=colors, width=0.6)
        for b, (f, r) in zip(bars, d.iterrows()):
            fleet_txt = " + ".join(x for x in [f"{r.vans} van" if r.vans else "", f"{r.motorbikes} moto" if r.motorbikes else ""] if x)
            ax.text(b.get_x() + b.get_width() / 2, r.cost_per_order + 0.6, f"R$ {r.cost_per_order:.2f}",
                    ha="center", fontsize=10, fontweight="bold" if f == best else "normal")
            ax.text(b.get_x() + b.get_width() / 2, 1.0, fleet_txt, ha="center", fontsize=8.5, color=INK, path_effects=HALO)
            if r.orders_not_delivered:
                ax.text(b.get_x() + b.get_width() / 2, r.cost_per_order + 3.2,
                        f"{int(r.orders_not_delivered)} too bulky", ha="center", fontsize=8, color=INK_2)
        ax.set_title(f"{DAY_LABEL[day]} ({int(d.orders.iloc[0])} orders)")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Cost per delivered order (R$)")
    axes[0].set_ylim(0, sc.cost_per_order.max() * 1.3)
    fig.suptitle("A mixed fleet is cheapest on both days: vans for bulky parcels, motorbikes for the rest",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "cost_per_order.png", dpi=160)
    plt.close(fig)


def route_maps(routes, depot):
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.2))
    for ax, sid in zip(axes, ["normal__mixed", "black_friday__mixed"]):
        r = routes[routes.scenario == sid]
        for (_, t), g in r.groupby(["route", "vehicle_type"]):
            g = g.sort_values("seq")
            ax.plot(g.lng, g.lat, color=TYPE_COLOR[t], lw=1.2, alpha=0.85)
            stops = g[g.order_id != "FC"]
            ax.scatter(stops.lng, stops.lat, s=14, color=TYPE_COLOR[t], edgecolor=SURFACE, lw=0.6, zorder=3)
        ax.scatter([depot.lng], [depot.lat], marker="*", s=380, color=INK, zorder=5)
        ax.annotate("FC São Paulo", (depot.lng, depot.lat), xytext=(8, -14), textcoords="offset points",
                    fontsize=9, path_effects=HALO)
        n_routes = r.route.nunique()
        day = sid.split("__")[0]
        ax.set_title(f"{DAY_LABEL[day]}: {r[r.order_id != 'FC'].order_id.nunique()} orders, {n_routes} routes")
        ax.set_aspect("equal")
        ax.set_xticks([]), ax.set_yticks([])
        ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(False)
    handles = [plt.Line2D([], [], color=c, lw=2, marker="o", ms=5, label=t.title()) for t, c in TYPE_COLOR.items()]
    axes[1].legend(handles=handles, frameon=False, loc="lower right")
    fig.suptitle("Optimised mixed-fleet routes from the São Paulo FC (Grande São Paulo)",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "route_maps.png", dpi=150)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(exist_ok=True)
    sc = pd.read_csv(OUT / "vrp_scenarios.csv")
    routes = pd.read_csv(OUT / "vrp_routes.csv")
    depot = pd.read_csv(OUT / "depot.csv").iloc[0]
    cost_chart(sc)
    route_maps(routes, depot)
    print("Figures written to", FIG)


if __name__ == "__main__":
    main()
