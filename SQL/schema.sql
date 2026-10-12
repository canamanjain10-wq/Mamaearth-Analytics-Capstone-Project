-- schema.sql
-- Capstone Project: Beauty & Personal Care E-commerce Analytics
-- Creates customers, products, and orders tables with proper constraints.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id      TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    city             TEXT NOT NULL,
    city_tier        INTEGER NOT NULL CHECK (city_tier IN (1, 2)),
    signup_date      DATE NOT NULL,
    acquisition_source TEXT NOT NULL
);

CREATE TABLE products (
    product_id    TEXT PRIMARY KEY,
    product_name  TEXT NOT NULL,
    category      TEXT NOT NULL,
    price         REAL NOT NULL CHECK (price > 0)
);

CREATE TABLE orders (
    order_id        TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL,
    product_id      TEXT NOT NULL,
    order_date      DATE NOT NULL,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    discount_pct    REAL,                    -- nullable
    payment_method  TEXT NOT NULL,
    rating          REAL,                    -- nullable
    returned        INTEGER NOT NULL DEFAULT 0 CHECK (returned IN (0, 1)),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id)  REFERENCES products(product_id)
);

-- Helpful indexes for reporting
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_product  ON orders(product_id);
CREATE INDEX idx_orders_date     ON orders(order_date);
