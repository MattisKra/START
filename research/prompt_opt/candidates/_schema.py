"""Schema variants: price-field descriptions that follow the policy's stated valuation basis."""

from pydantic import Field

from claimbot.schema import CaseEstimate as _CE, LineEstimate as _LE

_VAL = ("assuming the line is valid. For replaced property use the valuation basis the policy states: "
        "usually the current price of an equivalent standard-grade replacement (no premium upgrade); deduct "
        "depreciation only if the policy pays time value for this class of property. Before payout_fraction. "
        "Never 0 just because the line is excluded or unrelated.")


class LineLit(_LE):
    net_unit_price_p10: float = Field(description="10th percentile of the maximum reasonable NET price per unit in EUR, " + _VAL)
    net_unit_price_p50: float = Field(description="Median of the maximum reasonable NET price per unit in EUR, " + _VAL)
    net_unit_price_p90: float = Field(description="90th percentile of the maximum reasonable NET price per unit in EUR, " + _VAL)


class CaseLit(_CE):
    lines: list[LineLit] = Field(description="Exactly one entry per invoice line, in invoice order.")


class LineLitCite(LineLit):
    rationale: str = Field(
        description="Two or three sentences: name the policy clause(s) that decide coverage of this line "
        "(exclusion, not-a-repair-cost list, valuation basis, reduction), then relation to the damage, quantity and price."
    )


class CaseLitCite(_CE):
    lines: list[LineLitCite] = Field(description="Exactly one entry per invoice line, in invoice order.")
