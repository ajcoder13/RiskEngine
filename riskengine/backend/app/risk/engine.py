"""Orchestrates ingestion -> NLP -> impact scoring -> store. Backends are loaded once and cached."""
import logging
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.ingestion import service as ingestion
from app.ingestion.cleaning import clean_text, make_id
from app.nlp.events import EventClassifier
from app.nlp.pipeline import analyze
from app.nlp.sentiment import SentimentBackend, get_backend
from app.risk.builder import build_signals
from app.risk.params import RiskParams, load_params
from app.risk.store import SignalStore
from app.schemas.document import IngestionResult, RawDocument
from app.schemas.signal import RiskSignal, SourceType

log = logging.getLogger(__name__)


class RiskEngine:
    def __init__(self, settings: Settings | None = None, store: SignalStore | None = None,
                 sentiment: SentimentBackend | None = None, events: EventClassifier | None = None,
                 params: RiskParams | None = None):
        self.settings = settings or get_settings()
        self.store = store or SignalStore(self.settings.data_dir / "processed" / "signals.db")
        self.params = params or load_params()
        if sentiment is None:
            sentiment, self.model_info = get_backend(self.settings.sentiment_backend)
        else:
            self.model_info = getattr(sentiment, "name", "custom")
        self.sentiment = sentiment
        self.events = events or EventClassifier.auto()
        self.last_ingestion: IngestionResult | None = None

    def process(self, docs: list[RawDocument], reference_time: datetime | None = None, persist: bool = True,
                relevant_only: bool = True) -> list[RiskSignal]:
        nlp = analyze(docs, self.sentiment, self.events, self.model_info)
        sigs = build_signals(nlp, self.params, self.settings.risk_bands, reference_time, relevant_only)
        if persist and sigs:
            self.store.upsert_many(sigs)
        return sigs

    def ingest_and_score(self) -> tuple[list[RiskSignal], IngestionResult]:
        res = ingestion.collect(self.settings)
        # Live mode scores recency against 'now'; offline replay anchors to the newest document so the demo is deterministic.
        ref = datetime.now(timezone.utc) if self.settings.use_live_data else None
        self.last_ingestion = res
        return self.process(res.documents, reference_time=ref), res

    def analyze_text(self, text: str, source: SourceType = SourceType.NEWS, source_name: str = "user-input",
                     timestamp: datetime | None = None, persist: bool = False) -> list[RiskSignal]:
        ts = timestamp or datetime.now(timezone.utc)
        t = clean_text(text)
        doc = RawDocument(id=make_id(source_name, t), source=source, source_name=source_name, timestamp=ts, text=t)
        return self.process([doc], reference_time=ts, persist=persist, relevant_only=False)
