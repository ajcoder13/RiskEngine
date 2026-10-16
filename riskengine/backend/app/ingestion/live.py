"""Live news clients. Both raise IngestionError on any failure so the service can fall back."""
import logging
from datetime import datetime, timezone

import httpx

from app.ingestion.cleaning import clean_text, make_id
from app.schemas.document import RawDocument
from app.schemas.signal import SourceType

log = logging.getLogger(__name__)


class IngestionError(RuntimeError):
    pass


def _get_json(client: httpx.Client, url: str, params: dict) -> dict:
    try:
        r = client.get(url, params=params)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise IngestionError(f"{url}: {e}") from e


def parse_gdelt(payload: dict) -> list[RawDocument]:
    """GDELT DOC 2.0 artlist JSON: {'articles': [{url, title, seendate 'YYYYMMDDTHHMMSSZ', domain, ...}]}"""
    docs = []
    for a in payload.get("articles", []):
        title = clean_text(a.get("title", ""))
        if not title:
            continue
        try:
            ts = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            ts = datetime.now(timezone.utc)
        docs.append(RawDocument(id=make_id("gdelt", title), source=SourceType.NEWS,
                                source_name=f"gdelt:{a.get('domain', 'unknown')}", timestamp=ts,
                                text=title, url=a.get("url")))
    return docs


def parse_newsapi(payload: dict) -> list[RawDocument]:
    docs = []
    for a in payload.get("articles", []):
        text = clean_text(" ".join(x for x in (a.get("title"), a.get("description")) if x))
        if not text:
            continue
        try:
            ts = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError):
            ts = datetime.now(timezone.utc)
        src = (a.get("source") or {}).get("name") or "unknown"
        docs.append(RawDocument(id=make_id("newsapi", text), source=SourceType.NEWS,
                                source_name=f"newsapi:{src}", timestamp=ts, text=text, url=a.get("url")))
    return docs


def fetch_gdelt(client: httpx.Client, query: str, limit: int = 100) -> list[RawDocument]:
    payload = _get_json(client, "https://api.gdeltproject.org/api/v2/doc/doc",
                        {"query": query, "mode": "artlist", "format": "json",
                         "maxrecords": min(limit, 250), "sort": "datedesc", "timespan": "24h"})
    return parse_gdelt(payload)


def fetch_newsapi(client: httpx.Client, api_key: str, query: str = "stocks OR earnings OR economy",
                  limit: int = 100) -> list[RawDocument]:
    if not api_key:
        raise IngestionError("NEWSAPI_KEY not set")
    payload = _get_json(client, "https://newsapi.org/v2/everything",
                        {"q": query, "language": "en", "sortBy": "publishedAt",
                         "pageSize": min(limit, 100), "apiKey": api_key})
    return parse_newsapi(payload)
