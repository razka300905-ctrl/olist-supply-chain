"""Step 5 - Figures for the README: assortment depth trade-off, service-level curve, forecast backtest."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
FIG = HERE / "figures"

BLUE, LIGHT = "#2a78d6", "#b7d3f6"
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlelocation": "left",
})


def bars(ax, labels, values, fmt, chosen_idx, title):
    b = ax.bar(labels, values, color=[BLUE if i == chosen_idx else LIGHT for i in range(len(values))], width=0.6)
    for rect, v in zip(b, values):
        ax.text(rect.get_x() + rect.get_width() / 2, v * 1.02, fmt.format(v), ha="center", va="bottom", fontsize=9.5)
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, max(values) * 1.22)


def assortment_chart(t):
    s = t[t.sweep == "stock_rule"].sort_values("stock_rule_min_weeks")
    labels = [f"≥{w} of 12 wk\n({p} products)" for w, p in zip(s.stock_rule_min_weeks, s.products_listed_last_week)]
    chosen = list(s.stock_rule_min_weeks).index(6)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9))
    bars(axes[0], labels, s.fc_share_of_all_units_pct.tolist(), "{:.0f}%", chosen, "Share of all units shipped from the FC")
    bars(axes[1], labels, s.cost_per_unit_served.tolist(), "R$ {:.2f}", chosen, "Inventory cost per unit served")
    bars(axes[2], labels, s.weeks_of_cover.tolist(), "{:.1f} wk", chosen, "Stock on hand (weeks of cover)")
    fig.suptitle("Going deeper into the assortment ships more from the FC, but every extra unit costs more",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "assortment_tradeoff.png", dpi=160)
    plt.close(fig)


def service_chart(t):
    s = t[t.sweep == "service_level"].sort_values("service_level_pct")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, col, title, fmt in [(axes[0], "fill_rate_pct", "Fill rate achieved (%)", "{:.1f}%"),
                                (axes[1], "avg_inventory_value", "Average stock value (R$ thousand)", "R$ {:.0f}k")]:
        y = s[col] / (1000 if col == "avg_inventory_value" else 1)
        ax.plot(s.service_level_pct, y, color=BLUE, lw=2, marker="o", ms=7, markeredgecolor=SURFACE, markeredgewidth=2)
        sel = s.service_level_pct == 95
        ax.scatter(s.service_level_pct[sel], y[sel], s=170, facecolor="none", edgecolor=INK, lw=1.2, zorder=5)
        for x_, v in zip(s.service_level_pct, y):
            if x_ in (50, 95, 99):
                ax.annotate(fmt.format(v), (x_, v), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9)
        ax.set_title(title)
        ax.set_xlabel("Target cycle service level (%)")
        ax.margins(y=0.25)
    fig.suptitle("Raising the service target buys little fill rate; the assortment choice matters more",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "service_level_curve.png", dpi=160)
    plt.close(fig)


def forecast_chart(f):
    f = f.set_index("method").loc[["naive", "ma4", "ses", "croston"]]
    names = {"naive": "Naive", "ma4": "Moving avg (4 wk)", "ses": "Exp. smoothing", "croston": "Croston (SBA)"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    bars(axes[0], [names[m] for m in f.index], f.wape_pct.tolist(), "{:.0f}%", 1, "Forecast error (WAPE, lower is better)")
    bars(axes[1], [names[m] for m in f.index], f.bias_pct.tolist(), "{:+.0f}%", 1, "Bias (positive = forecasts too high)")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8.5)
    fig.suptitle("16-week backtest on the stocked products: simple, fast-reacting methods win",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.text(0.01, 0.01, "Dark bar = used in the stock policy. MA4 is almost as accurate as naive but does not jump "
             "with every single busy week, so reorder points and orders stay steadier.", fontsize=8.5, color=INK_2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIG / "forecast_backtest.png", dpi=160)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(exist_ok=True)
    t = pd.read_csv(OUT / "policy_tradeoff.csv")
    assortment_chart(t)
    service_chart(t)
    forecast_chart(pd.read_csv(OUT / "forecast_backtest.csv"))
    print("Figures written to", FIG)


if __name__ == "__main__":
    main()
