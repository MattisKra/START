"""Shared instructions for pricing work in its printed invoice unit."""

RATE_CHECK = """
For any material price decision, distinguish the printed unit, the necessary work and the
policy-payable amount. Compare a quoted price to the same trade, role, locality, date and unit.
For labour, separate technician and helper hours and rates. Elapsed days are not person-hours.
Separate total time on site from necessary hours for this covered operation. Documented
attendance bounds the allocation for each person. State assumptions about working hours per day,
other tasks and helper overlap. When allocation is unclear, show a defensible range.
Use a range for unstated hours or part-time attendance. Check regular vs emergency work.
For a flat-rate job, reconcile its components to ONE job. For an hourly line, return the hourly
price and justified hours separately. Check hire duration, metered kWh, trips per contractor,
loads, materials and VAT. Exclude duplicate components across trades and apply contractual
inclusions and caps. For replacement goods, match specification and the contractual basis.
Use the rationale or price evidence field to identify the deciding clause, quantities, rate and
its source or assumption on high-exposure lines. Keep document facts distinct from assumptions.
"""

LOOKUP = """
When the case already supplies an applicable tariff or exact comparable price, use it.
Otherwise search only for the largest unresolved price component that could change a payable line.
Prefer a dated local contractor tariff or supplier price sheet for the invoice date and trade.
Use generic queries without claim details, names or addresses. Check role, billing unit,
inclusions, and net vs gross. Cite the matching URL and rate in the affected line's explanation.
If no comparable price is available, label the estimate as an assumption. A market rate
informs the price of work; the case documents determine which work and hours are payable.
"""
