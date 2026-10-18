### 1. Purpose
- **Question:** every morning the São Paulo FC must deliver yesterday's orders. How many vehicles, which type, at what cost, and what happens on a peak day?
- **Objective:** find the cheapest fleet and routes that deliver every order within one shift, on a normal day and on Black Friday.
- **Output:** optimised routes per vehicle, the fleet size and mix, the cost per order, and a peak-day capacity gap.

### 2. The answer
**Run a mixed fleet of vans and motorbikes, and contract extra riders for peak days.**

| KPI | Normal day (63 orders) | Black Friday (248 orders) |
|---|---|---|
| Best fleet | 2 vans + 2 motorbikes | 6 vans + 9 motorbikes |
| Cost per order | R$ 23.34 | R$ 19.69 |
| Saving vs a greedy "nearest next stop" plan | −28% | −38% |
| Orders late with only the normal-day fleet | – | 130 of 248 (52%) |

### 3. Key findings
1. **A mixed fleet wins on both days.** Vans carry the bulky parcels, and motorbikes do the many small ones at a third of the cost per km.
2. **Motorbike-only looks cheap but fails service.** 4–6 orders a day are too bulky for a 90-litre box.
3. **Vans are limited by time, not space.** They run ~10% full but use the whole 9-hour shift, so stops per hour matter more than capacity.
4. **Peaks need a plan.** Black Friday has 4× the orders, and the normal fleet would leave half of them a day late.
5. **Density lowers cost.** With 4× the orders, cost per order falls (R$ 23.34 → R$ 19.69) because stops are closer together.

### 4. How we got there: steps and decisions

**Step 1 · Define the area.** The whole Grande São Paulo metro region (zip 01000–09999). São Paulo city is ~70% of orders; the rest comes from 10–22 neighbouring municipalities such as São Bernardo do Campo, Guarulhos, Osasco and Santo André.
*Why:* last-mile delivery is daily round trips from one depot. Leaving out the neighbouring cities would understate the fleet, and destinations 500+ km away go by line-haul truck instead.

**Step 2 · Use project 1's depot.** The São Paulo FC from the recommended network.
*Why:* it serves ~62% of national orders, and it links "where" (project 1) to "how" (this project).

**Step 3 · Pick real days.** Thu 1 Mar 2018 (63 orders, closest to the median Tue–Thu of Mar–May 2018) and Black Friday, 24 Nov 2017 (248 orders, the busiest day).
*Why:* real days keep the real mix of locations and parcel sizes, and the peak tests whether the plan holds.

**Step 4 · Build the orders.** One stop per order at its zip-code centroid, with weight and volume summed from product dimensions.
*Why:* the data has no street addresses, and zip level is accurate to a neighbourhood.

**Step 5 · Choose the model.** A capacitated vehicle routing problem: weight and volume limits, a 9-hour shift, a mixed fleet. The objective is the lowest cost (cost per vehicle-day + cost per km).
*Why:* it uses every constraint we have data or a sound assumption for. Customer time windows are not in the data.

**Step 6 · Solve it.** Google OR-Tools with guided local search (20–60 s). The mixed fleet starts from the van-only plan, so it can only match or beat it.
*Why:* an exact MILP is too slow for 248 stops, and OR-Tools is free and industry-standard.

**Step 7 · Compare against reality-like baselines.** A greedy "nearest next stop" dispatcher, and Black Friday with only the normal-day fleet.
*Why:* this shows what optimisation is worth (−28% to −38%) and turns "it's busy" into a number (130 late orders).

**Assumptions (illustrative):** van 650 kg / 3,300 L, 22 km/h, R$ 1.10/km + R$ 380/day. Motorbike 20 kg / 90 L, 30 km/h, R$ 0.35/km + R$ 180/day.

### 5. Risks: what would change the decision
- **Customer delivery time windows:** vans lose flexibility first, which favours a bigger motorbike share.
- **Cheaper vans** (e.g. electric): van-only gets closer to the mixed fleet.
- **Real road distances and traffic:** more vehicles are needed, but the ranking of the fleets likely stays the same.

### 6. Next step
The routes deliver what the FC has in stock. **Project 3** decides which products the FC should hold, and how many.
