"""Conservative description-based classification; unknown debits stay visible."""
from datetime import date
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
    result = dict(card=0, blik=0, total=0, unknown=0, excluded=0)
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
            result[classify(row)] += 1
    result["total"] = result["card"] + result["blik"]
    return result
