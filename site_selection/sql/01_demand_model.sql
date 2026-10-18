-- Site selection - demand, supply and candidate tables.
-- Reads the CLEAN layer built by data_pipeline/ (01_load_raw.py + 02_clean.py).
-- All objects are recreated each run.

-- 2.1 One coordinate per 5-digit zip prefix: the cleaned median centroid from the pipeline
-- (outside-Brazil points and duplicates already removed, missing zips filled from 3-digit zone).
DROP VIEW IF EXISTS zip_centroid;
DROP TABLE IF EXISTS zip_centroid;
CREATE VIEW zip_centroid AS
SELECT zip_code_prefix AS zip5, lat, lng, state FROM geo_zip_centroid;

-- 2.2 Item-level fact table for delivered orders, with customer and seller location.
DROP TABLE IF EXISTS fact_delivered_items;
CREATE TABLE fact_delivered_items AS
SELECT o.order_id,
       oi.order_item_id,
       o.order_purchase_timestamp,
       o.delivery_days,
       oi.price,
       oi.freight_value,
       p.product_weight_g / 1000.0 AS weight_kg,
       c.customer_zip_code_prefix AS cust_zip5,
       c.customer_state           AS cust_state,
       s.seller_zip_code_prefix   AS sell_zip5,
       s.seller_state             AS sell_state
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers   c  ON c.customer_id = o.customer_id
JOIN sellers     s  ON s.seller_id = oi.seller_id
JOIN products    p  ON p.product_id = oi.product_id
WHERE o.is_valid_delivered = 1;

-- 2.3 Demand zones = 3-digit zip prefix (Brazil "sub-region", ~850 zones).
-- Coordinates are the order-weighted centroid of the 5-digit zips inside the zone.
DROP TABLE IF EXISTS demand_zone;
CREATE TABLE demand_zone AS
WITH per_zip AS (
    SELECT f.cust_zip5,
           MAX(f.cust_state)            AS state,
           COUNT(DISTINCT f.order_id)   AS orders,
           COUNT(*)                     AS items,
           SUM(f.weight_kg)             AS weight_kg,
           SUM(f.price)                 AS revenue,
           SUM(f.freight_value)         AS freight
    FROM fact_delivered_items f
    GROUP BY f.cust_zip5
)
SELECT SUBSTR(z.cust_zip5, 1, 3)                     AS zone,
       MAX(z.state)                                  AS state,
       SUM(z.orders)                                 AS orders,
       SUM(z.items)                                  AS items,
       ROUND(SUM(z.weight_kg), 1)                    AS weight_kg,
       ROUND(SUM(z.revenue), 2)                      AS revenue,
       ROUND(SUM(z.freight), 2)                      AS freight,
       SUM(g.lat * z.orders) / SUM(z.orders)         AS lat,
       SUM(g.lng * z.orders) / SUM(z.orders)         AS lng
FROM per_zip z
JOIN zip_centroid g ON g.zip5 = z.cust_zip5
GROUP BY SUBSTR(z.cust_zip5, 1, 3);

-- 2.4 Supply zones: where sellers ship from (inbound flow into a fulfilment centre).
DROP TABLE IF EXISTS supply_zone;
CREATE TABLE supply_zone AS
SELECT SUBSTR(f.sell_zip5, 1, 3)               AS zone,
       MAX(f.sell_state)                       AS state,
       COUNT(*)                                AS items,
       SUM(g.lat) / COUNT(*)                   AS lat,
       SUM(g.lng) / COUNT(*)                   AS lng
FROM fact_delivered_items f
JOIN zip_centroid g ON g.zip5 = f.sell_zip5
GROUP BY SUBSTR(f.sell_zip5, 1, 3);

-- 2.5 Candidate sites: top 3 demand zones in every state + top 60 zones nationally.
-- Keeps the model small enough to solve exactly while covering every region.
DROP TABLE IF EXISTS candidate_site;
CREATE TABLE candidate_site AS
WITH ranked AS (
    SELECT d.*,
           ROW_NUMBER() OVER (PARTITION BY state ORDER BY orders DESC) AS rank_in_state,
           ROW_NUMBER() OVER (ORDER BY orders DESC)                    AS rank_national
    FROM demand_zone d
)
SELECT zone, state, lat, lng, orders, rank_in_state, rank_national
FROM ranked
WHERE rank_in_state <= 3 OR rank_national <= 60;

-- 2.6 As-is baseline: actual seller -> customer pairs (used for the
-- distance -> delivery-days and distance -> freight regressions in Python).
DROP TABLE IF EXISTS asis_shipments;
CREATE TABLE asis_shipments AS
SELECT f.order_id,
       f.delivery_days,
       f.freight_value,
       f.weight_kg,
       f.cust_state,
       f.sell_state,
       gc.lat AS cust_lat, gc.lng AS cust_lng,
       gs.lat AS sell_lat, gs.lng AS sell_lng
FROM fact_delivered_items f
JOIN zip_centroid gc ON gc.zip5 = f.cust_zip5
JOIN zip_centroid gs ON gs.zip5 = f.sell_zip5;
