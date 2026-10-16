"""Rule-based entity extraction with strict ticker linking (precision over recall).
Bare tickers (e.g. 'BA') are NOT matched: only $CASHTAGS and full company names, to avoid false links."""
import re
from dataclasses import dataclass, field

from app.nlp.companies import COMPANIES, COUNTRIES, NEG_CTX, SECTOR_KEYWORDS

_CASHTAG = re.compile(r"\$([A-Z]{1,5})\b")
_PERSON = re.compile(r"(?:CEO|[Cc]hief [Ee]xecutive|[Cc]hair(?:man|woman)?|[Gg]overnor|[Pp]resident|[Ss]ecretary)\s+"
                     r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)")


def _alias_pattern(alias: str, cs: bool) -> re.Pattern:
    ctx = NEG_CTX.get(alias, "")
    # (?<![\w&]) / (?![\w&]) act as word boundaries that also respect '&' inside names
    return re.compile(rf"(?<![\w&]){re.escape(alias)}(?![\w&]){ctx}", 0 if cs else re.I)


_PATTERNS: list[tuple[str, str, re.Pattern]] = []
for _t, _c in COMPANIES.items():
    for _a in sorted(_c["aliases"], key=len, reverse=True):
        _PATTERNS.append((_t, _a, _alias_pattern(_a, _a in _c["cs"])))


@dataclass
class Entities:
    tickers: list[str] = field(default_factory=list)       # ordered by first mention
    people: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {"companies": [COMPANIES[t]["name"] for t in self.tickers], "tickers": self.tickers,
                "people": self.people, "countries": self.countries, "sectors": self.sectors}


def extract(text: str) -> Entities:
    hits: dict[str, int] = {}
    for tkr, _alias, pat in _PATTERNS:
        m = pat.search(text)
        if m and (tkr not in hits or m.start() < hits[tkr]):
            hits[tkr] = m.start()
    for m in _CASHTAG.finditer(text):
        if m.group(1) in COMPANIES:
            hits[m.group(1)] = min(hits.get(m.group(1), m.start()), m.start())
    tickers = sorted(hits, key=hits.get)

    countries = [c for c in COUNTRIES if re.search(rf"(?<!\w){re.escape(c)}(?!\w)", text)]
    sectors = {COMPANIES[t]["sector"] for t in tickers}
    low = text.lower()
    for sec, kws in SECTOR_KEYWORDS.items():
        if any(re.search(rf"\b{kw}\b", low) for kw in kws):
            sectors.add(sec)
    return Entities(tickers=tickers, people=list(dict.fromkeys(_PERSON.findall(text))),
                    countries=countries, sectors=sorted(sectors))
