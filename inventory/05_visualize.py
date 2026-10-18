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


ORDER = ["naive", "ma4", "ses", "holt", "holt_damped", "croston", "tsb"]
NAMES = {"naive": "Naive", "ma4": "MA 4 wk", "ses": "SES", "holt": "Holt", "holt_damped": "Holt damp.",
         "croston": "Croston", "tsb": "TSB"}


def forecast_chart(f, t):
    """Product level: two error metrics disagree, so the decision uses the stock outcome."""
    f = f.set_index("method").loc[ORDER]
    stock = t[t.sweep == "forecast"].set_index("forecast_method").loc[ORDER]
    chosen = ORDER.index("ses")
    labels = [NAMES[m] for m in ORDER]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9))
    bars(axes[0], labels, f.wape_pct.tolist(), "{:.0f}%", chosen, "Error: WAPE (%)")
    bars(axes[1], labels, f.scaled_rmse_pct.tolist(), "{:.0f}%", chosen, "Error: scaled RMSE (%)")
    bars(axes[2], labels, (stock.avg_inventory_value / 1000).tolist(), "{:.0f}k", chosen,
         "Stock needed in the simulation (R$)")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8.5)
    fig.suptitle("Product level: the error metrics disagree, so the method is chosen on the stock outcome",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.text(0.01, 0.01, "Dark bar = SES, used in the policy: the same fill rate as MA4 (89.6% vs 89.8%) with ~9% less "
             "stock. Holt adds nothing (no trend). Croston/TSB hold little stock but miss more orders.",
             fontsize=8.5, color=INK_2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIG / "forecast_backtest.png", dpi=160)
    plt.close(fig)


def daily_chart(table, series):
    """FC total daily volume: Holt-Winters vs. simpler methods."""
    table = table.sort_values("wape_pct")
    best = table.index[0]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.1), gridspec_kw={"width_ratios": [1, 1.5]})
    ax = axes[0]
    y = range(len(table))[::-1]
    ax.barh(list(y), table.wape_pct, color=[BLUE if m == best else LIGHT for m in table.index], height=0.6)
    ax.set_yticks(list(y), table.label, fontsize=9)
    for yi, v in zip(y, table.wape_pct):
        ax.text(v + 0.4, yi, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_title("7-day-ahead error (WAPE, lower is better)")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, table.wape_pct.max() * 1.18)
    ax = axes[1]
    ax.plot(series.index, series.actual, color=MUTED, lw=1.4, label="Actual")
    ax.plot(series.index, series[best], color=BLUE, lw=2, label=table.loc[best, "label"])
    ax.set_title("Actual vs. Holt-Winters forecast, test period (units per day)")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.tick_params(axis="x", labelsize=8.5)
    fig.suptitle("FC daily volume: models with a weekday pattern cut the error by ~28%",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "forecast_daily.png", dpi=160)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(exist_ok=True)
    t = pd.read_csv(OUT / "policy_tradeoff.csv")
    assortment_chart(t)
    service_chart(t)
    forecast_chart(pd.read_csv(OUT / "forecast_backtest.csv"), t)
    daily_chart(pd.read_csv(OUT / "forecast_daily_backtest.csv", index_col=0),
                pd.read_csv(OUT / "forecast_daily_series.csv", index_col=0, parse_dates=True))
    print("Figures written to", FIG)


if __name__ == "__main__":
    main()
