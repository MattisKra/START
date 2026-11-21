"""Structured-output schema for the LLM.

The model estimates facts (validity, quantity, net unit price range, VAT).
Python turns those into gross totals and into the (a, b) pair, so the
arithmetic and the strategy stay deterministic and tunable.
"""

from pydantic import BaseModel, Field


class LineEstimate(BaseModel):
    index: int = Field(description="0-based position of the line on the invoice, in invoice order.")
    invoice_text: str = Field(description="The line item text as written on the invoice.")
    unit: str = Field(description="Unit as written on the invoice, e.g. m2, Stk, h, pauschal.")
    quantity_invoiced: float = Field(description="Quantity as written on the invoice.")
    rationale: str = Field(
        description="One or two sentences: coverage, relation to the damage, quantity and price reasoning."
    )
    covered: bool = Field(description="True if the policy covers this item (no exclusion applies).")
    related: bool = Field(description="True if the item is plausibly needed to repair the reported damage.")
    p_valid: float = Field(
        description="Probability from 0 to 1 that the item is both covered and related, i.e. has a positive fair value."
    )
    quantity_justified: float = Field(
        description="Largest quantity a claims expert would accept given the damage description and photos, "
        "assuming the line is valid. Equal to quantity_invoiced if that is plausible. Never 0 just because "
        "the line is excluded or unrelated; that is captured by p_valid."
    )
    net_unit_price_p10: float = Field(
        description="10th percentile of the maximum reasonable NET price per unit in EUR, assuming the line is valid. Never 0 just because the line is excluded or unrelated."
    )
    net_unit_price_p50: float = Field(
        description="Median of the maximum reasonable NET price per unit in EUR, assuming the line is valid. Never 0 just because the line is excluded or unrelated."
    )
    net_unit_price_p90: float = Field(
        description="90th percentile of the maximum reasonable NET price per unit in EUR, assuming the line is valid. Never 0 just because the line is excluded or unrelated."
    )
    vat_rate: float = Field(description="VAT rate as a fraction, e.g. 0.19 for 19%.")


class CaseEstimate(BaseModel):
    damage_summary: str = Field(description="What was damaged, where, and how, in one or two sentences.")
    policy_notes: str = Field(description="Exclusions or limits in the policy that matter for this invoice.")
    lines: list[LineEstimate] = Field(description="Exactly one entry per invoice line, in invoice order.")
