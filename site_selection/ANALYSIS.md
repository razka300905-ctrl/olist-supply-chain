### 1. Purpose
- **Question:** if Olist moves from "every seller ships" to its own fulfilment centres (FCs), how many should it open, and where?
- **Objective:** find the number and location of FCs that bring orders closest to customers, and show what each extra FC is worth.
- **Output:** a recommended network, a 1–6 FC trade-off curve, the KPIs per scenario, and a map of which FC serves which region.

### 2. The answer
**Open 3 FCs: São Paulo, the Minas Gerais/Rio corridor, and the Northeast. In practice that means São Paulo + Rio de Janeiro + Salvador.**

| KPI | Today | 3 FCs | Change |
|---|---|---|---|
| Average distance to customer | 774 km | 411 km | −47% |
| Orders within 300 km (next-day reach) | 27% | 58% | +30 pp |
| Estimated delivery time | 12.2 days | 10.6 days | −1.7 days |
| Estimated freight per item | R$ 19.9 | R$ 17.0 | −15% |

### 3. Key findings
1. **3 FCs is the knee of the curve.** The 3rd FC lifts next-day reach from 39% to 58%, the biggest jump of any step. After 5 FCs the curve is flat.
2. **Big metros cost almost nothing extra.** The model's exact sites (Juiz de Fora, Lagarto) are only 4% better on distance than São Paulo + Rio + Salvador, which are far easier to staff and supply.
3. **FCs are about speed, not freight.** Each extra FC saves only R$ 80k → 39k → 30k → 27k → 14k of freight a year. The business case is faster delivery.
4. **Supply is concentrated, demand is not.** 76% of items ship from São Paulo state, but only 42% of orders go there. That mismatch is why parcels travel ~775 km today.

### 4. How we got there: steps and decisions

**Step 1 · Clean the data.** We used valid delivered orders only, with one median coordinate per zip code.
*Why:* the raw files have duplicated map points, coordinates outside Brazil and orders that never shipped.

**Step 2 · Group demand into regions.** Orders were grouped into 849 three-digit zip regions, weighted by number of orders.
*Why:* 5-digit zips (15k points) are too many to solve exactly, and 27 states are too coarse. One order is one delivery, so orders, not revenue, measure the service need.

**Step 3 · Choose candidate sites.** The top 3 regions per state plus the top 60 nationally, 119 candidates in total.
*Why:* every region gets a candidate, and the model stays small enough (~100k variables) for a proven optimum.

**Step 4 · Choose the model.** A p-median model, solved exactly with PuLP + HiGHS for k = 1…6. It opens k sites and minimises order-weighted road distance.
*Why:* it is the standard model for "open k sites, serve demand as close as possible".
*Alternatives considered:* centre of gravity (handles one site only), k-means (no proven optimum), maximal coverage (needs an arbitrary radius).

**Step 5 · Measure distance.** Straight-line distance × 1.3.
*Why:* transparent and free. 1.3 is a common road-detour factor, and it is accurate enough to compare scenarios.

**Step 6 · Turn km into business KPIs.** Two regressions on ~110k real shipments: delivery days ≈ 8.6 + 0.47 per 100 km, and freight ≈ R$ 8.2 + 0.82 per 100 km + 2.58 per kg.
*Why:* managers decide on days and Reais, not kilometres.

**Step 7 · Pick the network.** 3 FCs (the knee), then swap the mathematical sites for the nearest big metros (+4% distance).

### 5. Risks: what would change the decision
- **Volume grows ~3×:** freight savings scale up, and 4–5 FCs start to pay for themselves.
- **Inbound cost to the Northeast is high:** supply sits in São Paulo, so the 3rd FC may shift to Rio/Belo Horizonte.
- **Real FC costs:** an FC is worth opening only if it costs less than its freight saving plus the value of faster delivery.

### 6. Next step
The São Paulo FC serves ~62% of orders. **Project 2** plans its daily delivery routes, and **Project 3** decides what it should stock.
