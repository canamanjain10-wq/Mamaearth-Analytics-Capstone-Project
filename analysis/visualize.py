#!/usr/bin/env python3
"""
visualize.py – Two required visualisations for the capstone.

1. category_return_rate.png          – return-rate bar chart by product category
2. monthly_revenue_corrected.png     – monthly revenue with vs without outliers
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

ROOT = Path(__file__).resolve().parent.parent
CLEANED = ROOT / "analysis" / "cleaned_orders.csv"
VIZ = ROOT / "visualizations"
VIZ.mkdir(exist_ok=True)


def main() -> None:
    df = pd.read_csv(CLEANED, parse_dates=["order_date"])
    df["month"] = df["order_date"].dt.to_period("M").astype(str)

    # ------------------------------------------------------------------
    # Chart 1 – Return-rate bar chart by category
    # ------------------------------------------------------------------
    cat = (
        df.groupby("category")
        .agg(orders=("order_id", "count"), returns=("returned", "sum"))
        .reset_index()
    )
    cat["return_rate"] = cat["returns"] / cat["orders"] * 100
    cat = cat.sort_values("return_rate", ascending=False)

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(cat["category"], cat["return_rate"], color="#e76f51", edgecolor="white")
    ax.set_title("Return Rate by Product Category", fontsize=14, pad=12)
    ax.set_xlabel("Category")
    ax.set_ylabel("Return Rate (%)")
    ax.set_ylim(0, max(cat["return_rate"]) * 1.30)
    for bar, rate in zip(bars, cat["return_rate"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.6,
            f"{rate:.1f}%",
            ha="center", va="bottom", fontsize=11,
        )
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out1 = VIZ / "category_return_rate.png"
    fig.savefig(out1, dpi=150)
    plt.close()
    print(f"Saved {out1}")

    # ------------------------------------------------------------------
    # Chart 2 – Monthly revenue: with outliers vs without outliers
    # ------------------------------------------------------------------
    with_out = df.groupby("month")["order_value"].sum()
    without_out = (
        df.loc[~df["is_quantity_outlier"]]
        .groupby("month")["order_value"].sum()
    )
    months = sorted(with_out.index)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(months, [with_out[m] for m in months],
            marker="o", linewidth=2, label="With outliers", color="#264653")
    ax.plot(months, [without_out.get(m, 0) for m in months],
            marker="s", linewidth=2, label="Without outliers", color="#2a9d8f")
    ax.set_title("Monthly Revenue – Outlier Corrected Trend", fontsize=14, pad=12)
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (INR)")
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    out2 = VIZ / "monthly_revenue_corrected.png"
    fig.savefig(out2, dpi=150)
    plt.close()
    print(f"Saved {out2}")

    # Keep the original simple trend as well (optional, already present)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(months, [with_out[m] for m in months], marker="o", linewidth=2, color="#264653")
    ax.set_title("Monthly Revenue Trend (Cleaned Data)", fontsize=14, pad=12)
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (INR)")
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    out3 = VIZ / "monthly_revenue_trend.png"
    fig.savefig(out3, dpi=150)
    plt.close()
    print(f"Saved {out3}")


if __name__ == "__main__":
    main()
