"""Step 2 - Solve the daily last-mile routing problem from the São Paulo FC (CVRPTW, OR-Tools).

Model: every order must be visited once; each vehicle starts and ends at the FC, respects its
weight and volume capacity, and must be back within one shift. Objective = minimise cost
(fixed cost per vehicle used + cost per km). Solved with guided local search; a greedy
"nearest next stop" first solution is kept as the baseline.

Scenarios: {normal day, Black Friday} x {van only, motorbike only, mixed fleet}
           + Black Friday with only the normal-day fleet (what is left undelivered?).
All operating assumptions live in VEHICLES / SHIFT_MIN below and are illustrative.
"""
from pathlib import Path
import math
import time

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
SITES = HERE.parent / "site_selection" / "outputs" / "selected_sites.csv"

ROAD_FACTOR = 1.3      # straight line -> road distance (same as project 1)
SHIFT_MIN = 9 * 60     # one driver shift, depot to depot
DROP_PENALTY = 10**8   # cost (centavos) of leaving an order undelivered - forces service when feasible

# Illustrative operating assumptions (Brazilian urban last-mile, 2018 prices)
VEHICLES = {
    "van": {"weight_kg": 650, "volume_l": 3300, "speed_kmh": 22, "service_min": 10,
            "cost_per_km": 1.10, "cost_per_day": 380},
    "motorbike": {"weight_kg": 20, "volume_l": 90, "speed_kmh": 30, "service_min": 5,
                  "cost_per_km": 0.35, "cost_per_day": 180},
}
FLEETS = {"van_only": ["van"], "motorbike_only": ["motorbike"], "mixed": ["van", "motorbike"]}


def road_km_matrix(lat, lng):
    lat, lng = np.radians(lat), np.radians(lng)
    dlat = lat[:, None] - lat[None, :]
    dlng = lng[:, None] - lng[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlng / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a)) * ROAD_FACTOR


def fits(order, vtype):
    v = VEHICLES[vtype]
    return order.weight_kg <= v["weight_kg"] and order.volume_l <= v["volume_l"]


