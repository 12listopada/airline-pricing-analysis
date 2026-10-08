# Forward Bookings and Pricing Sensitivity

**A synthetic airline portfolio case study | Snapshot: 7 October 2026 | EUR**

I built a Power BI case study to identify flights requiring commercial review and assess revenue sensitivity under explicit price and demand assumptions. The portfolio covers 54 upcoming flights across three illustrative routes from Keflavík: Copenhagen, London Heathrow and New York JFK. All data is simulated; it does not represent Icelandair operations.

The analysis compares each flight's booked load factor with departed flights on the same route at the same lead time. Portfolio gaps are weighted by capacity. Booking curves include the actual snapshot checkpoint, while pricing scenarios separate existing ticket sales from potential future sales and cap additional passengers at available seats.

**Three findings guide the review.** Copenhagen is the first investigation priority: its route booking gap is −3.98 percentage points and eight of 18 flights are below the illustrative −5 pp threshold. The 20 October departure has 78 seats remaining at D−13 and a −13.87 pp gap. I would investigate recent pickup and comparable competitor products before proposing a targeted offer.

JFK's 11 October departure is 97.5% booked with six seats remaining. In the sensitivity model, a 10% price increase combined with a 20% demand reduction produces EUR 1,393.93 in future ticket sales, versus EUR 1,584.02 in the baseline. This illustrates why a higher fare alone does not establish a better revenue outcome.

London Heathrow is ahead of its benchmark by 2.58 pp at route level. I would monitor remaining demand and investigate fare-product performance rather than interpret strong bookings alone as evidence of optimal pricing.

**Decision discipline is central to the project.** Without a capacity cap, a 10% price reduction needs more than 11.11% additional sales to preserve revenue; a 10% price increase tolerates approximately 9.09% fewer sales. These are arithmetic break-even conditions, not estimated price elasticity. Operational decisions would also need comparable market offers, fare restrictions, segmentation and demand evidence.

The package includes raw synthetic bookings, a deterministic generator, analysis scripts, report definitions and a data-validation script. Limitations include independent price/demand assumptions, no departure-day bookings and no controls for seasonality, cancellations, connections or competitor behavior. Booked ticket sales are not recognized revenue, yield or profit.
