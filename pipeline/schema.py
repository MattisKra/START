"""Structured output of the invoice extraction step."""

from pydantic import BaseModel, Field


class InvoiceLine(BaseModel):
    position: int = Field(description="The number printed in the POS. column. Numbering can continue from a previous invoice.")
    description: str = Field(description="The DESCRIPTION cell, verbatim, wrapped lines joined with a single space.")
    quantity: float = Field(description="The number printed in the AMOUNT column.")
    unit: str = Field(description="The UNIT cell, verbatim, e.g. 'pcs', 'hrs', 'm2', 'flat rate'.")


class Invoice(BaseModel):
    invoice_no: str
    date: str = Field(description="As printed, e.g. '16 Mar 2026'.")
    due_date: str = Field(description="As printed.")
    trade: str = Field(description="The TRADE field, e.g. 'Plumbing'.")
    issuer_name: str = Field(description="Company name in the FROM box.")
    issuer_address: str = Field(description="Address lines in the FROM box, joined with ', '.")
    recipient_name: str = Field(description="Name in the TO box.")
    recipient_address: str = Field(description="Address lines in the TO box, joined with ', '.")
    lines: list[InvoiceLine]
    other_text: str = Field(
        description="Any printed content that fits no other field (prices, totals, remarks, stamps). "
        "Empty string if there is none. Ignore the page header, logo and footer."
    )


class InvoiceExtraction(BaseModel):
    invoices: list[Invoice] = Field(description="One entry per invoice, in page order.")
