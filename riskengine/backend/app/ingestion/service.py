"""Hybrid ingestion: live (optional) + local Kaggle files + bundled sample fallback. Never raises."""
import logging
from pathlib import Path

import httpx

from app.config import Settings
from app.ingestion import live, loaders
from app.ingestion.cleaning import dedupe
from app.schemas.document import IngestionResult, RawDocument, SourceStatus
from app.schemas.signal import SourceType

log = logging.getLogger(__name__)

NEWS_FILE = "all-data.csv"      # Kaggle: Sentiment Analysis for Financial News
TWEETS_FILE = "tweets.csv"      # Kaggle: tweet-sentiment-vs-stock dataset (rename the CSV to this)
SAMPLE_NEWS = "news_sample.jsonl"
SAMPLE_TWEETS = "tweets_sample.jsonl"


def collect(settings: Settings, client: httpx.Client | None = None) -> IngestionResult:
    docs: list[RawDocument] = []
    report: list[SourceStatus] = []
    raw, sample = settings.data_dir / "raw", settings.data_dir / "sample"
    limit = settings.ingest_limit

    def attempt(name: str, mode: str, fn) -> list[RawDocument]:
        try:
            out = fn()
            report.append(SourceStatus(name=name, mode=mode, count=len(out)))
            return out
        except Exception as e:  # any failure -> report + fall through to fallback
            log.warning("Source %s failed: %s", name, e)
            report.append(SourceStatus(name=name, mode=mode, count=0, error=str(e)[:200]))
            return []

    if settings.use_live_data:
        own = client is None
        client = client or httpx.Client(timeout=settings.http_timeout)
        try:
            docs += attempt("gdelt", "live", lambda: live.fetch_gdelt(client, settings.gdelt_query, limit))
            if settings.newsapi_key:
                docs += attempt("newsapi", "live", lambda: live.fetch_newsapi(client, settings.newsapi_key, limit=limit))
        finally:
            if own:
                client.close()

    def local_or_sample(kind: SourceType, raw_file: str, loader, sample_file: str):
        p: Path = raw / raw_file
        if p.exists():
            got = attempt(raw_file, "local", lambda: loader(p))
            if got:
                return got
        return attempt(sample_file, "sample", lambda: loaders.load_sample_jsonl(sample / sample_file))

    docs += local_or_sample(SourceType.NEWS, NEWS_FILE, lambda p: loaders.load_phrasebank_csv(p, limit), SAMPLE_NEWS)
    docs += local_or_sample(SourceType.SOCIAL, TWEETS_FILE, lambda p: loaders.load_tweets_csv(p, limit=limit), SAMPLE_TWEETS)

    before = len(docs)
    docs = dedupe(docs)
    log.info("Ingested %d docs (%d after dedup) from %d sources", before, len(docs), len(report))
    return IngestionResult(documents=docs, report=report)
