from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

rng = np.random.default_rng(42)
AS_OF = pd.Timestamp("2026-10-07")

# Illustrative assumptions, not actual airline fares or capacity.
# Route: seats, base one-way fare in EUR, typical final load factor.
ROUTES = {
    "KEF-LHR": (180, 180, 0.86),
    "KEF-CPH": (180, 140, 0.78),
    "KEF-JFK": (240, 350, 0.89),
}

flights = []
bookings = []
booking_number = 0

departure_dates = pd.date_range(
    "2026-07-01", "2026-11-30", freq="3D"
)

for route, (capacity, base_fare, typical_load) in ROUTES.items():
    for departure in departure_dates:
        flight_id = f"{route}-{departure:%Y%m%d}"

        flights.append({
            "flight_id": flight_id,
            "route": route,
            "departure_date": departure,
            "capacity": capacity,
            "base_fare_eur": base_fare,
            "is_synthetic": True,
        })

        # Random variation in demand; sales never exceed capacity.
        final_load = np.clip(
            typical_load + rng.normal(0, 0.07), 0.45, 0.99
        )
        passenger_count = int(round(capacity * final_load))

        # Each row represents one passenger's booking.
        # This simplified model excludes cancellations and group bookings.
        lead_days = np.clip(
            rng.gamma(shape=2.0, scale=22.0, size=passenger_count),
            1,
            120,
        ).astype(int)

        for days_before in lead_days:
            booking_date = departure - pd.Timedelta(
                days=int(days_before)
            )

            if booking_date > AS_OF:
                continue

            # Assumed fare pattern: later bookings tend to cost more.
            # This does not estimate the effect of price on demand.
            late_booking_factor = 1 + 0.45 * (
                1 - days_before / 120
            )
            fare = max(
                40,
                base_fare
                * late_booking_factor
                * rng.lognormal(mean=0, sigma=0.12),
            )

            booking_number += 1
            bookings.append({
                "booking_id": f"B{booking_number:07d}",
                "flight_id": flight_id,
                "booking_date": booking_date,
                "days_before_departure": int(days_before),
                "passengers": 1,
                "fare_eur": round(float(fare), 2),
                "is_synthetic": True,
            })

flights_df = pd.DataFrame(flights)
bookings_df = pd.DataFrame(bookings)

# Basic integrity checks.
assert flights_df["flight_id"].is_unique
assert bookings_df["booking_id"].is_unique
assert bookings_df["booking_date"].max() <= AS_OF
assert bookings_df["flight_id"].isin(flights_df["flight_id"]).all()

sold = bookings_df.groupby("flight_id")["passengers"].sum()
capacity = flights_df.set_index("flight_id")["capacity"]
assert sold.le(capacity.loc[sold.index]).all()

flights_df.to_csv(
    DATA / "flights.csv", index=False, date_format="%Y-%m-%d"
)
bookings_df.to_csv(
    DATA / "bookings.csv", index=False, date_format="%Y-%m-%d"
)

print("Synthetic data generated successfully.")
print(f"Analysis date: {AS_OF.date()}")
print(f"Flights: {len(flights_df):,}")
print(f"Passenger bookings: {len(bookings_df):,}")
print(f"Files saved in: {DATA}")