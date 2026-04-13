from zoneinfo import available_timezones


FALLBACK_TIMEZONE_OPTIONS = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Phoenix",
    "America/Anchorage",
    "Pacific/Honolulu",
    "America/Toronto",
    "America/Vancouver",
    "America/Mexico_City",
    "America/Bogota",
    "America/Lima",
    "America/Santiago",
    "America/Sao_Paulo",
    "America/Argentina/Buenos_Aires",
    "UTC",
    "Europe/London",
    "Europe/Dublin",
    "Europe/Madrid",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Rome",
    "Europe/Warsaw",
    "Europe/Prague",
    "Europe/Vienna",
    "Europe/Amsterdam",
    "Europe/Brussels",
    "Europe/Zurich",
    "Europe/Stockholm",
    "Europe/Oslo",
    "Europe/Helsinki",
    "Europe/Minsk",
    "Europe/Kyiv",
    "Europe/Istanbul",
    "Asia/Jerusalem",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Bangkok",
    "Asia/Singapore",
    "Asia/Hong_Kong",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Australia/Perth",
    "Pacific/Auckland",
]


def get_timezone_options(current_timezone: str | None = None) -> list[str]:
    zones = sorted(available_timezones())

    if not zones:
        zones = FALLBACK_TIMEZONE_OPTIONS.copy()

    if current_timezone and current_timezone not in zones:
        zones.insert(0, current_timezone)

    return zones