def solve(orders, depot, fleet_types, max_per_type=None, time_limit_s=30, first_only=False, initial_routes=None):
    """Build and solve one model; returns (kpis, routes). Orders no allowed vehicle can carry are left out.
    initial_routes: optional list of order_id lists, used as the starting solution for the first vehicles."""
    can_carry = orders.apply(lambda o: any(fits(o, t) for t in fleet_types), axis=1)
    model_orders = orders[can_carry].reset_index(drop=True)
    too_big = int((~can_carry).sum())

    lat = np.r_[depot[0], model_orders.lat.to_numpy()]
    lng = np.r_[depot[1], model_orders.lng.to_numpy()]
    km = road_km_matrix(lat, lng)
    n = len(lat)
    meters = np.rint(km * 1000).astype(int)
    weight_g = np.r_[0, np.rint(model_orders.weight_kg * 1000).astype(int)]
    volume_dl = np.r_[0, np.rint(model_orders.volume_l * 10).astype(int)]

    # Vehicle list: enough of each type that the fleet never limits the optimum (unless max_per_type).
    # Bounds come from the stops one vehicle can do in a shift; main() warns if a bound is ever reached.
    vehicles = []
    for t in fleet_types:
        cap = (max_per_type or {}).get(t, math.ceil(n / (5 if t == "motorbike" else 15)) + 3)
        vehicles += [t] * cap

    manager = pywrapcp.RoutingIndexManager(n, len(vehicles), 0)
    routing = pywrapcp.RoutingModel(manager)
    node = manager.IndexToNode

    cost_cb, time_cb = {}, {}
    for t in fleet_types:
        v = VEHICLES[t]
        cents_per_m = v["cost_per_km"] * 100 / 1000
        m_per_s = v["speed_kmh"] * 1000 / 3600
        service_s = v["service_min"] * 60
        cost_cb[t] = routing.RegisterTransitCallback(
            lambda i, j, c=cents_per_m: int(meters[node(i), node(j)] * c))
        time_cb[t] = routing.RegisterTransitCallback(
            lambda i, j, s=m_per_s, sv=service_s: int(meters[node(i), node(j)] / s) + (sv if node(i) else 0))

    for vid, t in enumerate(vehicles):
        routing.SetArcCostEvaluatorOfVehicle(cost_cb[t], vid)
        routing.SetFixedCostOfVehicle(int(VEHICLES[t]["cost_per_day"] * 100), vid)

    routing.AddDimensionWithVehicleTransits([time_cb[t] for t in vehicles], 0, SHIFT_MIN * 60, True, "Time")
    w_cb = routing.RegisterUnaryTransitCallback(lambda i: int(weight_g[node(i)]))
    v_cb = routing.RegisterUnaryTransitCallback(lambda i: int(volume_dl[node(i)]))
    routing.AddDimensionWithVehicleCapacity(w_cb, 0, [VEHICLES[t]["weight_kg"] * 1000 for t in vehicles], True, "Weight")
    routing.AddDimensionWithVehicleCapacity(v_cb, 0, [VEHICLES[t]["volume_l"] * 10 for t in vehicles], True, "Volume")

    # Orders a vehicle type cannot carry may not be assigned to it; every order may be dropped at a high penalty
    for i in range(1, n):
        o = model_orders.iloc[i - 1]
        banned = [vid for vid, t in enumerate(vehicles) if not fits(o, t)]
        if banned:
            routing.VehicleVar(manager.NodeToIndex(i)).RemoveValues(banned)
        routing.AddDisjunction([manager.NodeToIndex(i)], DROP_PENALTY)

    def params(first_only):
        p = pywrapcp.DefaultRoutingSearchParameters()
        p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        if first_only:
            p.solution_limit = 1
            p.time_limit.seconds = time_limit_s
        else:
            p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            p.time_limit.seconds = time_limit_s
        return p

    def extract(sol):
        time_dim = routing.GetDimensionOrDie("Time")
        rows, served = [], set()
        route_no = 0
        for vid, t in enumerate(vehicles):
            idx = routing.Start(vid)
            if routing.IsEnd(sol.Value(routing.NextVar(idx))):
                continue
            route_no += 1
            seq, dist, w, vol = 0, 0.0, 0.0, 0.0
            stops = []
            while not routing.IsEnd(idx):
                nxt = sol.Value(routing.NextVar(idx))
                a, b = node(idx), node(nxt)
                if a:
                    o = model_orders.iloc[a - 1]
                    served.add(o.order_id)
                    w, vol = w + o.weight_kg, vol + o.volume_l
                stops.append((a, sol.Min(time_dim.CumulVar(idx)) / 60, dist))
                dist += km[a, b]
                idx = nxt
            stops.append((0, sol.Min(time_dim.CumulVar(idx)) / 60, dist))
            for seq, (a, minute, d) in enumerate(stops):
                o = model_orders.iloc[a - 1] if a else None
                rows.append({
                    "route": route_no, "vehicle_type": t, "seq": seq,
                    "order_id": o.order_id if a else "FC", "city": o.city if a else "FC Sao Paulo",
                    "lat": lat[a], "lng": lng[a], "arrival_min": round(minute, 1), "cum_km": round(d, 2),
                    "route_km": round(dist, 2), "route_min": round(stops[-1][1], 1),
                    "route_weight_kg": round(w, 2), "route_volume_l": round(vol, 1),
                    "weight_util_pct": round(w / VEHICLES[t]["weight_kg"] * 100, 1),
                    "volume_util_pct": round(vol / VEHICLES[t]["volume_l"] * 100, 1),
                })
        routes = pd.DataFrame(rows)
        per_route = routes.drop_duplicates("route") if len(routes) else routes
        n_served = len(served)
        cost = sum(VEHICLES[r.vehicle_type]["cost_per_day"] + VEHICLES[r.vehicle_type]["cost_per_km"] * r.route_km
                   for r in per_route.itertuples())
        kpi = {
            "orders": len(orders), "orders_served": n_served,
            "orders_not_delivered": len(orders) - n_served, "orders_too_big_for_fleet": too_big,
            "vans": int((per_route.vehicle_type == "van").sum()) if len(per_route) else 0,
            "motorbikes": int((per_route.vehicle_type == "motorbike").sum()) if len(per_route) else 0,
            "total_km": per_route.route_km.sum() if len(per_route) else 0,
            "total_cost": cost,
            "avg_route_hours": per_route.route_min.mean() / 60 if len(per_route) else 0,
            "max_route_hours": per_route.route_min.max() / 60 if len(per_route) else 0,
            "avg_stops_per_route": n_served / max(len(per_route), 1),
            "avg_volume_util_pct": per_route.volume_util_pct.mean() if len(per_route) else 0,
        }
        kpi["km_per_order"] = kpi["total_km"] / max(n_served, 1)
        kpi["cost_per_order"] = cost / max(n_served, 1)
        return kpi, routes

    p = params(first_only)
    if initial_routes:
        node_of = {oid: i + 1 for i, oid in enumerate(model_orders.order_id)}
        start = [[node_of[o] for o in r if o in node_of] for r in initial_routes]
        start += [[] for _ in range(len(vehicles) - len(start))]
        routing.CloseModelWithParameters(p)
        sol = routing.SolveFromAssignmentWithParameters(routing.ReadAssignmentFromRoutes(start, True), p)
    else:
        sol = routing.SolveWithParameters(p)
    kpi, routes = extract(sol)
    kpi["fleet_bound_reached"] = any(
        (routes.drop_duplicates("route").vehicle_type == t).sum() >= vehicles.count(t) for t in fleet_types
    ) if len(routes) and not max_per_type else False
    return kpi, routes


