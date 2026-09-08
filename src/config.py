"""
Central configuration for the LCA + CVRP model.

Every number the model depends on lives here, so that swapping the synthetic
network for a real one is a matter of editing this file rather than hunting
through the code.

Lines marked TODO(nunu) are placeholders. Replace them with the values used in
the YAEM 2026 study before presenting any result as reproducing the paper.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FIGURES_DIR = ROOT / "figures"

DEALERS_CSV = DATA_DIR / "synthetic_dealers.csv"
FACILITIES_CSV = DATA_DIR / "synthetic_facilities.csv"
ROUTES_CSV = DATA_DIR / "solved_routes.csv"


# --------------------------------------------------------------------------
# Network structure
# --------------------------------------------------------------------------

N_DEALERS = 885
N_FACILITIES = 13

# Bounding box used only to place synthetic points. Deliberately a coarse
# rectangle over Turkey so that distances are realistic in magnitude while
# no point corresponds to a real dealer location.
LAT_RANGE = (36.5, 41.5)
LON_RANGE = (27.0, 43.0)

RANDOM_SEED = 42


# --------------------------------------------------------------------------
# Demand and fleet
# --------------------------------------------------------------------------

# TODO(nunu): replace with the demand unit and distribution used in the thesis.
DEMAND_MEAN = 40          # units per dealer per period
DEMAND_STD = 15
DEMAND_MIN = 5

# TODO(nunu): replace with the real fleet definition.
VEHICLE_CAPACITY = 900    # same unit as demand
VEHICLES_PER_FACILITY = 8

# Road distances exceed great-circle distances. This multiplier converts
# haversine distance into an approximate road distance.
# TODO(nunu): replace if the thesis used a real road distance matrix.
ROAD_CIRCUITY_FACTOR = 1.35

# Mean capacity utilization across a route. A vehicle leaves the depot full and
# arrives back empty, so the average payload carried per kilometre is well
# below the nominal capacity. Tonne-kilometres are computed from this average
# payload, not from network-wide tonnage.
# TODO(nunu): replace with the utilization observed in the thesis data.
AVERAGE_PAYLOAD_UTILIZATION = 0.55


# --------------------------------------------------------------------------
# Life-cycle inventory and characterization
# --------------------------------------------------------------------------
# Characterization follows ReCiPe 2016 midpoint (H), impact category:
# global warming potential, 100-year horizon, expressed in kg CO2-eq.
#
# TODO(nunu): every factor below must be replaced with the Ecoinvent 3.9
# derived values actually used in the study. The values here are order-of-
# magnitude placeholders that keep the pipeline runnable, nothing more.

# Transport, per tonne-kilometre of freight moved by road
GWP_TRANSPORT_PER_TKM = 0.152        # kg CO2-eq / tkm

# Average payload mass per demand unit, used to convert demand into tonnes
TONNES_PER_DEMAND_UNIT = 0.027       # t / unit

# LPG pathway, per functional unit delivered
GWP_LPG_USE_PHASE = 2.98             # kg CO2-eq / FU
GWP_LPG_UPSTREAM = 0.61              # kg CO2-eq / FU

# Photovoltaic pathway
GWP_PV_MANUFACTURING = 1_450_000.0   # kg CO2-eq, one-off embodied burden
GWP_PV_OPERATION_PER_FU = 0.42       # kg CO2-eq / FU
PV_SYSTEM_LIFETIME_YEARS = 25

# Annual functional units delivered across the whole network
# TODO(nunu): replace with the annual throughput used in the thesis.
ANNUAL_FUNCTIONAL_UNITS = 260_000

# The routing model solves one representative delivery period. The LCA reports
# annual impact, so the single-period distance has to be scaled up. Keeping
# this as an explicit constant rather than folding it into the transport factor
# makes the assumption visible instead of buried.
# TODO(nunu): replace with the real replenishment frequency.
DELIVERY_PERIODS_PER_YEAR = 52


# --------------------------------------------------------------------------
# Reported study results
# --------------------------------------------------------------------------
# Kept here for reference only. These are the values published in the YAEM 2026
# conference paper. The synthetic pipeline will NOT reproduce them, and the
# code never uses these constants in a calculation.

PAPER_GWP_REDUCTION_PCT = 85.0
PAPER_CARBON_PAYBACK_YEARS = 2.16
PAPER_ROUTING_SAVING_KG_CO2E = 51_640.0
PAPER_ROUTING_SAVING_PCT = 5.56
