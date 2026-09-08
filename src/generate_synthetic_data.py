"""
Generate the synthetic distribution network.

Produces 885 dealers and 13 facilities with clustered spatial structure and a
right-skewed demand distribution, matching the shape of the network studied in
the paper without reproducing any of its real values.

Nothing in this file is derived from any real dataset. Coordinates are drawn
from a random process seeded in config.py, and dealer identifiers are
sequential integers.

Usage:
    python src/generate_synthetic_data.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


def _make_facilities(rng: np.random.Generator) -> pd.DataFrame:
    """Place facilities uniformly across the bounding box."""
    lat = rng.uniform(*config.LAT_RANGE, size=config.N_FACILITIES)
    lon = rng.uniform(*config.LON_RANGE, size=config.N_FACILITIES)

    return pd.DataFrame(
        {
            "facility_id": [f"F{i:02d}" for i in range(config.N_FACILITIES)],
            "latitude": np.round(lat, 5),
            "longitude": np.round(lon, 5),
        }
    )


def _make_dealers(rng: np.random.Generator, facilities: pd.DataFrame) -> pd.DataFrame:
    """
    Scatter dealers around facilities.

    Real dealer networks cluster near supply points rather than spreading
    uniformly, so each dealer is assigned to a facility and then offset by a
    normal perturbation. This keeps the routing problem structurally realistic.
    """
    assignments = rng.integers(0, config.N_FACILITIES, size=config.N_DEALERS)

    base_lat = facilities["latitude"].to_numpy()[assignments]
    base_lon = facilities["longitude"].to_numpy()[assignments]

    lat = base_lat + rng.normal(0.0, 0.45, size=config.N_DEALERS)
    lon = base_lon + rng.normal(0.0, 0.65, size=config.N_DEALERS)

    lat = np.clip(lat, *config.LAT_RANGE)
    lon = np.clip(lon, *config.LON_RANGE)

    demand = rng.normal(config.DEMAND_MEAN, config.DEMAND_STD, size=config.N_DEALERS)
    demand = np.maximum(demand, config.DEMAND_MIN).round().astype(int)

    return pd.DataFrame(
        {
            "dealer_id": [f"D{i:04d}" for i in range(config.N_DEALERS)],
            "assigned_facility": facilities["facility_id"].to_numpy()[assignments],
            "latitude": np.round(lat, 5),
            "longitude": np.round(lon, 5),
            "demand": demand,
        }
    )


def main() -> None:
    rng = np.random.default_rng(config.RANDOM_SEED)

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    facilities = _make_facilities(rng)
    dealers = _make_dealers(rng, facilities)

    facilities.to_csv(config.FACILITIES_CSV, index=False)
    dealers.to_csv(config.DEALERS_CSV, index=False)

    print(f"Wrote {len(facilities)} facilities -> {config.FACILITIES_CSV}")
    print(f"Wrote {len(dealers)} dealers    -> {config.DEALERS_CSV}")
    print(f"Total demand: {dealers['demand'].sum():,} units")
    print(
        "Dealers per facility: "
        f"min {dealers['assigned_facility'].value_counts().min()}, "
        f"max {dealers['assigned_facility'].value_counts().max()}"
    )


if __name__ == "__main__":
    main()
