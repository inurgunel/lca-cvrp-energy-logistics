"""
Life-cycle assessment of the two supply pathways.

Follows the ISO 14040 / 14044 structure: goal and scope are fixed by the
functional unit below, the inventory is assembled from the pathway parameters
in config.py plus the transport flow produced by the routing model, and
characterization uses ReCiPe 2016 midpoint (H) for global warming potential
over a 100-year horizon.

The coupling with routing happens in one place: transport tonne-kilometres
enter the inventory as a flow, so a change in routing changes the impact
result directly rather than being reported as a separate figure.

Functional unit: one delivered unit of energy service to a dealer.
TODO(nunu): state the thesis functional unit explicitly here.

Usage:
    python src/lca_model.py
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

import config


@dataclass
class PathwayResult:
    """Characterized result for one supply pathway, in kg CO2-eq per year."""

    name: str
    upstream: float
    use_phase: float
    transport: float
    amortized_manufacturing: float

    @property
    def total(self) -> float:
        return (
            self.upstream
            + self.use_phase
            + self.transport
            + self.amortized_manufacturing
        )


def average_payload_tonnes() -> float:
    """
    Mean payload carried per kilometre driven.

    Multiplying total network distance by total network tonnage would be wrong
    by roughly the number of vehicle trips: no single vehicle carries the whole
    network's freight over the whole network's distance. Tonne-kilometres are
    therefore built from an average payload, which is the standard freight LCA
    convention.
    """
    return (
        config.VEHICLE_CAPACITY
        * config.AVERAGE_PAYLOAD_UTILIZATION
        * config.TONNES_PER_DEMAND_UNIT
    )


def transport_impact(distance_km: float) -> float:
    """
    Characterize the transport flow, annualized.

    The routing model solves one representative delivery period, so the result
    is scaled by the number of periods per year before it is compared against
    annual throughput.
    """
    tkm_per_period = distance_km * average_payload_tonnes()
    annual_tkm = tkm_per_period * config.DELIVERY_PERIODS_PER_YEAR
    return annual_tkm * config.GWP_TRANSPORT_PER_TKM


def lpg_pathway(distance_km: float, annual_fu: int) -> PathwayResult:
    return PathwayResult(
        name="LPG",
        upstream=config.GWP_LPG_UPSTREAM * annual_fu,
        use_phase=config.GWP_LPG_USE_PHASE * annual_fu,
        transport=transport_impact(distance_km),
        amortized_manufacturing=0.0,
    )


def pv_pathway(distance_km: float, annual_fu: int) -> PathwayResult:
    """
    The PV pathway carries its manufacturing burden explicitly.

    Amortizing the embodied emissions over the system lifetime is what makes
    the annual comparison fair; the payback period below reports the same
    burden the other way round, as time rather than as an annual charge.
    """
    return PathwayResult(
        name="Photovoltaic",
        upstream=0.0,
        use_phase=config.GWP_PV_OPERATION_PER_FU * annual_fu,
        transport=transport_impact(distance_km),
        amortized_manufacturing=(
            config.GWP_PV_MANUFACTURING / config.PV_SYSTEM_LIFETIME_YEARS
        ),
    )


def carbon_payback_years(lpg: PathwayResult, pv: PathwayResult) -> float | None:
    """
    Years until avoided operating emissions offset the PV manufacturing burden.

    Compares operating impact only, since the manufacturing burden is what is
    being paid back and must not appear on both sides of the ratio.
    """
    lpg_operating = lpg.upstream + lpg.use_phase + lpg.transport
    pv_operating = pv.upstream + pv.use_phase + pv.transport

    annual_avoided = lpg_operating - pv_operating
    if annual_avoided <= 0:
        return None

    return config.GWP_PV_MANUFACTURING / annual_avoided


def _report(result: PathwayResult) -> None:
    print(f"\n{result.name} pathway (kg CO2-eq / year)")
    print(f"  {'Upstream':<28}{result.upstream:>16,.0f}")
    print(f"  {'Use phase':<28}{result.use_phase:>16,.0f}")
    print(f"  {'Transport':<28}{result.transport:>16,.0f}")
    print(f"  {'Manufacturing (amortized)':<28}{result.amortized_manufacturing:>16,.0f}")
    print(f"  {'TOTAL':<28}{result.total:>16,.0f}")


def main() -> None:
    if not config.ROUTES_CSV.exists():
        raise SystemExit(
            f"{config.ROUTES_CSV} not found. Run src/cvrp_solver.py first."
        )

    routes = pd.read_csv(config.ROUTES_CSV)

    baseline_km = routes["baseline_km"].sum()
    optimized_km = routes["optimized_km"].sum()
    annual_fu = config.ANNUAL_FUNCTIONAL_UNITS

    print("=" * 62)
    print("PATHWAY COMPARISON (optimized routing in both cases)")
    print("=" * 62)

    lpg = lpg_pathway(optimized_km, annual_fu)
    pv = pv_pathway(optimized_km, annual_fu)

    _report(lpg)
    _report(pv)

    reduction_pct = 100.0 * (lpg.total - pv.total) / lpg.total
    payback = carbon_payback_years(lpg, pv)

    print("\n" + "=" * 62)
    print(f"{'GWP reduction, PV vs LPG':<40}{reduction_pct:>18.2f} %")
    if payback is not None:
        print(f"{'Carbon payback period':<40}{payback:>16.2f} yr")
    else:
        print(f"{'Carbon payback period':<40}{'never (no net saving)':>22}")

    print("\n" + "=" * 62)
    print("ROUTING CONTRIBUTION")
    print("=" * 62)

    transport_baseline = transport_impact(baseline_km)
    transport_optimized = transport_impact(optimized_km)
    routing_saving = transport_baseline - transport_optimized

    lpg_unoptimized = lpg_pathway(baseline_km, annual_fu)
    share = 100.0 * routing_saving / lpg_unoptimized.total

    print(f"{'Transport impact, baseline routing':<40}{transport_baseline:>16,.0f} kg")
    print(f"{'Transport impact, optimized routing':<40}{transport_optimized:>16,.0f} kg")
    print(f"{'Avoided through routing':<40}{routing_saving:>16,.0f} kg")
    print(f"{'Share of total LPG footprint':<40}{share:>18.2f} %")

    print("\n" + "-" * 62)
    print("Reminder: this run uses SYNTHETIC data and placeholder")
    print("characterization factors. It reproduces the method, not the")
    print("figures reported at YAEM 2026.")
    print("-" * 62)


if __name__ == "__main__":
    main()
