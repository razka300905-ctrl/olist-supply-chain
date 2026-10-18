-- VRP - delivery orders for the São Paulo fulfilment centre.
-- Reads the CLEAN layer (data_pipeline/). Service area = Grande São Paulo (zip codes 01000-09999).
-- One row per order: where it goes, how heavy and how bulky it is.

DROP TABLE IF EXISTS vrp_orders;
CREATE TABLE vrp_orders AS
SELECT o.order_id,
       DATE(o.order_purchase_timestamp)                 AS purchase_date,
       c.customer_zip_code_prefix                       AS zip5,
       c.customer_city                                  AS city,
       g.lat, g.lng,
       COUNT(*)                                         AS n_items,
       ROUND(SUM(p.product_weight_g) / 1000.0, 3)       AS weight_kg,
       ROUND(SUM(p.product_volume_cm3) / 1000.0, 2)     AS volume_l,
       ROUND(SUM(oi.price), 2)                          AS order_value
FROM orders o
JOIN customers   c  ON c.customer_id = o.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products    p  ON p.product_id = oi.product_id
JOIN geo_zip_centroid g ON g.zip_code_prefix = c.customer_zip_code_prefix
WHERE o.is_valid_delivered = 1
  AND c.customer_zip_code_prefix < '10000'
GROUP BY o.order_id;
CREATE INDEX ix_vrp_orders_date ON vrp_orders(purchase_date);

-- Orders per purchase day (used to pick a representative normal day and the peak day)
DROP TABLE IF EXISTS vrp_daily;
CREATE TABLE vrp_daily AS
SELECT purchase_date,
       CAST(strftime('%w', purchase_date) AS INTEGER) AS weekday,   -- 0 = Sunday
       COUNT(*)                                       AS orders,
       ROUND(SUM(weight_kg), 1)                       AS weight_kg,
       ROUND(SUM(volume_l), 1)                        AS volume_l
FROM vrp_orders
GROUP BY purchase_date;
