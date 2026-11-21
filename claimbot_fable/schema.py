"""Structured output of the reader. The model fills facts; engine.py does the arithmetic."""

from typing import Literal

from pydantic import BaseModel, Field


class ReaderLine(BaseModel):
    index: int = Field(description="0-based position of the line on the invoice, in invoice order.")
    invoice_text: str = Field(description="The line item text as written on the invoice.")
    unit: str = Field(description="Unit as written on the invoice, e.g. m2, Stk, pcs, hrs, flat rate.")
    quantity_invoiced: float = Field(description="Quantity as written on the invoice.")
    quantity_justified: float = Field(
        description="Largest quantity the damage description (and photos) justify for this line, assuming the line is valid. "
        "Equal to quantity_invoiced when the invoiced quantity is plausible; smaller when the description shows less was needed. "
        "Never 0 just because the line is excluded; that is captured by p_valid."
    )
    covered: bool = Field(description="True if the policy covers this item (no exclusion applies).")
    related: bool = Field(description="True if the item belongs to the reported damage and event.")
    p_valid: float = Field(description="Probability from 0 to 1 that the line is both covered and related, i.e. has a positive fair value.")
    net_unit_price_p10: float = Field(
        description="10th percentile of the maximum amount the policy owes per unit, NET of VAT, in EUR, if the line is valid, on the policy's own "
        "valuation basis (usually the same kind and quality in new condition; do NOT depreciate unless the policy says so), before payout_fraction."
    )
    net_unit_price_p50: float = Field(description="Median of the same quantity (net per unit, EUR, before payout_fraction).")
    net_unit_price_p90: float = Field(description="90th percentile of the same quantity (net per unit, EUR, before payout_fraction).")
    vat_rate: float = Field(description="VAT rate as a fraction, e.g. 0.19.")
    payout_fraction: float = Field(
        description="Fraction from 0 to 1 of the amount the policy actually pays after PROPORTIONAL reductions that apply to this line "
        "(e.g. 0.5 when the indemnity is halved for a missing protective device, a co-payment share). 1.0 if none. "
        "Aggregate sub-limits and caps shared by several lines go into aggregate_limits, not here."
    )
    rationale: str = Field(description="Two or three sentences with the clause numbers that decided coverage, valuation, reductions and quantity.")


class AggregateLimit(BaseModel):
    amount_gross: float = Field(description="The ceiling in EUR INCLUDING VAT (convert if the policy states it net).")
    line_indices: list[int] = Field(description="0-based indices of the invoice lines that count against this ceiling.")
    clause: str = Field(description="Clause number and a short quote.")


class Anchor(BaseModel):
    total_gross: float = Field(description="A total in EUR (gross) that the description states or clearly implies for these lines together.")
    line_indices: list[int] = Field(description="0-based indices of the invoice lines it applies to.")
    kind: Literal["total", "upper_bound"] = Field(description="'total' if the lines together should come to about this amount, 'upper_bound' if it is only a ceiling.")
    quote: str = Field(description="The words in the description the anchor comes from.")


class ReaderCase(BaseModel):
    damage_summary: str = Field(description="What was damaged, where and how, in one or two sentences.")
    policy_notes: str = Field(description="The clauses that matter for this invoice: valuation basis, reductions, limits, exclusions.")
    lines: list[ReaderLine] = Field(description="Exactly one entry per invoice line, in invoice order.")
    aggregate_limits: list[AggregateLimit] = Field(description="Sub-limits or caps shared by several lines (empty list if none).")
    anchors: list[Anchor] = Field(description="Totals stated in the description (empty list if none).")
