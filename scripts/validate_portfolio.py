from pathlib import Path
import json
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
data = root / 'data'
c = pd.read_csv(data / 'current_vs_history.csv')
b = pd.read_csv(data / 'booking_curves.csv', parse_dates=['checkpoint_date'])
s = pd.read_csv(data / 'pricing_scenarios.csv')
assert c.flight_id.is_unique
assert not b.duplicated(['flight_id', 'days_before_departure']).any()
assert not s.duplicated(['flight_id', 'price_change_pct', 'demand_change_pct']).any()
assert np.allclose(c.capacity - c.passengers_now, c.seats_remaining)
assert np.allclose(c.passengers_now / c.capacity * 100, c.load_factor_now_pct)
assert np.allclose(c.passengers_now * c.average_fare_now_eur, c.revenue_now_eur)
assert b.checkpoint_date.le(pd.Timestamp('2026-10-07')).all()
snap = b.loc[b.checkpoint_date.eq(pd.Timestamp('2026-10-07'))].merge(c, on='flight_id', validate='one_to_one')
assert len(snap) == len(c) == 54
assert np.allclose(snap.booked_passengers, snap.passengers_now)
assert np.allclose(snap.gap_pp, snap.gap_same_lead_pp)
assert b.sort_values(['flight_id','days_before_departure'], ascending=[True,False]).groupby('flight_id').booked_passengers.diff().dropna().ge(0).all()
expected = np.minimum(s.seats_remaining, s.baseline_unconstrained_demand * (1+s.demand_change_pct/100))
assert np.allclose(expected,s.expected_additional_passengers)
assert np.allclose(s.expected_additional_passengers*s.assumed_future_fare_eur,s.future_sales_revenue_eur)
assert np.allclose(s.future_sales_revenue_eur-s.baseline_future_revenue_eur,s.revenue_change_eur)
baseline=s.loc[s.price_change_pct.eq(0)&s.demand_change_pct.eq(0)]
assert len(baseline)==54 and np.allclose(baseline.revenue_change_eur,0)
for p in (root/'dashboard_complete/AirlinePricing_Complete/AirlinePricing.Report').rglob('*.json'):
    json.loads(p.read_text(encoding='utf-8-sig'))
for p in (root/'dashboard_complete/AirlinePricing_Complete/AirlinePricing.SemanticModel/definition/tables').glob('*.tmdl'):
    text=p.read_text(encoding='utf-8-sig')
    if 'File.Contents' in text:
        assert 'File.Contents(DataFolder &' in text
print(f'PASS: {len(c)} flights; {len(b)} curve rows; {len(s)} scenarios; 54 matching snapshot points.')
print('Data arithmetic and JSON parsing passed. Power BI rendering and DAX execution remain to be checked in Desktop.')
