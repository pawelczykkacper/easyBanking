"""Conservative description-based classification; unknown debits stay visible."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
import unicodedata

def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold().replace("ł", "l"))
                   if not unicodedata.combining(c))

def classify(row):
    code = row.get("bank_transaction_code") or {}
    info = row.get("remittance_information") or []
    if isinstance(info, str):
        info = [info]
    text = normalized(" ".join([code.get("description", ""), row.get("note") or "", *info]))
    if re.search(r"bankomat|wyplat|wplat|cash withdrawal|cash deposit|zwrot|refund|reversal|anul|prowizj|oplata|fee|przelew|transfer", text):
        return "excluded"
    payment = re.search(r"platnosc|platnosci|zakup|purchase|payment|transakcja bezgotowkowa", text)
    if re.search(r"\bblik\b", text):
        return "blik" if payment else "unknown"
    if payment and re.search(r"kart|card", text):
        return "card"
    return "unknown"

def count(rows, start, end):
    result = dict(card=0, blik=0, unknown=0, excluded=0)
    amounts = {}
    unknown_details = []
    seen = set()
    for row in rows:
        ident = row.get("transaction_id") or row.get("entry_reference")
        if ident:
            if ident in seen:
                continue
            seen.add(ident)
        if row.get("status") != "BOOK" or row.get("credit_debit_indicator") != "DBIT":
            continue
        try:
            booked = date.fromisoformat(row["booking_date"][:10])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Missing or invalid booking date") from None
        if start <= booked <= end:
            kind = classify(row)
            result[kind] += 1
            if kind == "unknown":
                info = row.get("remittance_information") or []
                if isinstance(info, str):
                    info = [info]
                code = row.get("bank_transaction_code") or {}
                description = " · ".join(str(part).strip() for part in
                    [code.get("description", ""), row.get("note") or "", *info]
                    if part and str(part).strip()) or "Brak opisu"
                amount = row.get("transaction_amount") or {}
                unknown_details.append({
                    "date": booked.isoformat(),
                    "description": description[:500],
                    "amount": amount.get("amount"),
                    "currency": amount.get("currency"),
                })
            if kind in ("card", "blik"):
                amount = row.get("transaction_amount") or {}
                currency = amount.get("currency")
                raw_value = amount.get("amount")
                if not currency or raw_value is None:
                    raise ValueError("Payment is missing amount or currency")
                try:
                    value = Decimal(str(raw_value))
                except InvalidOperation:
                    raise ValueError("Payment has invalid amount") from None
                amounts[currency] = amounts.get(currency, Decimal("0")) + value
    result["amounts"] = amounts
    result["unknown_details"] = unknown_details
    return result
