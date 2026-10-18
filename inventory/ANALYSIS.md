### 1. Purpose
- **Question:** about 19,000 different products reached the São Paulo FC's area in one year. Which should the FC hold, how many of each, and when should it reorder?
- **Objective:** ship as many units as possible from FC stock while keeping capital, space and costs under control.
- **Output:** the stock list, the reorder point and order quantity per product, the service-level trade-offs, and a day-by-day test of the policy on 16 unseen weeks.

### 2. The answer
**Stock only the ~130 most regular products (sold in ≥6 of the last 12 weeks), re-plan every Monday, and target a 95% service level. Sellers keep shipping everything else directly.**

| KPI | Result |
|---|---|
| Products in the FC | 132 of ~19,000 |
| Share of São Paulo units shipped from the FC | 13% |
| Fill rate on stocked products | 89.8% |
| Average stock | R$ 153k (~20 m³, 11 weeks of cover) |
| Inventory cost per unit served | R$ 17.97 |

### 3. Key findings
1. **The assortment turns over fast.** 52% of test-period units came from products with no sales in the previous 34 weeks. Volume is stable, but the products change, so the plan must be rebuilt every week.
2. **Going deeper costs more per unit.** Stocking 651 products doubles the FC share (25%), but almost doubles the cost (R$ 33.95/unit) and holds 16.5 weeks of stock.
3. **Service levels above 95% buy nothing.** From 50% to 95%, fill rate rises ~3 points for R$ 27k more stock. Above that only the stock grows.
4. **Simple forecasts win.** Weekly demand per product is very noisy. A 4-week moving average beats exponential smoothing and Croston, which forecast too high because products fade after their peak.
5. **The FC is a speed play.** Inventory costs R$ 18 per unit against ~R$ 3 of freight saved (project 1). It pays off through faster delivery, or through sellers paying fulfilment and storage fees (the Amazon FBA model).

### 4. How we got there: steps and decisions

**Step 1 · Define the FC's demand.** Valid delivered items from the zip regions that project 1 assigns to the São Paulo FC (62% of national items).
*Why:* it is the biggest FC and the same depot as project 2.

**Step 2 · Split time honestly.** 34 calibration weeks (Sep 2017–Apr 2018) and 16 test weeks (May–Aug 2018).
*Why:* plans and forecasts only ever see the past, as they would in real life.

**Step 3 · Segment the products.** ABC by revenue, crossed with the Syntetos-Boylan demand pattern (smooth / erratic / intermittent / lumpy).
*Why:* this is the standard for sparse e-commerce demand. Most candidate products are intermittent (they don't sell every week).

**Step 4 · Choose the stock list.** Products sold in ≥6 of the last 12 weeks, rebuilt every Monday.
*Why:* recent, regular demand. We compared ≥3, ≥6 and ≥9 of 12 weeks, and ≥6 balances FC share against cost per unit.

**Step 5 · Choose the forecast.** A 4-week moving average.
*Why:* in a 16-week backtest it was within 2 points of the most accurate method (naive, 109% vs 111% WAPE) but steadier.
*Alternatives considered:* exponential smoothing (+28% bias) and Croston (+12% bias).

**Step 6 · Set the stock policy.** Reorder point = lead-time demand + safety stock (z × σ × √lead time). Order quantity = min(EOQ, 8 weeks of demand).
*Why:* a standard, explainable policy. Pure EOQ is 7% cheaper but holds 16 weeks of stock; a 4-week cap means too many small orders.

**Step 7 · Set the lead time.** Each seller's handling time from the data (median ~2 days) + 2 days transit + 1 day receiving ≈ 6 days.

**Step 8 · Test it day by day.** Real daily orders, 4 warm-up weeks, and a weekly re-plan. Unserved demand is shipped by the seller (no lost sale), and stock of delisted products is returned to the seller.
*Why:* this shows what the policy really achieves, including stockouts and ageing stock.

**Assumptions (illustrative):** holding cost 25% of value per year, R$ 40 per replenishment or removal order, customer price used as the unit value.

**Why the fill rate is ~90% and not 95%:** newly listed products wait one lead time (~6 days) for their first delivery, and single large orders can exceed the stock on hand.

### 5. Risks: what would change the decision
- **Sellers pay storage and fulfilment fees:** Olist's cost falls, so a deeper assortment becomes attractive.
- **Faster inbound** (6 → 3 days): less safety stock, and better fill on new listings.
- **A more stable assortment:** a fixed list becomes viable, and it is cheaper per unit (R$ 11.71).

### 6. Next step
This closes the loop: **where** the FCs are (project 1), **how** they deliver (project 2), and **what** they hold (project 3). A natural extension is a fulfilment-fee model that tests what sellers would pay for faster delivery.
