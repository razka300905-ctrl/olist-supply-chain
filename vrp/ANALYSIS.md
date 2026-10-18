## Analysis: what we chose and why

### The decision in one sentence
**Deliver Grande São Paulo with a mixed fleet (vans + motorbikes) from the São Paulo FC, and contract extra riders for peak days.** On a normal day 2 vans + 2 motorbikes deliver every order at R$ 23.34 each. Black Friday needs about 15 vehicles.

### Which area does the VRP cover? One city or several?
**Several cities: the whole Grande São Paulo metropolitan region** (zip codes 01000–09999).

| | Normal day (63 orders) | Black Friday (248 orders) |
|---|---|---|
| Municipalities served | 11 | 23 |
| São Paulo city | 70% of orders | 67% of orders |
| Largest other cities | São Bernardo do Campo, Guarulhos, Osasco, Santo André | São Bernardo do Campo, Santo André, Guarulhos, Osasco, Barueri |

**Why the metro region, and not one city or the whole country?**
- **Not one city:** about 30% of orders go to neighbouring municipalities that one FC easily reaches in a day trip. Leaving them out would understate fleet needs.
- **Not all of Brazil:** last-mile delivery means daily round trips from one depot. Deliveries 500+ km away go by line-haul carrier, which is a different problem.
- **Why São Paulo:** project 1 showed the São Paulo FC serves ~62% of national orders, so it is the most important depot to plan first.

### Results: what we chose

| Choice | Why |
|---|---|
| **Mixed fleet** | Cheapest on both days (R$ 23.34 normal, R$ 19.69 Black Friday). Vans handle bulky parcels, and motorbikes do the many small ones at a third of the cost per km. |
| **Not motorbike-only** | Looks cheap, but 4–6 orders a day are too bulky for a 90-litre box, so service fails |
| **Not van-only** | Reliable but 36% more expensive per order on a normal day. Vans run ~10% full, so they pay for space they don't use. |
| **Plan peak capacity separately** | With the normal fleet, 130 of 248 Black Friday orders (52%) would be a day late. Owning a fleet sized for Black Friday would leave it idle most of the year, which makes contracted or crowd-sourced riders the better fit. |

### Modelling choices

| Decision | Options considered | Our choice | Why |
|---|---|---|---|
| **Depot** | Any warehouse · project 1's FC | **São Paulo FC from project 1** | Connects the projects: network design decides where, routing decides how |
| **Which days** | An "average" synthetic day · real days | **Two real days:** Thu 1 Mar 2018 (63 orders, closest to the median Tue–Thu of Mar–May 2018) and **Black Friday 24 Nov 2017** (248, the busiest day) | Real days keep the real mix of locations and parcel sizes. The peak tests whether the plan holds under stress. |
| **Stop location** | Street address · zip-code centroid | **Zip-code centroid** | The dataset has no addresses. Zip level is accurate to a neighbourhood. |
| **Problem type** | TSP (one vehicle) · CVRP · CVRP with customer time windows | **CVRP with weight + volume capacity, a 9-hour shift limit and a mixed fleet** | Uses every constraint we have data or a sound assumption for. Customer time windows are not in the data. |
| **Objective** | Fewest km · fewest vehicles · lowest cost | **Lowest cost** (fixed cost per vehicle + cost per km) | Balances the other two. A vehicle is expensive, but so is driving extra km. |
| **Fleet options** | Vans · motorbikes · cargo bikes · mix | **Van, motorbike and mixed** | The two standard Brazilian last-mile vehicles. Testing the mix shows whether combining beats either alone. |
| **Solver** | Exact MILP · own heuristic · Google OR-Tools | **OR-Tools, guided local search, 20–60 s time limit** | Exact MILP is too slow for 248 stops. OR-Tools is free, industry-standard and supports every constraint above. |
| **Starting point** | Solve each fleet separately · warm start | **Mixed fleet starts from the van-only plan** | Guarantees mixed ≤ van-only. Without it the search got stuck at a worse answer. |
| **Baseline** | None · greedy "nearest next stop" | **Greedy nearest-next-stop plan** | That is how a simple dispatcher plans, so it measures what optimisation is worth (−28% to −38% cost) |
| **Stress test** | Assume enough vehicles · cap the fleet | **Black Friday with only the normal-day fleet** | Turns "it's busy" into a number: 130 orders late |
| **Costs & speeds** | Real Olist figures · public benchmarks | **Illustrative assumptions** (van R$ 1.10/km + R$ 380/day; motorbike R$ 0.35/km + R$ 180/day) | Olist does not publish them. They are kept in one editable table, and conclusions rely on relative differences. |

### What would change the decision
- **Customer delivery time windows:** vans lose more flexibility than motorbikes, which favours a bigger motorbike share.
- **Cheaper vans** (e.g. electric, low cost per km): van-only gets closer to mixed.
- **Real road distances and traffic:** times go up, so more vehicles are needed. The fleet ranking likely stays the same.
