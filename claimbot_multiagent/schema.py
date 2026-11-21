"""All specialist references use the printed invoice position."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Amount = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Basis = Literal["repair", "replacement_new", "current_value", "service", "other"]



class Coverage(BaseModel):
    position: int
    covered: bool
    probability_if_related: Probability
    basis: Basis
    payout_fraction: Probability
    clause: str


class Attribution(BaseModel):
    position: int
    related: bool
    probability: Probability
    invoice_unit: str
    related_share: Probability = Field(description="Share of the full reasonably required variable work attributable to this incident.")
    attributable_invoice_units: Amount | None = Field(description="Upper bound in printed units if supported directly, otherwise null. For fixed fees count necessary visits or jobs in printed units.")
    evidence: str


class Limit(BaseModel):
    positions: list[int]
    amount_gross: Positive
    clause: str


class Policy(BaseModel):
    coverage: list[Coverage]
    limits: list[Limit]


class Incident(BaseModel):
    attribution: list[Attribution]


class Assessment(Policy, Incident):
    pass


class Quote(BaseModel):
    position: int
    basis: Literal["repair", "replacement_new", "current_value", "service", "other", "invoice_work"]
    invoice_unit: str
    fixed_fee: bool
    operation: str
    operations: Positive | None = Field(description="Reasonable operation count for the whole invoiced scope before causal reductions. Null for unsupported conversion.")
    invoice_units_per_operation: Positive | None = Field(description="Conversion to printed units, e.g. 2 hours per door, or 1 fee per visit.")
    p10: Amount
    p50: Positive
    p90: Positive
    vat: Annotated[float, Field(ge=0, le=0.3)]
    inclusions: str
    source: str


class PriceAnchor(BaseModel):
    positions: list[int]
    total_gross: Positive
    kind: Literal["total", "upper_bound"]
    quote: str


class Valuation(BaseModel):
    quotes: list[Quote]
    anchors: list[PriceAnchor]
    lookup_queries: list[str]


class Full(Assessment, Valuation):
    pass
