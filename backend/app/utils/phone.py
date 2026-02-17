import phonenumbers


class PhoneValidationError(ValueError):
    pass


def normalize_phone(phone: str, default_region: str = "AE") -> str:
    try:
        parsed = phonenumbers.parse(phone, default_region)
    except phonenumbers.NumberParseException as exc:
        raise PhoneValidationError(str(exc)) from exc
    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        raise PhoneValidationError(f"Invalid phone number: {phone}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def dedupe_contacts(rows: list[dict]) -> list[dict]:
    seen = {}
    for row in rows:
        normalized = normalize_phone(str(row.get("phone", "")))
        row["phone_e164"] = normalized
        seen[normalized] = row
    return list(seen.values())
