"""Document -> NLPResult(s). One result per mentioned company (max 3), or one company-less result.
LIMITATION: sentiment is document-level, not target-aware: every company in a headline shares its score."""
import logging

from app.nlp import entities as ent
from app.nlp.companies import COMPANIES
from app.nlp.events import EventClassifier
from app.nlp.sentiment import SentimentBackend
from app.schemas.document import RawDocument
from app.schemas.nlp import NLPResult

log = logging.getLogger(__name__)
MAX_COMPANIES_PER_DOC = 3


def analyze(docs: list[RawDocument], sentiment: SentimentBackend, events: EventClassifier,
            model_info: str = "") -> list[NLPResult]:
    if not docs:
        return []
    sents = sentiment.predict([d.text for d in docs])
    results: list[NLPResult] = []
    for d, s in zip(docs, sents):
        ents = ent.extract(d.text)
        ev = events.classify(d.text)
        targets = ents.tickers[:MAX_COMPANIES_PER_DOC] or [None]
        for t in targets:
            results.append(NLPResult(
                doc_id=d.id, source=d.source, source_name=d.source_name, timestamp=d.timestamp, text=d.text,
                simulated=d.simulated, ticker=t, company=COMPANIES[t]["name"] if t else None,
                sentiment_score=s.score, sentiment_probs=s.probs, sentiment_confidence=s.confidence,
                event_type=ev.event_type, event_confidence=ev.confidence, event_method=ev.method,
                event_scores=ev.scores, entities=ents.as_dict(), model_info=model_info))
    log.info("NLP: %d docs -> %d results", len(docs), len(results))
    return results
