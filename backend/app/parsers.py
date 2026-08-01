import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal

from defusedxml import ElementTree


def parse_csv(content: bytes) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    fields = {x.strip().lower() for x in (reader.fieldnames or [])}
    if not {"date", "description", "amount"}.issubset(fields):
        raise ValueError("CSV requires date, description and amount columns")
    return [{"date": date.fromisoformat(row["date"]), "value_date": date.fromisoformat(row["value_date"]) if row.get("value_date") else None, "reference": row.get("reference"), "description": row["description"], "amount": Decimal(row["amount"].replace(" ", "").replace(",", "."))} for row in reader]


def parse_mt940(content: bytes) -> list[dict]:
    text = content.decode("utf-8", errors="strict")
    rows, current = [], None
    pattern = re.compile(r"^:61:(\d{6})(\d{4})?([DC])([0-9,]+)(?:N\w{3})?(.*)$")
    for raw in text.splitlines():
        if match := pattern.match(raw.strip()):
            year = 2000 + int(match.group(1)[:2]); month = int(match.group(1)[2:4]); day = int(match.group(1)[4:6])
            amount = Decimal(match.group(4).replace(",", ".")) * (-1 if match.group(3) == "D" else 1)
            current = {"date": date(year, month, day), "value_date": None, "reference": match.group(5).strip() or None, "description": match.group(5).strip() or "Bank transaction", "amount": amount}; rows.append(current)
        elif raw.startswith(":86:") and current:
            current["description"] = raw[4:].strip()
    if not rows: raise ValueError("No MT940 transaction lines found")
    return rows


def _text(element, suffix: str) -> str | None:
    child = next((x for x in element.iter() if x.tag.endswith(suffix) and x.text and x.text.strip()), None)
    return child.text.strip() if child is not None else None


def parse_camt053(content: bytes) -> list[dict]:
    root = ElementTree.fromstring(content)
    rows = []
    for entry in (x for x in root.iter() if x.tag.endswith("Ntry")):
        amount_text = _text(entry, "Amt"); booking = _text(entry, "BookgDt") or _text(entry, "Dt")
        if not amount_text or not booking: continue
        indicator = _text(entry, "CdtDbtInd")
        amount = Decimal(amount_text) * (-1 if indicator == "DBIT" else 1)
        rows.append({"date": datetime.fromisoformat(booking[:10]).date(), "value_date": None, "reference": _text(entry, "AcctSvcrRef"), "description": _text(entry, "AddtlNtryInf") or "Bank transaction", "amount": amount})
    if not rows: raise ValueError("No CAMT.053 entries found")
    return rows


def parse_statement(content: bytes, fmt: str) -> list[dict]:
    parsers = {"csv": parse_csv, "mt940": parse_mt940, "camt053": parse_camt053}
    if fmt not in parsers: raise ValueError(f"Unsupported bank format: {fmt}")
    return parsers[fmt](content)
