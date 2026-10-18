### 1. Purpose
- **Question:** about 19,000 different products reached the São Paulo FC's area in one year. Which should the FC hold, how many of each, and when should it reorder?
- **Objective:** ship as many units as possible from FC stock while keeping capital, space and costs under control.
- **Output:** a stock list, the reorder point and order quantity per product, service-level trade-offs, a forecast-method comparison, and a day-by-day test of the policy on 16 unseen weeks.

### 2. The answer
**Stock only the ~130 most regular products (sold in ≥6 of the last 12 weeks), forecast them with exponential smoothing, re-plan every Monday, and target a 95% service level. Sellers keep shipping everything else directly.**

| KPI | Result |
|---|---|
| Products in the FC | 132 of ~19,000 |
| Share of São Paulo units shipped from the FC | 13% |
| Fill rate on stocked products | 89.6% |
| Average stock | R$ 139k (~19 m³, 10 weeks of cover) |
| Inventory cost per unit served | R$ 16.84 |

### 3. Key findings
1. **The assortment turns over fast.** 52% of test-period units came from products with no sales in the previous 34 weeks. Volume is stable, but the products change, so the plan must be rebuilt every week.
2. **Going deeper costs more per unit.** Stocking 651 products doubles the FC share (25%), but nearly doubles the cost (R$ 32.57/unit) and holds 14.6 weeks of stock.
3. **Service levels above 95% buy nothing.** From 50% to 95%, fill rate rises ~3 points for R$ 20k more stock. Above that, only the stock grows.
4. **Pick the forecast by its effect on stock, not only by its error.** The two error metrics rank the methods differently. In the stock simulation, exponential smoothing gives the same fill rate as a moving average with ~9% less stock.
5. **Holt-Winters wins where there is seasonality.** For the FC's total daily volume (clear weekday pattern), it cuts forecast error by ~28%.
6. **The FC is a speed play.** Inventory costs ~R$ 17 per unit against ~R$ 3 of freight saved (project 1). It pays off through faster delivery, or through sellers paying fulfilment and storage fees (the Amazon FBA model).

### 4. How we got there: steps and decisions

**Step 1 · Define the FC's demand.** Valid delivered items from the zip regions that project 1 assigns to the São Paulo FC (62% of national items).
*Why:* it is the biggest FC and the same depot as project 2.

**Step 2 · Split time honestly.** 34 calibration weeks (Sep 2017–Apr 2018) and 16 test weeks (May–Aug 2018).
*Why:* plans and forecasts only ever see the past, as they would in real life.

**Step 3 · Segment the products.** ABC by revenue, crossed with the Syntetos-Boylan demand pattern (smooth / erratic / intermittent / lumpy).
*Why:* this is the standard for sparse e-commerce demand. Most candidate products are intermittent (they don't sell every week).

**Step 4 · Choose the stock list.** Products sold in ≥6 of the last 12 weeks, rebuilt every Monday.
*Why:* recent, regular demand. We compared ≥3, ≥6 and ≥9 of 12 weeks, and ≥6 balances FC share against cost per unit.

**Step 5 · Choose the forecast, at two levels.**

*Level A: per product, per week (drives the stock).* Seven methods were compared over 16 unseen weeks:

| Method | WAPE | Scaled RMSE | Bias | Stock needed (simulation) | Fill rate |
|---|---|---|---|---|---|
| Naive | 109% | 232% | +7% | R$ 196k | 90.6% |
| Moving average (4 wk) | 111% | 217% | +14% | R$ 153k | 89.8% |
| **Exp. smoothing (SES)** | 118% | **202%** | +28% | **R$ 139k** | **89.6%** |
| Holt | 124% | 215% | +40% | R$ 152k | 89.4% |
| Holt damped | 118% | 207% | +28% | R$ 147k | 89.3% |
| Croston (SBA) | 132% | 224% | +12% | R$ 92k | 87.0% |
| TSB | 131% | 215% | +35% | R$ 113k | 88.6% |

- **WAPE** favours forecasts near zero, because most weeks have no sale. That flatters naive.
- **Scaled RMSE** rewards getting the average right, which is what stock depends on. SES wins.
- **Decision:** SES. It keeps the fill rate of the moving average with ~9% less stock and ~6% lower cost per unit.
- Holt adds nothing because the products have no trend. Croston and TSB hold little stock but miss more orders.
- **Holt-Winters is not usable here.** It needs at least two full seasons (2 × 52 weeks of history), and weeks full of zeros have no seasonal shape.

*Level B: FC total, per day (drives staffing and the daily fleet).* The daily total is smooth, with a clear weekday pattern: Monday/Tuesday are +13% vs average, Saturday is −24%. Each method forecast 7 days ahead, every Monday for 16 weeks:

| Method | WAPE | Bias |
|---|---|---|
| **Holt-Winters (multiplicative)** | **19.0%** | −0.6% |
| Seasonal ES (no trend) | 19.4% | −4.1% |
| Holt-Winters (additive) | 19.4% | −3.9% |
| Seasonal naive | 24.2% | −1.2% |
| Moving average (7 days) | 26.4% | −1.2% |
| SES / Holt / Holt damped | 26.8% | −13% |
| Naive | 28.2% | −16.8% |

- **Decision:** Holt-Winters (multiplicative) for daily volume. The weekday season does the work; the trend term adds almost nothing.

**Step 6 · Set the stock policy.** Reorder point = lead-time demand + safety stock (z × σ × √lead time). Order quantity = min(EOQ, 8 weeks of demand).
*Why:* a standard, explainable policy. Pure EOQ is 2% cheaper but holds 15 weeks of stock; a 4-week cap means too many small orders (R$ 20.39/unit).

**Step 7 · Set the lead time.** Each seller's handling time from the data (median ~2 days) + 2 days transit + 1 day receiving ≈ 6 days.

**Step 8 · Test it day by day.** Real daily orders, 4 warm-up weeks, and a weekly re-plan. Unserved demand is shipped by the seller (no lost sale), and stock of delisted products is returned to the seller.
*Why:* this shows what the policy really achieves, including stockouts and ageing stock.

**Assumptions (illustrative):** holding cost 25% of value per year, R$ 40 per replenishment or removal order, customer price used as the unit value.

**Why the fill rate is ~90% and not 95%:** newly listed products wait one lead time (~6 days) for their first delivery, and single large orders can exceed the stock on hand.

### 5. Risks: what would change the decision
- **Sellers pay storage and fulfilment fees:** Olist's cost falls, so a deeper assortment becomes attractive.
- **Faster inbound** (6 → 3 days): less safety stock, and better fill on new listings.
- **A more stable assortment:** a fixed list becomes viable, and it is cheaper per unit (R$ 11.02).
- **Two or more years of history:** yearly seasonality (e.g. Black Friday) could then be modelled at product or category level.

### 6. Next step
This closes the loop: **where** the FCs are (project 1), **how** they deliver (project 2), and **what** they hold (project 3). The daily Holt-Winters forecast can feed project 2 directly, to size each day's fleet in advance.
