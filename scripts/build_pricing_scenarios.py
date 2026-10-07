from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
AS_OF = pd.Timestamp("2026-10-07")

flights = pd.read_csv(
    DATA / "flights.csv", parse_dates=["departure_date"]
)
bookings = pd.read_csv(
    DATA / "bookings.csv", parse_dates=["booking_date"]
)
current = pd.read_csv(DATA / "current_vs_history.csv")
bookings = bookings.loc[bookings["booking_date"] <= AS_OF]

past = flights.loc[flights["departure_date"] < AS_OF]
rows = []

for flight in current.itertuples(index=False):
    peers = past.loc[past["route"] == flight.route]
    historical = bookings.loc[
        bookings["flight_id"].isin(peers["flight_id"])
    ]

    # Historical bookings made AFTER the matching lead-time checkpoint.
    late_passengers = historical.loc[
        historical["days_before_departure"] < flight.days_to_departure,
        "passengers",
    ].sum()

    historical_capacity = peers["capacity"].sum()
    if historical_capacity == 0:
        continue

    baseline_demand = (
        late_passengers / historical_capacity * flight.capacity
    )

    # Illustrative future offer, not an observed market price.
    baseline_fare = flight.base_fare_eur * 1.45
    baseline_sales = min(baseline_demand, flight.seats_remaining)
    baseline_revenue = baseline_sales * baseline_fare

    # Independent assumptions; not an estimated price-demand relationship.
    for price_change in [-0.10, 0.0, 0.10]:
        for demand_change in [-0.20, 0.0, 0.20]:
            fare = baseline_fare * (1 + price_change)
            demand = baseline_demand * (1 + demand_change)
            sales = min(demand, flight.seats_remaining)
            incremental_revenue = sales * fare

            rows.append({
                "flight_id": flight.flight_id,
                "route": flight.route,
                "days_to_departure": flight.days_to_departure,
                "seats_remaining": flight.seats_remaining,
                "price_change_pct": price_change * 100,
                "demand_change_pct": demand_change * 100,
                "assumed_future_fare_eur": fare,
                "baseline_unconstrained_demand": baseline_demand,
                "expected_additional_passengers": sales,
                "capacity_constrained": demand > flight.seats_remaining,
                "future_sales_revenue_eur": incremental_revenue,
                "baseline_future_revenue_eur": baseline_revenue,
                "revenue_change_eur": (
                    incremental_revenue - baseline_revenue
                ),
                "scenario_total_booked_revenue_eur": (
                    flight.revenue_now_eur + incremental_revenue
                ),
                "is_synthetic": True,
            })

scenarios = pd.DataFrame(rows)

assert scenarios["expected_additional_passengers"].ge(0).all()
assert scenarios["expected_additional_passengers"].le(
    scenarios["seats_remaining"]
).all()

baseline = scenarios.loc[
    (scenarios["price_change_pct"] == 0)
    & (scenarios["demand_change_pct"] == 0)
]
assert np.allclose(baseline["revenue_change_eur"], 0)

scenarios.to_csv(DATA / "pricing_scenarios.csv", index=False)

print(f"Scenario rows: {len(scenarios)}")
print("\nExample: KEF-JFK-20261011")
print(
    scenarios.loc[
        scenarios["flight_id"] == "KEF-JFK-20261011",
        [
            "price_change_pct",
            "demand_change_pct",
            "expected_additional_passengers",
            "future_sales_revenue_eur",
            "revenue_change_eur",
        ],
    ].round(2).to_string(index=False)
)
