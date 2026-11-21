"""Quantity tokens used by the English invoice layout and archived plain text."""

# Existing ungrouped invoices also use decimal commas. Grouped decimals such as
# 2,412.1 have an unambiguous thousands mark and must be consumed as one token.
QUANTITY = r"(?:\d{1,3}(?:,\d{3})+\.\d+|\d+(?:[.,]\d+)?)"


def parse_quantity(token: str) -> float:
    if "." in token:
        return float(token.replace(",", ""))
    return float(token.replace(",", "."))
