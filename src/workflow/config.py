from typing import Final

MAX_SPECIALISTS_PER_REQUEST: Final[int] = 3
SPECIALIST_ROUTES: Final[frozenset[str]] = frozenset(
    {
        "faq_reader",
        "professional_suggester",
        "agency_suggester",
        "solar_panel_specialist",
    }
)
