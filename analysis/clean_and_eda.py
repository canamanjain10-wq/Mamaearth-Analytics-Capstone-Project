#!/usr/bin/env python3
"""
clean_and_eda.py – Part 2: Python wrangling & EDA

Required steps:
1. Load and inspect          – three CSVs; confirm raw orders shape
2. Standardise casing        – payment_method 7 → 3 values
3. Remove duplicates         – natural-key double submissions; print dropped IDs
4. Impute missing values     – discount → 0, rating → median
5. Merge and reconcile       – compute order_value; explain vs Part-1 SQL total
6. IQR outliers              – flag quantity outliers (do NOT drop)
7. COD return hypothesis     – state hypothesis, test by payment method, verdict
8. Multi-level segmentation  – return rate by payment × city_tier; name highest-risk
9. Correlation analysis      – matrix + strength labels
10. Outlier-corrected trend  – monthly revenue with / without outliers; true peak
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "analysis"

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 140)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")


def corr_strength(r: float) -> str:
    a = abs(r)
    if a < 0.10:
        return "negligible"
    if a < 0.30:
        return "weak"
    if a < 0.50:
        return "moderate"
    return "strong"


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Load and inspect
    # ------------------------------------------------------------------
    print("=" * 70)
    print("1. LOAD AND INSPECT")
    print("=" * 70)
    customers = pd.read_csv(DATA / "customers.csv")
    products = pd.read_csv(DATA / "products.csv")
    orders = pd.read_csv(DATA / "orders.csv")

    print(f"customers shape : {customers.shape}")
    print(f"products shape  : {products.shape}")
    print(f"orders shape    : {orders.shape}")          # must be (180, 9)
    print(f"orders columns  : {list(orders.columns)}")
    assert len(orders) == 180, f"Expected 180 raw orders, got {len(orders)}"
    raw_order_count = 180
    print()

    # ------------------------------------------------------------------
    # 2. Standardise casing
    # ------------------------------------------------------------------
    print("=" * 70)
    print("2. STANDARDISE CASING")
    print("=" * 70)
    print("Raw payment_method values (7):")
    print(orders["payment_method"].value_counts(dropna=False).to_string())
    print()

    payment_map = {
        "upi": "UPI", "UPI": "UPI",
        "card": "Card", "Card": "Card", "CARD": "Card",
        "cod": "COD", "COD": "COD",
    }
    orders["payment_method"] = (
        orders["payment_method"].str.strip().map(payment_map)
    )
    print("After standardisation (3 values):")
    print(orders["payment_method"].value_counts(dropna=False).to_string())
    print()

    # ------------------------------------------------------------------
    # 3. Remove duplicates (natural key)
    # ------------------------------------------------------------------
    print("=" * 70)
    print("3. REMOVE DUPLICATES")
    print("=" * 70)
    natural_key = [
        "customer_id", "product_id", "order_date",
        "quantity", "discount_pct", "payment_method", "rating", "returned",
    ]
    dup_mask = orders.duplicated(subset=natural_key, keep="first")
    dropped_ids = orders.loc[dup_mask, "order_id"].tolist()
    print(f"Dropped order_ids (double submissions): {dropped_ids}")
    orders = orders.loc[~dup_mask].copy()
    print(f"Orders remaining: {len(orders)}")
    print()

    # ------------------------------------------------------------------
    # 4. Impute missing values
    # ------------------------------------------------------------------
    print("=" * 70)
    print("4. IMPUTE MISSING VALUES")
    print("=" * 70)
    print(f"Missing discount_pct before : {orders['discount_pct'].isna().sum()}")
    print(f"Missing rating before       : {orders['rating'].isna().sum()}")

    orders["discount_pct"] = orders["discount_pct"].fillna(0)
    median_rating = float(orders["rating"].median())
    orders["rating"] = orders["rating"].fillna(median_rating)

    print(f"Filled discount_pct with 0")
    print(f"Filled rating with median = {median_rating}")
    print(f"Missing discount_pct after  : {orders['discount_pct'].isna().sum()}")
    print(f"Missing rating after        : {orders['rating'].isna().sum()}")
    print()

    # ------------------------------------------------------------------
    # 5. Merge and reconcile
    # ------------------------------------------------------------------
    print("=" * 70)
    print("5. MERGE AND RECONCILE")
    print("=" * 70)
    merged = (
        orders
        .merge(customers, on="customer_id", how="left")
        .merge(products, on="product_id", how="left")
    )
    # Critical: divide by 100.0 (never integer 100)
    merged["order_value"] = (
        merged["quantity"]
        * merged["price"]
        * (1 - merged["discount_pct"] / 100.0)
    )
    cleaned_total = float(merged["order_value"].sum())
    part1_total = 99860.20          # from sql/reports.sql on raw 180 rows
    print(f"Part-1 SQL total revenue (raw 180 rows) : ₹{part1_total:,.2f}")
    print(f"Cleaned total revenue (175 rows)        : ₹{cleaned_total:,.2f}")
    print(f"Difference                              : ₹{part1_total - cleaned_total:,.2f}")
    print()
    print("Exact reason the totals differ:")
    print("  Part 1 ran on all 180 raw rows (including 5 double-submitted orders).")
    print("  Here we dropped those 5 rows before computing revenue.")
    print("  The difference equals the order_value of the dropped rows.")
    print()

    # ------------------------------------------------------------------
    # 6. IQR outliers (flag only)
    # ------------------------------------------------------------------
    print("=" * 70)
    print("6. IQR OUTLIERS ON QUANTITY")
    print("=" * 70)
    q1 = merged["quantity"].quantile(0.25)
    q3 = merged["quantity"].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    print(f"Q1={q1}, Q3={q3}, IQR={iqr} → fences [{lower}, {upper}]")

    merged["is_quantity_outlier"] = (
        (merged["quantity"] < lower) | (merged["quantity"] > upper)
    )
    outliers = merged.loc[merged["is_quantity_outlier"]]
    print(f"Quantity outliers flagged (kept): {len(outliers)}")
    if len(outliers):
        print(outliers[["order_id", "customer_id", "quantity", "order_value"]]
              .to_string(index=False))
    print()

    # ------------------------------------------------------------------
    # 7. COD return hypothesis
    # ------------------------------------------------------------------
    print("=" * 70)
    print("7. COD RETURN HYPOTHESIS")
    print("=" * 70)
    print("Hypothesis: COD orders have a higher return rate than Card or UPI")
    print("            because customers can refuse delivery more easily.")
    print()

    by_pay = (
        merged.groupby("payment_method")["returned"]
        .agg(orders="count", returns="sum", return_rate="mean")
        .assign(return_rate_pct=lambda x: (x["return_rate"] * 100).round(2))
        .sort_values("return_rate_pct", ascending=False)
    )
    print(by_pay[["orders", "returns", "return_rate_pct"]].to_string())
    print()

    cod_rate = by_pay.loc["COD", "return_rate_pct"]
    card_rate = by_pay.loc["Card", "return_rate_pct"]
    upi_rate = by_pay.loc["UPI", "return_rate_pct"]
    if cod_rate > card_rate and cod_rate > upi_rate:
        verdict = "SUPPORTED"
        reason = (
            f"COD return rate ({cod_rate}%) is materially higher than "
            f"Card ({card_rate}%) and UPI ({upi_rate}%)."
        )
    else:
        verdict = "NOT SUPPORTED"
        reason = "COD does not show the highest return rate."
    print(f"Verdict: {verdict}")
    print(f"Reason : {reason}")
    print()

    # ------------------------------------------------------------------
    # 8. Multi-level segmentation
    # ------------------------------------------------------------------
    print("=" * 70)
    print("8. MULTI-LEVEL SEGMENTATION (payment_method × city_tier)")
    print("=" * 70)
    seg = (
        merged.groupby(["payment_method", "city_tier"])["returned"]
        .agg(orders="count", returns="sum", return_rate="mean")
        .assign(return_rate_pct=lambda x: (x["return_rate"] * 100).round(2))
        .reset_index()
        .sort_values("return_rate_pct", ascending=False)
    )
    print(seg[["payment_method", "city_tier", "orders", "returns", "return_rate_pct"]]
          .to_string(index=False))
    top = seg.iloc[0]
    highest_risk = (
        f"{top['payment_method']} + Tier-{int(top['city_tier'])} "
        f"({top['return_rate_pct']}%)"
    )
    print()
    print(f"Highest-risk segment: {highest_risk}")
    print()

    # ------------------------------------------------------------------
    # 9. Correlation analysis
    # ------------------------------------------------------------------
    print("=" * 70)
    print("9. CORRELATION ANALYSIS")
    print("=" * 70)
    corr_cols = ["quantity", "discount_pct", "rating", "returned",
                 "order_value", "price"]
    corr = merged[corr_cols].corr().round(3)
    print(corr.to_string())
    print()
    print("Pair-wise strength labels (|r|):")
    pairs = []
    for i, a in enumerate(corr_cols):
        for b in corr_cols[i + 1:]:
            r = float(corr.loc[a, b])
            label = corr_strength(r)
            pairs.append({"pair": f"{a} ↔ {b}", "r": r, "strength": label})
            print(f"  {a:12s} ↔ {b:12s}  r={r:+.3f}  → {label}")
    print()

    # ------------------------------------------------------------------
    # 10. Outlier-corrected monthly trend
    # ------------------------------------------------------------------
    print("=" * 70)
    print("10. OUTLIER-CORRECTED MONTHLY REVENUE TREND")
    print("=" * 70)
    merged["month"] = pd.to_datetime(merged["order_date"]).dt.to_period("M").astype(str)

    with_out = (
        merged.groupby("month")["order_value"].sum().round(2).to_dict()
    )
    without_out = (
        merged.loc[~merged["is_quantity_outlier"]]
        .groupby("month")["order_value"].sum().round(2).to_dict()
    )

    print("Month       With outliers   Without outliers")
    for m in sorted(with_out):
        print(f"{m}   {with_out[m]:>12,.2f}   {without_out.get(m, 0):>14,.2f}")

    true_peak = max(without_out, key=without_out.get)
    print()
    print(f"True peak month (outliers removed): {true_peak} "
          f"(₹{without_out[true_peak]:,.2f})")
    print()

    # ------------------------------------------------------------------
    # Persist artefacts
    # ------------------------------------------------------------------
    cleaned_path = OUT / "cleaned_orders.csv"
    merged.to_csv(cleaned_path, index=False)
    print(f"Cleaned data → {cleaned_path}")

    summary = {
        "raw_orders": raw_order_count,
        "cleaned_orders": int(len(merged)),
        "dropped_duplicate_ids": dropped_ids,
        "median_rating_used": median_rating,
        "part1_sql_total": part1_total,
        "total_revenue_cleaned": round(cleaned_total, 2),
        "quantity_outliers": [
            {
                "order_id": r.order_id,
                "customer_id": r.customer_id,
                "quantity": int(r.quantity),
                "order_value": round(float(r.order_value), 2),
            }
            for _, r in outliers.iterrows()
        ],
        "payment_method_return_rates": {
            k: float(v) for k, v in by_pay["return_rate_pct"].items()
        },
        "cod_hypothesis_verdict": verdict,
        "cod_hypothesis_reason": reason,
        "highest_risk_segment": highest_risk,
        "correlation_pairs": pairs,
        "monthly_revenue_with_outliers": with_out,
        "monthly_revenue_without_outliers": without_out,
        "true_peak_month": true_peak,
        "true_peak_revenue": without_out[true_peak],
        "category_revenue": {
            k: round(float(v), 2)
            for k, v in merged.groupby("category")["order_value"].sum().items()
        },
        "overall_return_rate_pct": round(float(merged["returned"].mean() * 100), 2),
    }
    summary_path = OUT / "cleaning_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary     → {summary_path}")


if __name__ == "__main__":
    main()
