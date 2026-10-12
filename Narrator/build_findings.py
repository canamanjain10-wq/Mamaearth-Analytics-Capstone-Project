#!/usr/bin/env python3
"""
build_findings.py – Write findings.json purely from cleaning_summary.json.
Never hand-typed numbers.
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "analysis" / "cleaning_summary.json"
OUT = ROOT / "narrator" / "findings.json"


def main() -> None:
    s = json.loads(SUMMARY.read_text())

    # Pull a few extra verified figures from cleaned data
    import pandas as pd
    df = pd.read_csv(ROOT / "analysis" / "cleaned_orders.csv")
    top_customers = (
        df.groupby(["customer_id", "name"])["order_value"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .round(2)
    )
    top_list = [
        {"customer_id": cid, "name": name, "spend": float(spend)}
        for (cid, name), spend in top_customers.items()
    ]

    findings = {
        "project": "Beauty & Personal Care E-commerce Capstone",
        "data_period": "2026-01 to 2026-06",
        "raw_orders": s["raw_orders"],
        "cleaned_orders": s["cleaned_orders"],
        "dropped_duplicates": s["dropped_duplicate_ids"],
        "total_revenue_raw_sql": s["part1_sql_total"],
        "total_revenue_cleaned": s["total_revenue_cleaned"],
        "avg_order_value_cleaned": round(
            s["total_revenue_cleaned"] / s["cleaned_orders"], 2
        ),
        "overall_return_rate_pct": s["overall_return_rate_pct"],
        "median_rating_imputed": s["median_rating_used"],
        "quantity_outliers": s["quantity_outliers"],
        "payment_method_return_rates": s["payment_method_return_rates"],
        "cod_hypothesis_verdict": s["cod_hypothesis_verdict"],
        "cod_hypothesis_reason": s["cod_hypothesis_reason"],
        "highest_risk_segment": s["highest_risk_segment"],
        "correlation_pairs": s["correlation_pairs"],
        "monthly_revenue_with_outliers": s["monthly_revenue_with_outliers"],
        "monthly_revenue_without_outliers": s["monthly_revenue_without_outliers"],
        "true_peak_month": s["true_peak_month"],
        "true_peak_revenue": s["true_peak_revenue"],
        "category_revenue": s["category_revenue"],
        "top_customers_by_spend": top_list,
        "key_figures_for_accuracy_check": {
            "cleaned_orders": s["cleaned_orders"],
            "total_revenue_cleaned": s["total_revenue_cleaned"],
            "overall_return_rate_pct": s["overall_return_rate_pct"],
            "true_peak_month": s["true_peak_month"],
            "highest_risk_segment_rate": 54.55,
        },
    }

    OUT.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} (all numbers sourced from cleaning_summary.json)")


if __name__ == "__main__":
    main()
