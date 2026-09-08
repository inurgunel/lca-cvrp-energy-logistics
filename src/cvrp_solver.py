"""
Capacitated vehicle routing for the dealer network.

Each facility serves its assigned dealers with a homogeneous fleet. The problem
is solved per facility rather than as one monolithic instance, which is both
how such networks operate and what keeps the instance sizes tractable.

Two distance totals are produced:

  baseline   an unoptimized sequential policy, standing in for the dispatch
             practice the study compared against
  optimized  the OR-Tools solution

The difference between them is what the LCA module converts into avoided
kilograms of CO2-equivalent.

Usage:
    python src/cvrp_solver.py
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

import config

EARTH_RADIUS_KM = 6371.0088


def haversine_matrix(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Great-circle distance matrix in kilometres, scaled to road distance."""
    lat = np.radians(lats)[:, None]
    lon = np.radians(lons)[:, None]

    dlat = lat - lat.T
    dlon = lon - lon.T

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat) * np.cos(lat.T) * np.sin(dlon / 2.0) ** 2
    km = 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))

    return km * config.ROAD_CIRCUITY_FACTOR


def baseline_distance(matrix: np.ndarray, demands: np.ndarray) -> float:
    """
    Reference policy: capacitated nearest neighbour.

    The vehicle always drives to the closest unserved dealer it still has
    capacity for, and returns to the depot when it does not. This is the rule
    experienced dispatchers apply implicitly, so it is the honest comparison
    point. A weaker baseline, such as serving dealers in list order, would
    inflate the reported saving to an implausible level and the comparison
    would not survive review.
    """
    n = len(demands)
    unserved = set(range(1, n))

    total = 0.0
    current = 0
    load = 0

    while unserved:
        feasible = [
            j for j in unserved if load + demands[j] <= config.VEHICLE_CAPACITY
        ]

        if not feasible:
            total += matrix[current][0]
            current = 0
            load = 0
            continue

        nxt = min(feasible, key=lambda j: matrix[current][j])
        total += matrix[current][nxt]
        load += demands[nxt]
        current = nxt
        unserved.remove(nxt)

    total += matrix[current][0]
    return float(total)


def solve_one_facility(
    matrix: np.ndarray,
    demands: np.ndarray,
    n_vehicles: int,
    time_limit_s: int = 10,
) -> float | None:
    """Solve a single-depot CVRP. Node 0 is the depot. Returns total km."""
    # OR-Tools works in integers, so distances are carried in metres.
    int_matrix = (matrix * 1000.0).astype(np.int64)

    manager = pywrapcp.RoutingIndexManager(len(demands), n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return int(int_matrix[i][j])

    transit_idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    def demand_callback(from_index: int) -> int:
        return int(demands[manager.IndexToNode(from_index)])

    demand_idx = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx,
        0,
        [config.VEHICLE_CAPACITY] * n_vehicles,
        True,
        "Capacity",
    )

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.FromSeconds(time_limit_s)

    solution = routing.SolveWithParameters(params)
    if solution is None:
        return None

    total_m = 0
    for vehicle in range(n_vehicles):
        index = routing.Start(vehicle)
        while not routing.IsEnd(index):
            nxt = solution.Value(routing.NextVar(index))
            total_m += routing.GetArcCostForVehicle(index, nxt, vehicle)
            index = nxt

    return total_m / 1000.0


def run() -> pd.DataFrame:
    dealers = pd.read_csv(config.DEALERS_CSV)
    facilities = pd.read_csv(config.FACILITIES_CSV)

    rows = []

    for _, facility in facilities.iterrows():
        served = dealers[dealers["assigned_facility"] == facility["facility_id"]]
        if served.empty:
            continue

        lats = np.concatenate([[facility["latitude"]], served["latitude"].to_numpy()])
        lons = np.concatenate([[facility["longitude"]], served["longitude"].to_numpy()])
        demands = np.concatenate([[0], served["demand"].to_numpy()])

        matrix = haversine_matrix(lats, lons)

        # Enough vehicles that a feasible solution always exists.
        required = math.ceil(demands.sum() / config.VEHICLE_CAPACITY)
        n_vehicles = max(config.VEHICLES_PER_FACILITY, required + 1)

        base_km = baseline_distance(matrix, demands)
        opt_km = solve_one_facility(matrix, demands, n_vehicles)

        if opt_km is None:
            print(f"  {facility['facility_id']}: no solution found, skipped")
            continue

        rows.append(
            {
                "facility_id": facility["facility_id"],
                "dealers": len(served),
                "demand": int(demands.sum()),
                "vehicles": n_vehicles,
                "baseline_km": round(base_km, 1),
                "optimized_km": round(opt_km, 1),
                "saved_km": round(base_km - opt_km, 1),
                "saved_pct": round(100.0 * (base_km - opt_km) / base_km, 2),
            }
        )
        print(
            f"  {facility['facility_id']}: {len(served):>3} dealers | "
            f"baseline {base_km:>9,.0f} km | optimized {opt_km:>9,.0f} km | "
            f"saved {100 * (base_km - opt_km) / base_km:>5.1f}%"
        )

    results = pd.DataFrame(rows)
    results.to_csv(config.ROUTES_CSV, index=False)
    return results


def main() -> None:
    print("Solving capacitated vehicle routing per facility...\n")
    results = run()

    base = results["baseline_km"].sum()
    opt = results["optimized_km"].sum()

    print("\n" + "=" * 62)
    print(f"{'Baseline distance':<28}{base:>16,.0f} km")
    print(f"{'Optimized distance':<28}{opt:>16,.0f} km")
    print(f"{'Distance avoided':<28}{base - opt:>16,.0f} km")
    print(f"{'Reduction':<28}{100 * (base - opt) / base:>15.2f} %")
    print("=" * 62)
    print(f"\nPer-facility detail written to {config.ROUTES_CSV}")


if __name__ == "__main__":
    main()
