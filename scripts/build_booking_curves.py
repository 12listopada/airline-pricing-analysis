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

for flight in future.itertuples(index=False):
    peers = past.loc[past["route"] == flight.route]
    historical_bookings = bookings.loc[bookings["flight_id"].isin(peers["flight_id"])]
    historical_capacity = peers["capacity"].sum()
    current_lead = int((flight.departure_date - AS_OF).days)
    for days_before in sorted(set(CHECKPOINTS + [current_lead]), reverse=True):
        checkpoint_date = flight.departure_date - pd.Timedelta(days=days_before)
        if checkpoint_date > AS_OF:
            continue
        historical_passengers = historical_bookings.loc[
            historical_bookings["days_before_departure"] >= days_before, "passengers"].sum()
        benchmark = 100 * historical_passengers / historical_capacity
        passengers = bookings.loc[
            (bookings["flight_id"] == flight.flight_id) &
            (bookings["days_before_departure"] >= days_before), "passengers"].sum()
        lf = 100 * passengers / flight.capacity
        rows.append({"flight_id": flight.flight_id, "route": flight.route,
            "departure_date": flight.departure_date, "days_before_departure": days_before,
            "checkpoint_date": checkpoint_date, "booked_passengers": int(passengers),
            "load_factor_pct": lf, "historical_load_factor_pct": benchmark,
            "gap_pp": lf - benchmark, "historical_peer_count": len(peers), "is_synthetic": True})

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