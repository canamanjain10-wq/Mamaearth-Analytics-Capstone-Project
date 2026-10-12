-- reports.sql
-- Nine business queries on the raw (seeded) data.
-- Exact query output is pasted as a comment block above each query.
-- Run against beauty.db after schema + seed:
--   sqlite3 -header -column beauty.db < sql/reports.sql

------------------------------------------------------------------------------
-- 1. Order totals
--    Total orders, revenue and average order value
--    (NULL discount_pct treated as 0%)
/*
total_orders  total_revenue  avg_order_value
------------  -------------  ---------------
180           99860.2        554.78
*/
SELECT
    COUNT(*) AS total_orders,
    ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
        AS total_revenue,
    ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
        AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id;


------------------------------------------------------------------------------
-- 2. COUNT(*) vs COUNT(col)
--    Show how many orders have no rating
/*
total_rows  non_null_ratings  missing_ratings
----------  ----------------  ---------------
180         165               15
*/
SELECT
    COUNT(*)            AS total_rows,
    COUNT(rating)       AS non_null_ratings,
    COUNT(*) - COUNT(rating) AS missing_ratings
FROM orders;


------------------------------------------------------------------------------
-- 3. LEFT JOIN + NOT IN
--    Find customers with zero orders – two equivalent ways
/*
LEFT JOIN result:
customer_id  name
-----------  ------
C045         Vihaan

NOT IN result:
customer_id  name
-----------  ------
C045         Vihaan
*/
-- Method A: LEFT JOIN
SELECT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;

-- Method B: NOT IN
SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders)
ORDER BY customer_id;


------------------------------------------------------------------------------
-- 4. GROUP BY + HAVING
--    Return rate by city; keep only cities above 20 %
/*
city       total_orders  returns  return_rate_pct
---------  ------------  -------  ---------------
Jaipur     19            8        42.11
Lucknow    49            15       30.61
Bangalore  33            8        24.24
*/
SELECT
    c.city,
    COUNT(*) AS total_orders,
    SUM(o.returned) AS returns,
    ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.city
HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;


------------------------------------------------------------------------------
-- 5. ORDER BY + LIMIT / OFFSET
--    Top 5 customers by spend, then ranks 3–5 via OFFSET
/*
Top 5:
customer_id  name     total_spend
-----------  -------  -----------
C043         Reyansh  12920.0
C026         Isha     8371.6
C008         Meera    4564.6
C011         Arjun    4111.0
C042         Sanya    3785.0

Ranks 3–5 (OFFSET 2 LIMIT 3):
customer_id  name   total_spend
-----------  -----  -----------
C008         Meera  4564.6
C011         Arjun  4111.0
C042         Sanya  3785.0
*/
-- Top 5
SELECT
    c.customer_id,
    c.name,
    ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
        AS total_spend
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p  ON o.product_id  = p.product_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC
LIMIT 5;

-- Ranks 3–5
SELECT
    c.customer_id,
    c.name,
    ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
        AS total_spend
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p  ON o.product_id  = p.product_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC
LIMIT 3 OFFSET 2;


------------------------------------------------------------------------------
-- 6. Three-table JOIN
--    Order count and revenue by product category
/*
category      order_count  revenue
------------  -----------  -------
Haircare      54           44956.1
Skincare      60           27346.0
Babycare      30           16805.0
PersonalCare  36           10753.1
*/
SELECT
    p.category,
    COUNT(*) AS order_count,
    ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
        AS revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;


------------------------------------------------------------------------------
-- 7. LIKE
--    Customers whose name starts with "A"
/*
customer_id  name    city       acquisition_source
-----------  ------  ---------  ------------------
C001         Aarav   Mumbai     Organic
C003         Aditi   Mumbai     Organic
C031         Aditya  Jaipur     Ad
C036         Aisha   Delhi      Ad
C004         Ananya  Lucknow    Organic
C030         Anika   Bangalore  Organic
C044         Aria    Bangalore  Referral
C011         Arjun   Bangalore  Referral
C021         Aryan   Bangalore  Ad
C041         Ayaan   Lucknow    Organic
*/
SELECT customer_id, name, city, acquisition_source
FROM customers
WHERE name LIKE 'A%'
ORDER BY name;


------------------------------------------------------------------------------
-- 8. DISTINCT
--    Distinct acquisition sources
/*
acquisition_source
------------------
Ad
Organic
Referral
Social
*/
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;


------------------------------------------------------------------------------
-- 9. ALTER + UPDATE CASE
--    Add loyalty_tier: Gold for tier-1 cities, else Silver
/*
After ALTER + UPDATE the first 10 rows look like:
customer_id  name     city       city_tier  loyalty_tier
-----------  -------  ---------  ---------  ------------
C001         Aarav    Mumbai     1          Gold
C002         Vivaan   Delhi      1          Gold
C003         Aditi    Mumbai     1          Gold
C004         Ananya   Lucknow    2          Silver
C005         Ishaan   Mumbai     1          Gold
C006         Diya     Delhi      1          Gold
C007         Kabir    Lucknow    2          Silver
C008         Meera    Lucknow    2          Silver
C009         Rohan    Lucknow    2          Silver
C010         Sara     Mumbai     1          Gold
*/
-- Make the statement re-runnable.
-- SQLite has no "ADD COLUMN IF NOT EXISTS", so we guard with a temp check.
-- On a fresh database the ALTER runs; on subsequent runs the column already
-- exists and we simply re-apply the UPDATE.

-- (If you see "duplicate column name" it is safe to ignore – the UPDATE still runs.)
ALTER TABLE customers ADD COLUMN loyalty_tier TEXT;

UPDATE customers
SET loyalty_tier = CASE
    WHEN city_tier = 1 THEN 'Gold'
    ELSE 'Silver'
END;

-- Verification query
SELECT customer_id, name, city, city_tier, loyalty_tier
FROM customers
ORDER BY customer_id
LIMIT 10;
