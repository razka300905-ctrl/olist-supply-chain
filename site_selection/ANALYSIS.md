## Analysis: what we chose and why

### The decision in one sentence
**Open 3 fulfilment centres, in São Paulo, the Minas Gerais/Rio corridor and the Northeast. In practice that means São Paulo + Rio de Janeiro + Salvador.** This nearly halves the distance to customers (774 → 411 km) and doubles next-day reach (27% → 58%).

### Why 3 FCs, and not 1, 2 or 5?

| FCs | What the extra FC buys | Verdict |
|---|---|---|
| 1 | A São Paulo hub alone already beats today's direct shipping (−13% km) | Too little: 62% of orders are still outside next-day reach |
| 2 | Adds the Northeast: average distance −36% vs today, but next-day reach barely moves (38% → 39%) | Helps remote customers, but not the dense South-East |
| **3** | **Adds Minas Gerais/Rio: next-day reach jumps 39% → 58%, the biggest single gain** | **The knee of the curve, so start here** |
| 4–5 | Adds the South and the Centre-West: steady but smaller gains (+4 pp each) | Phase 2, once volume grows |
| 6 | 800 km reach does not improve at all | Not worth it |

The freight saved by each extra FC falls quickly (R$ 80k → 39k → 30k → 27k → 14k a year). At today's volume, **service level, not freight cost**, is the reason to open FCs.

### Why São Paulo + Rio + Salvador instead of the model's exact sites?
The optimiser picks **Juiz de Fora (MG)** and **Lagarto (SE)** because each sits at the mathematical centre of its demand. A real company also needs workers, warehouse space and carriers. The big-metro network costs **only 4% more distance** and is far easier to run, so that is the version to take to stakeholders.

### Modelling choices

| Decision | Options considered | Our choice | Why |
|---|---|---|---|
| **Objective** | Minimise cost · minimise distance · maximise coverage | **Minimise order-weighted distance**, and report cost as a break-even | FC rent and labour costs are not in the data. Distance drives both delivery time and freight. |
| **Demand unit** | 5-digit zip (15k points) · state (27) · 3-digit zip zone (849) | **849 three-digit zones** | Detailed enough to see cities, and small enough to solve exactly |
| **What one unit of demand is** | Orders · revenue · weight | **Orders** | Each order is one delivery, i.e. one service event for a customer |
| **Candidate sites** | All 849 zones · top-N only · top 3 per state + top 60 nationally | **119 candidates (top 3 per state + top 60)** | Every region has a candidate, and the model stays exactly solvable (~100k variables) |
| **Model** | Centre of gravity · k-means clustering · maximal coverage · **p-median** | **p-median (MILP)** | The standard model for "open k sites, minimise weighted distance". It gives a proven optimum and makes the k = 1…6 trade-off easy. Centre of gravity only handles 1 site, k-means gives no proven optimum, and coverage needs an arbitrary radius. |
| **Solver** | Heuristic · exact MILP | **PuLP + HiGHS (exact)** | Free, fast (seconds per k), with proven optimality |
| **Distance** | Road-network API · straight line · straight line × 1.3 | **Haversine × 1.3** | Transparent and free. 1.3 is a common road-detour factor, and it is accurate enough to compare scenarios. |
| **Turning km into business KPIs** | Show km only · assume rates · learn from data | **Regressions on ~110k real shipments** (days and R$ against km) | Converts an abstract distance into delivery days and freight cost that stakeholders understand |
| **Data** | Raw CSVs · cleaned layer | **Cleaned layer, valid delivered orders only** | Avoids duplicate map points, broken dates and orders that never shipped |

### What would change the decision
- **3× volume growth:** freight savings scale up, and 4–5 FCs start paying for themselves.
- **High inbound cost to the Northeast:** 76% of supply sits in São Paulo, so the third FC may move to Rio/Belo Horizonte.
- **Real FC costs:** each extra FC is worth opening only if it costs less than its freight saving plus the value of faster delivery.
