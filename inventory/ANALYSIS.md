## Analysis: what we chose and why

### The decision in one sentence
**Stock only the ~130 products that sold in at least 6 of the last 12 weeks. Re-plan the list and the reorder points every Monday, target a 95% service level, and let sellers keep shipping everything else directly.** The FC then ships 13% of São Paulo units, with about R$ 153k of stock (20 m³), at R$ 17.97 of inventory cost per unit.

### The finding that shaped everything: the assortment turns over fast
- In the 16 test weeks, **52% of units came from products that had no sales at all in the previous 34 weeks.**
- Total demand stayed stable (about 1,100 units a week). The *products* changed, not the volume.
- So a product list fixed once goes stale within weeks. **Weekly re-planning** is not a refinement here; it is required.

### Results: what we chose

| Choice | Options compared | Result | Why |
|---|---|---|---|
| **Which products** | Sold in ≥3, ≥6 or ≥9 of the last 12 weeks | **≥6 → 132 products, 13% of units, R$ 17.97/unit, 11.2 weeks of cover** | ≥3 doubles the FC share (25%), but costs R$ 33.95/unit with 16.5 weeks of stock. ≥9 is cheapest (R$ 11.99) but ships only 6% of units. ≥6 is the balance. |
| **Re-plan weekly** | List fixed once vs. re-planned every Monday | **Weekly: 13% FC share, 11.2 wk cover** (fixed list: 9%, 15.8 wk) | A fixed list is cheaper per unit (R$ 11.71) but ships 30% fewer units, and its stock ages on products that stopped selling |
| **Service level** | 50% (no safety stock) to 99% | **95%: fill rate 89.8%, stock R$ 153k** | 50% → 95% adds ~3 points of fill rate for R$ 27k more stock. Above 95% nothing improves. |
| **Order size** | Cap at 4 weeks · cap at 8 weeks · pure EOQ | **8-week cap: R$ 17.97/unit, 11.2 wk cover** | Pure EOQ is 7% cheaper on paper but holds 16 weeks of stock. A 4-week cap means many small orders (R$ 22.58/unit). |
| **Forecast method** | Naive · moving average (4 wk) · exponential smoothing · Croston | **Moving average, 4 weeks** | Within 2 points of naive on error (111% vs 109% WAPE) but steadier week to week. Smoothing and Croston forecast too high (+28%, +12%) because products fade after their peak. |

### Why the fill rate is ~90% and not 95%
"95% service level" sets the safety stock per replenishment cycle. The fill rate is lower for two reasons:
- **newly listed products start with an empty shelf** and wait one lead time (~6 days) for their first delivery;
- **demand that arrives in one big order** can exceed the stock on hand.

The missed units are not lost. The seller ships them directly, exactly as Olist works today.

### How this connects to projects 1 and 2
- **Project 1** showed that the case for FCs is *faster delivery, not cheaper freight* (an FC saves about R$ 3 of freight per item). Here, inventory costs **R$ 18 per unit**. Stocking the FC therefore has to be justified by speed and conversion, or paid by sellers through **fulfilment and storage fees** (the Amazon FBA model).
- The FC's demand area comes from project 1. The units it ships go out on the routes planned in **project 2**.

### Modelling choices

| Decision | Options considered | Our choice | Why |
|---|---|---|---|
| **Scope** | All of Brazil · one FC | **São Paulo FC** (62% of national items in the 3-FC network) | The biggest FC, and the same depot as project 2 |
| **Time windows** | Random split · time-ordered | **34 calibration weeks (Sep 2017–Apr 2018) → 16 test weeks (May–Aug 2018)** | Forecasts and plans only ever see the past, the way they would in real life |
| **Segmentation** | ABC only · ABC + demand pattern | **ABC (revenue) × Syntetos-Boylan pattern** (smooth / erratic / intermittent / lumpy) | The standard way to classify sparse e-commerce demand. Most stocked products are *intermittent* (they don't sell every week). |
| **Stock policy** | Periodic review · continuous review (s, Q) | **Reorder point + order quantity, checked daily** | Standard for a warehouse with daily inbound. Simple to explain and to run. |
| **Safety stock** | Fixed days of cover · statistical | **z × σ(weekly demand) × √(lead time / 7)** | Ties stock directly to demand variability and lead time |
| **Lead time** | Fixed · from data | **Seller handling time (data, median 2 days) + 2 days transit + 1 day receiving ≈ 6 days** | Uses each seller's real handling speed |
| **Unserved demand** | Lost sale · back-order · seller ships it | **Seller ships it directly** | That is the marketplace's current model, so a stockout costs speed, not the sale |
| **Delisted products** | Keep the stock · return it to the seller | **Return to the seller (R$ 40 per removal order)** | Avoids paying to store products that no longer sell |
| **Evaluation** | Formulas only · day-by-day simulation | **Simulation on real daily orders, with 4 warm-up weeks** | Shows what the policy actually achieves, including stockouts and ageing stock |
| **Costs** | Olist figures · assumptions | **Holding 25%/year of value, R$ 40 per replenishment or removal order** | Not published by Olist. The conclusions rely on relative differences between options. |

### What would change the decision
- **Sellers pay storage and fulfilment fees:** Olist's own cost falls, so a deeper assortment (≥3 of 12 weeks) becomes attractive.
- **Faster inbound** (lead time 6 → 3 days): less safety stock is needed and the fill rate on new listings improves.
- **More stable demand** (fewer new products each month): a fixed list becomes viable and cheaper.
