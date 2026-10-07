# Airline Booking Performance & Pricing Scenarios

**Python · pandas · NumPy · Power BI · DAX**

A commercial analytics portfolio project that identifies upcoming flights selling below their historical booking pace and explores revenue trade-offs under alternative price and demand assumptions.

The project uses simulated airline booking and fare data. It demonstrates an analytical workflow rather than actual airline results or an operational pricing system.

## Business Questions

- Which flights are selling ahead of or behind historical booking pace?
- Is weak performance persistent throughout the booking window?
- How could changes in price and demand affect future ticket revenue?
- Which flights should receive further commercial review?

## Portfolio Snapshot

Analysis date: **end of 7 October 2026**. All monetary values are in **EUR**.

| Metric | Value |
|---|---:|
| Illustrative routes | KEF–LHR, KEF–CPH, KEF–JFK |
| Generated flights | 153 |
| Observed passenger bookings | 22,830 |
| Historical comparison flights | 33 per route |
| Upcoming flights | 54 |
| Available seats on upcoming flights | 4,786 |
| Booked ticket revenue on upcoming flights | €1,813,200.63 |
| Portfolio booked load factor | 55.7% |
| Booking curve observations | 195 |
| Pricing scenarios | 486 |

Portfolio booked load factor describes the current position across flights with different departure dates. It is not a forecast of final occupancy.

## Dashboard

### 1. Portfolio Overview

Displays upcoming-flight KPIs, route filters, capacity-weighted booking gaps and a flight review table.

Each flight is compared with historical flights on the same route at the same number of days before departure.

![alt text](<Zrzut ekranu 2026-10-07 190821.png>)

### 2. Booking Pace

Compares a selected flight's cumulative bookings with its historical benchmark.

Only checkpoints reached by the analysis date are included. The categorical axis orders checkpoints from D−60 toward departure; spacing between checkpoints does not represent equal elapsed time.

![alt text](<Zrzut ekranu 2026-10-07 190834.png>)

### 3. Pricing Scenarios

Shows future ticket revenue and change versus baseline in two scenario matrices.

Rows represent demand changes of −20%, 0% and +20%. Columns represent price changes of −10%, 0% and +10%.

Select one flight to view its scenarios. Alternative scenarios must not be added together.

![alt text](<Zrzut ekranu 2026-10-07 190847-1.png>)

### 4. Methodology

Explains the data, calculations, assumptions and limits of the analysis.


## Findings and Recommended Review

| Flight | Observed position | Recommended review |
|---|---|---|
| KEF–CPH, 8 October | 67.22% booked versus 80.72% historically at D−1; 59 seats remaining | Urgent review of comparable competitor offers, available fare products and recent booking pickup. |
| KEF–CPH, 20 October | 13.87 percentage points below history at D−13; 78 seats remaining | Investigate the offer and demand context while time remains for a commercial response. |
| KEF–JFK, 17 October | 10.51 percentage points below history at D−10; 69 seats remaining | Review recent bookings and fare availability before considering an intervention. |
| KEF–JFK, 11 October | 10.25 percentage points above history at D−4; six seats remaining | Review remaining inventory and fare availability. Strong sales do not automatically justify a price increase. |

For KEF–CPH on 8 October, the booking gap is already −6.85 percentage points at D−60 and reaches −13.50 points at D−1. Underperformance is persistent within the simulation, rather than a sudden last-minute slowdown.

These findings identify review priorities. They do not establish the cause of weak sales or prove that changing prices would improve revenue.

## Pricing Trade-Off Example

For KEF–JFK on 11 October, the baseline assumes approximately 3.12 additional passengers at a future fare of €507.50, producing €1,584.02 in additional ticket revenue.

| Price change | Demand change | Future ticket revenue | Change vs baseline |
|---|---|---:|---:|
| 0% | 0% | €1,584.02 | €0.00 |
| −10% | +20% | €1,710.74 | +€126.72 |
| +10% | −20% | €1,393.93 | −€190.08 |

