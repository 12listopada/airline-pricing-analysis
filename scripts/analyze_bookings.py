from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
AS_OF = pd.Timestamp("2026-10-07")


def export(frame, filename):
    frame.to_csv(
        DATA / filename,
        index=False,
        date_format="%Y-%m-%d",
    )


def sales_snapshot(selected_flights, selected_bookings, suffix):
    """Keep every selected flight, including those without bookings."""
    totals = selected_bookings.groupby("flight_id").agg(
        passengers=("passengers", "sum"),
        revenue_eur=("fare_eur", "sum"),
    )
    result = selected_flights.merge(
        totals, on="flight_id", how="left", validate="one_to_one"
    )
    result[["passengers", "revenue_eur"]] = (
        result[["passengers", "revenue_eur"]].fillna(0)
    )
    result["passengers"] = result["passengers"].astype(int)
    result["load_factor_pct"] = (
        100 * result["passengers"] / result["capacity"]
    )
    result["average_fare_eur"] = (
        result["revenue_eur"]
        / result["passengers"].replace(0, float("nan"))
    )
    assert result["passengers"].between(0, result["capacity"]).all()

    return result.rename(columns={
        "passengers": f"passengers_{suffix}",
        "revenue_eur": f"revenue_{suffix}_eur",
        "load_factor_pct": f"load_factor_{suffix}_pct",
        "average_fare_eur": f"average_fare_{suffix}_eur",
    })


def route_summary(frame):
    """Calculate weighted route metrics from flight totals."""
    summary = frame.groupby("route", as_index=False).agg(
        flights=("flight_id", "count"),
        seats=("capacity", "sum"),
        passengers_d14=("passengers_d14", "sum"),
        revenue_d14_eur=("revenue_d14_eur", "sum"),
    )
    summary["load_factor_d14_pct"] = (
        100 * summary["passengers_d14"] / summary["seats"]
    )
    summary["average_fare_d14_eur"] = (
        summary["revenue_d14_eur"]
        / summary["passengers_d14"].replace(0, float("nan"))
    )
    return summary


def add_historical_benchmark(current, past_flights, bookings):
    """Match each future flight to its route and lead time."""
    rows = []
    for flight in current.itertuples(index=False):
        peers = past_flights.loc[past_flights["route"] == flight.route]
        peer_sales = bookings.loc[
            bookings["flight_id"].isin(peers["flight_id"])
            & (bookings["days_before_departure"] >= flight.days_to_departure)
        ]
        seats = peers["capacity"].sum()
        rows.append({
            "flight_id": flight.flight_id,
            "historical_peer_count": len(peers),
            "benchmark_same_lead_pct": (
                100 * peer_sales["passengers"].sum() / seats
                if seats > 0 else float("nan")
            ),
        })

    benchmark = pd.DataFrame(rows, columns=[
        "flight_id", "historical_peer_count", "benchmark_same_lead_pct"
    ])
    result = current.merge(
        benchmark, on="flight_id", how="left", validate="one_to_one"
    )
    result["gap_same_lead_pp"] = (
        result["load_factor_now_pct"] - result["benchmark_same_lead_pct"]
    )
    return result


def main():
    flights = pd.read_csv(DATA / "flights.csv", parse_dates=["departure_date"])
    bookings = pd.read_csv(DATA / "bookings.csv", parse_dates=["booking_date"])
    bookings = bookings.loc[bookings["booking_date"] <= AS_OF].copy()

    assert flights["flight_id"].is_unique
    assert bookings["booking_id"].is_unique
    assert bookings["flight_id"].isin(flights["flight_id"]).all()

    # 1. Observable D-14 snapshots and route summary.
    eligible = flights.loc[
        flights["departure_date"] - pd.Timedelta(days=14) <= AS_OF
    ]
    d14 = sales_snapshot(
        eligible, bookings.loc[bookings["days_before_departure"] >= 14], "d14"
    )
    summary = route_summary(d14)
    export(d14, "flight_performance_d14.csv")
    export(summary, "route_summary_d14.csv")

    # 2. Historical D-14 benchmark, excluding future departures.
    history = route_summary(d14.loc[d14["departure_date"] < AS_OF])
    history = history[["route", "flights", "load_factor_d14_pct"]].rename(
        columns={
            "flights": "historical_flights",
            "load_factor_d14_pct": "benchmark_load_factor_d14_pct",
        }
    )
    comparison = d14.loc[d14["departure_date"] > AS_OF].merge(
        history, on="route", how="left", validate="many_to_one"
    )
    comparison["gap_vs_history_pp"] = (
        comparison["load_factor_d14_pct"]
        - comparison["benchmark_load_factor_d14_pct"]
    )
    export(
        comparison.sort_values("gap_vs_history_pp"),
        "upcoming_flights_d14_comparison.csv",
    )

    # 3. Current position and seven-day booking pickup.
    current = sales_snapshot(
        flights.loc[flights["departure_date"] > AS_OF], bookings, "now"
    )
    recent = bookings.loc[
        bookings["booking_date"] > AS_OF - pd.Timedelta(days=7)
    ].groupby("flight_id")["passengers"].sum()

    current["bookings_last_7_days"] = (
        current["flight_id"].map(recent).fillna(0).astype(int)
    )
    current["days_to_departure"] = (
        current["departure_date"] - AS_OF
    ).dt.days
    current["seats_remaining"] = current["capacity"] - current["passengers_now"]
    current = current.sort_values(["departure_date", "route"])
    export(current, "current_flight_position.csv")

    # 4. Current versus historical sales at the same lead time.
    matched = add_historical_benchmark(
        current, flights.loc[flights["departure_date"] < AS_OF], bookings
    )
    export(matched, "current_vs_history.csv")

    print(f"Completed: {len(d14)} D-14 snapshots; {len(current)} future flights.")
    print("\nCurrent sales versus history — first 12 flights")
    print(matched[[
        "flight_id", "days_to_departure", "load_factor_now_pct",
        "benchmark_same_lead_pct", "gap_same_lead_pp", "historical_peer_count",
    ]].head(12).round(2).to_string(index=False))


if __name__ == "__main__":
    main()