def run(orders, depot, fleet_types, max_per_type=None, time_limit_s=30, initial_routes=None):
    """Greedy baseline and optimised solution on identical (freshly built) models."""
    t0 = time.perf_counter()
    base_kpi, _ = solve(orders, depot, fleet_types, max_per_type, time_limit_s, first_only=True)
    t1 = time.perf_counter()
    kpi, routes = solve(orders, depot, fleet_types, max_per_type, time_limit_s, initial_routes=initial_routes)
    print(f"  (baseline {t1 - t0:.0f}s, optimised {time.perf_counter() - t1:.0f}s)", flush=True)
    kpi["baseline_km"] = base_kpi["total_km"]
    kpi["baseline_cost"] = base_kpi["total_cost"]
    kpi["baseline_vehicles"] = base_kpi["vans"] + base_kpi["motorbikes"]
    kpi["cost_saving_vs_baseline_pct"] = (1 - kpi["total_cost"] / base_kpi["total_cost"]) * 100
    return kpi, routes


def main() -> None:
    sites = pd.read_csv(SITES, dtype={"zone": str})
    fc = sites[(sites.k == 3) & (sites.state == "SP")].iloc[0]
    depot = (fc.lat, fc.lng)
    days = pd.read_csv(OUT / "scenario_days.csv").set_index("day").date

    results, all_routes = [], []
    for day in ["normal", "black_friday"]:
        orders = pd.read_csv(OUT / f"orders_{day}.csv")
        van_routes = None
        for fleet, types in FLEETS.items():
            # The mixed fleet starts from the van-only plan, so it can only match or beat it
            start = van_routes if fleet == "mixed" else None
            kpi, routes = run(orders, depot, types, time_limit_s=20 if day == "normal" else 60, initial_routes=start)
            if fleet == "van_only":
                van_routes = [g.order_id[g.order_id != "FC"].tolist() for _, g in routes.groupby("route")]
            if kpi["fleet_bound_reached"]:
                print(f"  WARNING: vehicle bound reached in {day}/{fleet}; raise the bound in solve()")
            sid = f"{day}__{fleet}"
            results.append({"scenario": sid, "day": day, "date": days[day], "fleet": fleet, **kpi})
            all_routes.append(routes.assign(scenario=sid))
            print(f"{sid:<30} vans={kpi['vans']:>2} motos={kpi['motorbikes']:>2} km={kpi['total_km']:6.0f} "
                  f"cost=R${kpi['total_cost']:7.0f} R$/order={kpi['cost_per_order']:5.2f} "
                  f"undelivered={kpi['orders_not_delivered']:>3} saving={kpi['cost_saving_vs_baseline_pct']:4.1f}%")

    # Black Friday with only the vehicles a normal day needs (mixed fleet)
    normal_mixed = next(r for r in results if r["scenario"] == "normal__mixed")
    cap = {"van": normal_mixed["vans"], "motorbike": normal_mixed["motorbikes"]}
    orders = pd.read_csv(OUT / "orders_black_friday.csv")
    kpi, routes = run(orders, depot, ["van", "motorbike"], max_per_type=cap, time_limit_s=60)
    sid = "black_friday__normal_fleet"
    results.append({"scenario": sid, "day": "black_friday", "date": days["black_friday"],
                    "fleet": f"normal_fleet ({cap['van']} van + {cap['motorbike']} moto)", **kpi})
    all_routes.append(routes.assign(scenario=sid))
    print(f"{sid:<30} vans={kpi['vans']:>2} motos={kpi['motorbikes']:>2} km={kpi['total_km']:6.0f} "
          f"undelivered={kpi['orders_not_delivered']:>3}")

    pd.DataFrame(results).round(2).to_csv(OUT / "vrp_scenarios.csv", index=False)
    pd.concat(all_routes).to_csv(OUT / "vrp_routes.csv", index=False)
    pd.DataFrame([{"vehicle_type": t, **v} for t, v in VEHICLES.items()] +
                 [{"vehicle_type": "shift", "service_min": SHIFT_MIN}]).to_csv(OUT / "vrp_assumptions.csv", index=False)
    pd.DataFrame([{"name": "Depot (FC Sao Paulo)", "lat": depot[0], "lng": depot[1]}]).to_csv(OUT / "depot.csv", index=False)


if __name__ == "__main__":
    main()
