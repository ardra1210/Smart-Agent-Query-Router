"""Split a compound question ("show my PRs and my Linear tickets") into parts.

Splitting is only a proposal: the router uses the parts only if every part
routes cleanly and they land on more than one agent. "bugs and issues" stays
one question because its halves don't route on their own.
"""

import re

_SEPARATORS = re.compile(r"\s*(?:;|,?\s*\b(?:and also|and then|as well as|and|also|plus)\b)\s*", re.IGNORECASE)


def split_query(query: str) -> list[str]:
    return [part.strip(" ,.?!") for part in _SEPARATORS.split(query) if part.strip(" ,.?!")]
