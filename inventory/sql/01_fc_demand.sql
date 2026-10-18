-- Inventory - demand that the São Paulo FC would serve.
-- Reads the CLEAN layer plus fc_zone_map (loaded from project 1: which FC serves each 3-digit zip zone
-- in the recommended 3-FC network). One row per order item.

DROP TABLE IF EXISTS inv_demand;
CREATE TABLE inv_demand AS
SELECT oi.order_id,
       oi.product_id,
       p.product_category_name_english                     AS category,
       DATE(o.order_purchase_timestamp)                    AS order_date,
       oi.price,
       p.product_weight_g / 1000.0                          AS weight_kg,
       p.product_volume_cm3 / 1000.0                        AS volume_l,
       oi.seller_id,
       s.seller_state
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers   c  ON c.customer_id = o.customer_id
JOIN products    p  ON p.product_id = oi.product_id
JOIN sellers     s  ON s.seller_id = oi.seller_id
JOIN fc_zone_map m  ON m.zone = SUBSTR(c.customer_zip_code_prefix, 1, 3)
WHERE o.is_valid_delivered = 1
  AND m.fc_state = 'SP';
CREATE INDEX ix_inv_demand_product ON inv_demand(product_id);

-- Seller handling time (order approved -> handed to carrier): the seller's share of the
-- replenishment lead time when the seller ships stock to the FC.
DROP TABLE IF EXISTS inv_seller_handling;
CREATE TABLE inv_seller_handling AS
SELECT oi.seller_id,
       COUNT(DISTINCT o.order_id)                                                         AS orders,
       AVG(julianday(o.order_delivered_carrier_date) - julianday(o.order_approved_at))     AS avg_handling_days
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.is_valid_delivered = 1
  AND o.order_delivered_carrier_date >= o.order_approved_at
GROUP BY oi.seller_id;
