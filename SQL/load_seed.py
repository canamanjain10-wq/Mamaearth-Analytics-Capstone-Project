#!/usr/bin/env python3
"""
load_seed.py – Re-runnable seed loader for the beauty e-commerce database.

Reads the three CSVs from ../data/, converts blank cells to NULL,
loads them into the SQLite database created by schema.sql, and
prints verification row counts (expected: 45 / 16 / 180).

Usage (from project root):
    sqlite3 beauty.db < sql/schema.sql
    python3 sql/load_seed.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "beauty.db"
DATA_DIR = ROOT / "data"


def blank_to_none(row: dict) -> dict:
    """Convert empty strings to None so SQLite stores NULL."""
    return {k: (None if v == "" else v) for k, v in row.items()}


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [blank_to_none(row) for row in reader]


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}\nRun schema.sql first.")

    customers = load_csv(DATA_DIR / "customers.csv")
    products = load_csv(DATA_DIR / "products.csv")
    orders = load_csv(DATA_DIR / "orders.csv")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Make the script re-runnable
    cur.execute("DELETE FROM orders")
    cur.execute("DELETE FROM products")
    cur.execute("DELETE FROM customers")

    cur.executemany(
        """
        INSERT INTO customers
            (customer_id, name, city, city_tier, signup_date, acquisition_source)
        VALUES
            (:customer_id, :name, :city, :city_tier, :signup_date, :acquisition_source)
        """,
        customers,
    )

    cur.executemany(
        """
        INSERT INTO products (product_id, product_name, category, price)
        VALUES (:product_id, :product_name, :category, :price)
        """,
        products,
    )

    # Coerce numeric fields; leave blanks as None
    for o in orders:
        o["quantity"] = int(o["quantity"]) if o["quantity"] is not None else None
        o["discount_pct"] = float(o["discount_pct"]) if o["discount_pct"] is not None else None
        o["rating"] = float(o["rating"]) if o["rating"] is not None else None
        o["returned"] = int(o["returned"]) if o["returned"] is not None else 0

    cur.executemany(
        """
        INSERT INTO orders
            (order_id, customer_id, product_id, order_date,
             quantity, discount_pct, payment_method, rating, returned)
        VALUES
            (:order_id, :customer_id, :product_id, :order_date,
             :quantity, :discount_pct, :payment_method, :rating, :returned)
        """,
        orders,
    )

    conn.commit()

    # Verification
    counts = {
        "customers": cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "products": cur.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders": cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
    }
    print("Row counts after load:")
    for table, n in counts.items():
        print(f"  {table:12s}: {n}")

    expected = {"customers": 45, "products": 16, "orders": 180}
    if counts != expected:
        raise SystemExit(f"Unexpected counts: {counts} (expected {expected})")

    # Quick NULL check
    null_discount = cur.execute(
        "SELECT COUNT(*) FROM orders WHERE discount_pct IS NULL"
    ).fetchone()[0]
    null_rating = cur.execute(
        "SELECT COUNT(*) FROM orders WHERE rating IS NULL"
    ).fetchone()[0]
    print(f"\nNULL discount_pct : {null_discount}")
    print(f"NULL rating       : {null_rating}")
    print("\nSeed completed successfully.")

    conn.close()


if __name__ == "__main__":
    main()
