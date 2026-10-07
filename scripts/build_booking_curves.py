from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
AS_OF = pd.Timestamp("2026-10-07")
CHECKPOINTS = [60, 45, 30, 21, 14, 10, 7, 4, 1, 0]

flights = pd.read_csv(
    DATA / "flights.csv", parse_dates=["departure_date"]
)
bookings = pd.read_csv(
    DATA / "bookings.csv", parse_dates=["booking_date"]
)
bookings = bookings.loc[bookings["booking_date"] <= AS_OF]

past = flights.loc[flights["departure_date"] < AS_OF]
future = flights.loc[flights["departure_date"] > AS_OF]
rows = []

for route, future_group in future.groupby("route"):
    peers = past.loc[past["route"] == route]
    historical_bookings = bookings.loc[
        bookings["flight_id"].isin(peers["flight_id"])
    ]
    historical_capacity = peers["capacity"].sum()

    for days_before in CHECKPOINTS:
        historical_passengers = historical_bookings.loc[
            historical_bookings["days_before_departure"] >= days_before,
            "passengers",
        ].sum()

        benchmark = (
            100 * historical_passengers / historical_capacity
            if historical_capacity > 0 else float("nan")
        )

        for flight in future_group.itertuples(index=False):
            checkpoint_date = (
                flight.departure_date
                - pd.Timedelta(days=days_before)
            )

            # Exclude checkpoints that have not happened yet.
            if checkpoint_date > AS_OF:
                continue

            passengers = bookings.loc[
                (bookings["flight_id"] == flight.flight_id)
                & (bookings["days_before_departure"] >= days_before),
                "passengers",
            ].sum()

            load_factor = 100 * passengers / flight.capacity
            rows.append({
                "flight_id": flight.flight_id,
                "route": route,
                "departure_date": flight.departure_date,
                "days_before_departure": days_before,
                "checkpoint_date": checkpoint_date,
                "booked_passengers": int(passengers),
                "load_factor_pct": load_factor,
                "historical_load_factor_pct": benchmark,
                "gap_pp": load_factor - benchmark,
                "historical_peer_count": len(peers),
                "is_synthetic": True,
            })

curves = pd.DataFrame(rows).sort_values(
    ["flight_id", "days_before_departure"],
    ascending=[True, False],
)

assert not curves.duplicated(
    ["flight_id", "days_before_departure"]
).any()
assert curves["checkpoint_date"].le(AS_OF).all()
assert curves["load_factor_pct"].between(0, 100).all()

# Cumulative bookings must not decrease as departure approaches.
changes = curves.groupby("flight_id")["booked_passengers"].diff()
assert changes.dropna().ge(0).all()

curves.to_csv(
    DATA / "booking_curves.csv",
    index=False,
    date_format="%Y-%m-%d",
)

print(f"Booking curve rows: {len(curves)}")
print(f"Future flights represented: {curves['flight_id'].nunique()}")
print("\nExample: KEF-CPH-20261008")
print(
    curves.loc[
        curves["flight_id"] == "KEF-CPH-20261008",
        [
            "days_before_departure",
            "booked_passengers",
            "load_factor_pct",
            "historical_load_factor_pct",
            "gap_pp",
        ],
    ].round(2).to_string(index=False)
)