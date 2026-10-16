"""Local dataset loaders (Kaggle CSVs + bundled sample JSONL). All return normalised RawDocuments."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.ingestion.cleaning import clean_text, make_id
from app.schemas.document import RawDocument
from app.schemas.signal import SourceType

log = logging.getLogger(__name__)

TEXT_COLS = ["text", "tweet", "content", "headline", "title", "Text", "Tweet"]
DATE_COLS = ["date", "created_at", "timestamp", "datetime", "Date", "Datetime"]
LABEL_COLS = ["sentiment", "label", "polarity", "Sentiment"]


def _pick(cols: list[str], candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in cols), None)


def _norm_label(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().lower()
    return {"pos": "positive", "neg": "negative", "neu": "neutral",
            "1": "positive", "-1": "negative", "0": "neutral", "4": "positive", "2": "neutral"}.get(s, s)


def load_phrasebank_csv(path: Path, limit: int | None = None) -> list[RawDocument]:
    """Kaggle 'Sentiment Analysis for Financial News' (all-data.csv): headerless, latin-1, cols = label,text.
    The file has no timestamps, so ingest time is used and flagged."""
    df = pd.read_csv(path, header=None, names=["label", "text"], encoding="latin-1")
    now = datetime.now(timezone.utc)
    docs = []
    for lab, txt in zip(df["label"], df["text"]):
        t = clean_text(str(txt))
        if t:
            docs.append(RawDocument(id=make_id("phrasebank", t), source=SourceType.NEWS,
                                    source_name="kaggle-financial-news", timestamp=now, text=t,
                                    label=_norm_label(lab), timestamp_is_ingest_time=True))
        if limit and len(docs) >= limit:
            break
    log.info("Loaded %d financial-news rows from %s", len(docs), path.name)
    return docs


def load_tweets_csv(path: Path, source_name: str = "kaggle-tweets", limit: int | None = None) -> list[RawDocument]:
    """Generic tweet CSV loader with column auto-detection (Kaggle tweet datasets vary in schema)."""
    df = pd.read_csv(path, encoding="utf-8", encoding_errors="replace", on_bad_lines="skip")
    cols = list(df.columns)
    tcol, dcol, lcol = _pick(cols, TEXT_COLS), _pick(cols, DATE_COLS), _pick(cols, LABEL_COLS)
    if tcol is None:
        raise ValueError(f"No text column found in {path.name}; columns={cols}")
    now = datetime.now(timezone.utc)
    ts = pd.to_datetime(df[dcol], errors="coerce", utc=True) if dcol else pd.Series([pd.NaT] * len(df))
    docs = []
    for i, row in df.iterrows():
        t = clean_text(str(row[tcol]))
        if not t:
            continue
        stamp = ts.iloc[i]
        missing = pd.isna(stamp)
        docs.append(RawDocument(id=make_id(source_name, t), source=SourceType.SOCIAL, source_name=source_name,
                                timestamp=now if missing else stamp.to_pydatetime(), text=t,
                                label=_norm_label(row[lcol]) if lcol else None,
                                timestamp_is_ingest_time=bool(missing)))
        if limit and len(docs) >= limit:
            break
    log.info("Loaded %d tweets from %s (cols: text=%s date=%s label=%s)", len(docs), path.name, tcol, dcol, lcol)
    return docs


def load_sample_jsonl(path: Path) -> list[RawDocument]:
    """Bundled SYNTHETIC fallback data. Always flagged simulated=True."""
    docs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        t = clean_text(r["text"])
        docs.append(RawDocument(id=make_id(r["source_name"], t), source=SourceType(r["source"]),
                                source_name=r["source_name"], timestamp=datetime.fromisoformat(r["timestamp"]),
                                text=t, simulated=True))
    return docs
