from __future__ import annotations

COMMON_ACRONYMS = {
    "atm",
    "axis",
    "gst",
    "hdfc",
    "icici",
    "idfc",
    "imps",
    "neft",
    "rtgs",
    "sbi",
    "upi",
}


def normalize_label(value: str | None) -> str | None:
    if value is None:
        return None

    text = " ".join(value.split()).strip()
    if not text:
        return None

    normalized_parts: list[str] = []
    for part in text.split(" "):
        if part.isupper() and len(part) > 1:
            normalized_parts.append(part)
        elif part.lower() in COMMON_ACRONYMS:
            normalized_parts.append(part.upper())
        else:
            normalized_parts.append(part[:1].upper() + part[1:].lower())

    return " ".join(normalized_parts)


def normalize_label_list(values: list[str] | None) -> list[str]:
    if not values:
        return []

    normalized_values = []
    for value in values:
        normalized = normalize_label(value)
        if normalized:
            normalized_values.append(normalized)
    return normalized_values


def normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    return text.upper()


def normalize_period(value: str | None) -> str | None:
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    return text.lower()
