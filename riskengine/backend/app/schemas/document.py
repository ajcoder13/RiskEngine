from datetime import datetime

from pydantic import BaseModel

from app.schemas.signal import SourceType


class RawDocument(BaseModel):
    """One piece of unstructured text, normalised across all sources."""
    id: str
    source: SourceType
    source_name: str
    timestamp: datetime
    text: str
    url: str | None = None
    label: str | None = None      # ground-truth sentiment, ONLY if the dataset ships one
    simulated: bool = False       # True for bundled synthetic sample data
    timestamp_is_ingest_time: bool = False  # dataset had no date; ingest time used


class SourceStatus(BaseModel):
    name: str
    mode: str          # live | local | sample
    count: int
    error: str | None = None


class IngestionResult(BaseModel):
    documents: list[RawDocument]
    report: list[SourceStatus]