A higher fare does not necessarily generate higher revenue if ticket sales fall.

Without capacity constraints, a 10% fare reduction requires more than 11.1% additional ticket sales to increase revenue. This is a break-even calculation, not an estimate of customer price sensitivity or profitability.

## Methodology

- A fixed random seed of `42` makes data generation reproducible.
- Each booking represents one passenger.
- Only bookings made on or before the analysis date are retained.
- Booked load factor equals booked passengers divided by seat capacity.
- Historical benchmarks use departed flights on the same route, reconstructed at the same lead time.
- Historical flights with zero bookings remain in the benchmark.
- Booking gaps are expressed in percentage points.
- Portfolio booking gaps are weighted by seat capacity.
- Seven-day booking pickup covers 1–7 October inclusive.
- Review thresholds below −5 and above +5 percentage points are illustrative, not validated pricing rules.

### Scenario Assumptions

- Remaining demand is approximated from historical bookings occurring after the matching lead-time checkpoint, scaled by capacity.
- The assumed future fare equals the route base fare multiplied by `1.45`.
- Price and demand changes are varied independently.
- Additional ticket sales cannot exceed remaining seat capacity.
- Existing booked revenue is unchanged.
- Fractional passenger counts represent expected values.

## Project Files

| File or folder | Purpose |
|---|---|
| `scripts/generate_data.py` | Generate simulated flights and bookings |
| `scripts/analyze_bookings.py` | Calculate booking performance and historical benchmarks |
| `scripts/build_booking_curves.py` | Build observable booking checkpoints |
| `scripts/build_pricing_scenarios.py` | Calculate capacity-constrained revenue scenarios |
| `data/` | Source and derived CSV files |
| Power BI project folder | Saved report and semantic model |
| `scripts/archive/` | Earlier working scripts; not required to run the analysis |

## Run the Analysis

From the main project folder in Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install pandas numpy
.\.venv\Scripts\python.exe scripts\generate_data.py
.\.venv\Scripts\python.exe scripts\analyze_bookings.py
.\.venv\Scripts\python.exe scripts\build_booking_curves.py
.\.venv\Scripts\python.exe scripts\build_pricing_scenarios.py
```

Open the saved `.pbip` project in Power BI Desktop and refresh the data.

The saved report currently expects its CSV inputs in:

```text
C:\airline-pricing-analysis\data
```

If the project is stored elsewhere, update the CSV source paths in Power Query before refreshing.

The analysis date is fixed in all four analytical scripts. Changing it requires updating the scripts consistently and regenerating the outputs.

Do not rerun the archived dashboard builders: they are not needed to refresh the final report and could replace manual formatting.

## Validation

The four analytical scripts were executed successfully.

Regenerated `current_vs_history.csv`, `booking_curves.csv` and `pricing_scenarios.csv` matched the submitted dashboard inputs within floating-point tolerance.

Checks include:

- Unique booking and flight identifiers.
- Valid booking-to-flight references.
- Passenger counts within seat capacity.
- No future booking-curve checkpoints.
- Non-decreasing cumulative bookings.
- Scenario sales within remaining capacity.
- Zero revenue change for the baseline scenario.

Selected dashboard values and filtering behavior were also checked in Power BI Desktop.

## Limitations

Demand levels and late-booking fare patterns are assumptions built into the generator, not independent market discoveries.

The model excludes cancellations, group bookings, overbooking, connecting passengers, fare restrictions and ancillary revenue. It does not control for seasonality, weekday effects or competitor pricing.

Booked revenue represents ticket sales, not recognized revenue or profit.

The project does not estimate causal price elasticity, identify an optimal fare or implement ATPCo fare management. Operational decisions would require additional market and commercial evidence.

## Author

Oliwia Tomiczek  
[GitHub](https://github.com/12listopada)