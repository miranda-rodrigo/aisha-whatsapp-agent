"""Timezone inference from phone number prefix (DDI + DDD for Brazil)."""

import re

# DDI country code -> IANA timezone (best single representative)
# Only countries with a single timezone or a clear dominant one.
_DDI_TO_TZ: dict[str, str] = {
    "1":   "America/New_York",      # USA/Canada (Eastern as default)
    "351": "Europe/Lisbon",         # Portugal
    "44":  "Europe/London",         # UK
    "49":  "Europe/Berlin",         # Germany
    "33":  "Europe/Paris",          # France
    "34":  "Europe/Madrid",         # Spain
    "39":  "Europe/Rome",           # Italy
    "31":  "Europe/Amsterdam",      # Netherlands
    "32":  "Europe/Brussels",       # Belgium
    "41":  "Europe/Zurich",         # Switzerland
    "43":  "Europe/Vienna",         # Austria
    "48":  "Europe/Warsaw",         # Poland
    "46":  "Europe/Stockholm",      # Sweden
    "47":  "Europe/Oslo",           # Norway
    "45":  "Europe/Copenhagen",     # Denmark
    "358": "Europe/Helsinki",       # Finland
    "353": "Europe/Dublin",         # Ireland
    "52":  "America/Mexico_City",   # Mexico
    "54":  "America/Argentina/Buenos_Aires",  # Argentina
    "56":  "America/Santiago",      # Chile
    "57":  "America/Bogota",        # Colombia
    "58":  "America/Caracas",       # Venezuela
    "51":  "America/Lima",          # Peru
    "593": "America/Guayaquil",     # Ecuador
    "598": "America/Montevideo",    # Uruguay
    "595": "America/Asuncion",      # Paraguay
    "591": "America/La_Paz",        # Bolivia
    "61":  "Australia/Sydney",      # Australia
    "64":  "Pacific/Auckland",      # New Zealand
    "81":  "Asia/Tokyo",            # Japan
    "82":  "Asia/Seoul",            # South Korea
    "86":  "Asia/Shanghai",         # China
    "91":  "Asia/Kolkata",          # India
    "971": "Asia/Dubai",            # UAE
    "966": "Asia/Riyadh",           # Saudi Arabia
    "972": "Asia/Jerusalem",        # Israel
    "90":  "Europe/Istanbul",       # Turkey
    "7":   "Europe/Moscow",         # Russia
    "27":  "Africa/Johannesburg",   # South Africa
    "20":  "Africa/Cairo",          # Egypt
    "234": "Africa/Lagos",          # Nigeria
    "254": "Africa/Nairobi",        # Kenya
}

# Brazil DDD -> IANA timezone
# Source: ANATEL DDD regions
_BR_DDD_TO_TZ: dict[str, str] = {
    # UTC-3 (Brasília)
    "11": "America/Sao_Paulo", "12": "America/Sao_Paulo", "13": "America/Sao_Paulo",
    "14": "America/Sao_Paulo", "15": "America/Sao_Paulo", "16": "America/Sao_Paulo",
    "17": "America/Sao_Paulo", "18": "America/Sao_Paulo", "19": "America/Sao_Paulo",
    "21": "America/Sao_Paulo", "22": "America/Sao_Paulo", "24": "America/Sao_Paulo",
    "27": "America/Sao_Paulo", "28": "America/Sao_Paulo",
    "31": "America/Sao_Paulo", "32": "America/Sao_Paulo", "33": "America/Sao_Paulo",
    "34": "America/Sao_Paulo", "35": "America/Sao_Paulo", "37": "America/Sao_Paulo",
    "38": "America/Sao_Paulo",
    "41": "America/Sao_Paulo", "42": "America/Sao_Paulo", "43": "America/Sao_Paulo",
    "44": "America/Sao_Paulo", "45": "America/Sao_Paulo", "46": "America/Sao_Paulo",
    "47": "America/Sao_Paulo", "48": "America/Sao_Paulo", "49": "America/Sao_Paulo",
    "51": "America/Sao_Paulo", "53": "America/Sao_Paulo", "54": "America/Sao_Paulo",
    "55": "America/Sao_Paulo",
    "61": "America/Sao_Paulo", "62": "America/Sao_Paulo", "64": "America/Sao_Paulo",
    "65": "America/Cuiaba",   "66": "America/Cuiaba",   # Mato Grosso (UTC-4, no DST)
    "67": "America/Campo_Grande",  # Mato Grosso do Sul (UTC-4, with DST)
    "68": "America/Rio_Branco",    # Acre (UTC-5)
    "69": "America/Porto_Velho",   # Rondônia (UTC-4)
    "71": "America/Bahia",  "73": "America/Bahia",  "74": "America/Bahia",
    "75": "America/Bahia",  "77": "America/Bahia",
    "79": "America/Sao_Paulo",  # Sergipe
    "81": "America/Recife", "82": "America/Maceio", "83": "America/Fortaleza",
    "84": "America/Fortaleza",  # RN — same tz
    "85": "America/Fortaleza", "86": "America/Fortaleza",
    "87": "America/Recife",    "88": "America/Fortaleza",
    "89": "America/Fortaleza",  # Piauí
    "91": "America/Belem",  "92": "America/Manaus", "93": "America/Belem",
    "94": "America/Belem",  "95": "America/Boa_Vista",
    "96": "America/Belem",  # Amapá
    "97": "America/Manaus", "98": "America/Fortaleza", "99": "America/Fortaleza",
}


def infer_timezone(phone: str) -> str | None:
    """Infer IANA timezone from a phone number (E.164 format without '+').

    Returns None if inference is not possible or too ambiguous.
    Only returns a value when reasonably confident.
    """
    # Normalize: remove +, spaces, dashes
    digits = re.sub(r"[^\d]", "", phone)

    # Brazil: +55 + DDD (2 digits) + number
    if digits.startswith("55") and len(digits) >= 4:
        ddd = digits[2:4]
        tz = _BR_DDD_TO_TZ.get(ddd)
        if tz:
            return tz

    # Try 3-digit DDI prefixes first (to avoid mismatching, e.g. "353" vs "35")
    for prefix_len in (3, 2, 1):
        prefix = digits[:prefix_len]
        if prefix in _DDI_TO_TZ:
            # Skip Brazil (handled above) and ambiguous multi-tz countries
            if prefix == "55":
                return None  # BR without valid DDD — too uncertain
            if prefix == "1":
                return None  # USA/Canada — too large and ambiguous
            return _DDI_TO_TZ[prefix]

    return None
