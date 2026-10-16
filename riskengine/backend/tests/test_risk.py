import math
from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.nlp.events import EventClassifier
from app.nlp.sentiment import LexiconBackend
from app.risk import scoring as sc
from app.risk.builder import build_signals
from app.risk.engine import RiskEngine
from app.risk.params import RiskParams, load_params
from app.risk.store import SignalStore
from app.risk.triggers import should_trigger_stress, trigger_signals
from app.schemas.nlp import NLPResult
from app.schemas.signal import Direction, EventType as E, RiskLevel, SourceType

P = RiskParams()
BANDS = Settings(_env_file=None).risk_bands
T0 = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)


def impact(event=E.REGULATORY, s=-0.8, c=0.8, rel=0.7, mkt=1.0, nov=1.0, rec=1.0, p=P):
    return sc.compute_impact(event=event, sentiment=s, confidence=c, reliability=rel, relevance=mkt,
                             novelty_=nov, recency_=rec, p=p)[0]


# ---- impact score
def test_impact_always_in_range_even_at_extremes():
    assert 1.0 <= impact(E.OTHER, 0, 0, 0, 0, 0, 0) <= 10.0
    top = impact(E.CREDIT_EVENT, -1, 1, 1, 1, 1, 1)
    assert 8.5 < top <= 10.0


def test_impact_monotonic_in_each_factor():
    assert impact(E.CREDIT_EVENT) > impact(E.LEGAL) > impact(E.PRODUCT_LAUNCH)          # severity
    assert impact(s=-0.9) > impact(s=-0.3)                                              # sentiment magnitude
    assert impact(c=0.9) > impact(c=0.3)                                                # confidence
    assert impact(rel=0.95) > impact(rel=0.4)                                           # source reliability
    assert impact(mkt=1.0) > impact(mkt=0.45)                                           # relevance
    assert impact(nov=1.0) > impact(nov=0.4)                                            # novelty
    assert impact(rec=1.0) > impact(rec=0.2)                                            # recency


def test_sentiment_sign_does_not_change_magnitude():
    assert impact(s=-0.7) == impact(s=0.7)


def test_breakdown_reproduces_impact_exactly():
    i, b = sc.compute_impact(event=E.GEOPOLITICAL, sentiment=-0.8, confidence=0.62, reliability=0.7,
                             relevance=0.85, novelty_=0.8, recency_=0.9, p=P)
    base = P.w_severity * P.severity[E.GEOPOLITICAL] + P.w_sentiment * 0.8
    mods = b["f_confidence"] * b["f_reliability"] * b["f_relevance"] * b["f_novelty"] * b["f_recency"]
    assert b["impact"] == i                      # breakdown and headline score agree exactly
    assert b["base"] == pytest.approx(base, abs=1e-3)
    assert i == pytest.approx(1 + 9 * (base * mods) ** P.gamma, abs=0.02)


@pytest.mark.parametrize("name,kw,lo,hi", [
    ("severe conflict, reliable source", dict(event=E.GEOPOLITICAL, s=-0.9, c=0.8, rel=0.95, mkt=0.85), 8.0, 10),
    ("large-cap credit event", dict(event=E.CREDIT_EVENT, s=-0.9, c=0.82), 8.0, 10),
    ("regulatory recall", dict(event=E.REGULATORY, s=-0.93, c=0.83), 7.0, 8.0),
    ("neutral product launch", dict(event=E.PRODUCT_LAUNCH, s=0.0, c=0.65), 1.0, 3.0),
    ("low-reliability macro tweet", dict(event=E.MACROECONOMIC, s=-0.5, c=0.5, rel=0.4, mkt=0.85), 3.0, 6.0),
])
def test_calibration_anchors(name, kw, lo, hi):
    assert lo <= impact(**kw) <= hi, name


def test_params_override_json(tmp_path):
    f = tmp_path / "p.json"
    f.write_text('{"gamma": 1.0, "severity": {"Legal": 0.9}}')
    p = load_params(f)
    assert p.gamma == 1.0 and p.severity[E.LEGAL] == 0.9 and p.severity[E.CREDIT_EVENT] == 0.9


# ---- factors
def test_source_reliability_ordering():
    assert (sc.source_reliability(SourceType.NEWS, "newsapi:Reuters") > sc.source_reliability(SourceType.NEWS, "gdelt:blog.example")
            > sc.source_reliability(SourceType.SOCIAL, "kaggle-tweets"))
    assert sc.source_reliability(SourceType.NEWS, "unknown") == 0.65


def test_novelty_and_recency():
    assert sc.novelty(0, P) == 1.0 and sc.novelty(1, P) > sc.novelty(3, P)
    assert sc.recency(T0, T0, P) == 1.0
    assert sc.recency(T0 - timedelta(hours=P.recency_halflife_hours), T0, P) == pytest.approx(0.5)
    assert sc.recency(T0 + timedelta(hours=5), T0, P) == 1.0   # future-dated docs are not penalised


def test_direction_rules():
    assert sc.direction(-0.5, E.EARNINGS, P) == Direction.ADVERSE
    assert sc.direction(0.5, E.EARNINGS, P) == Direction.FAVOURABLE
    assert sc.direction(0.0, E.EARNINGS, P) == Direction.NEUTRAL
    assert sc.direction(0.0, E.GEOPOLITICAL, P) == Direction.ADVERSE        # adverse by nature
    assert sc.direction(0.6, E.CREDIT_EVENT, P) == Direction.FAVOURABLE     # ...unless clearly positive


def test_risk_level_boundaries():
    L = lambda x: sc.risk_level(x, BANDS)
    assert (L(1), L(2.99), L(3), L(5.99), L(6), L(7.99), L(8), L(10)) == (
        RiskLevel.LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.HIGH,
        RiskLevel.CRITICAL, RiskLevel.CRITICAL)


# ---- builder
def nlp(text="x", ticker="TSLA", event=E.REGULATORY, s=-0.8, ts=T0, src=SourceType.NEWS, name="newsapi:Reuters", i=0):
    return NLPResult(doc_id=f"d{i}", source=src, source_name=name, timestamp=ts, text=text, ticker=ticker,
                     company="Tesla" if ticker else None, sentiment_score=s,
                     sentiment_probs={"positive": 0.1, "negative": 0.8, "neutral": 0.1}, sentiment_confidence=0.8,
                     event_type=event, event_confidence=0.8, event_method="rules")


def test_builder_repeat_story_is_less_novel_and_lower_impact():
    a, b = build_signals([nlp(i=1, ts=T0), nlp(i=2, ts=T0 + timedelta(hours=1))], P, BANDS)
    assert a.score_breakdown["novelty"] == 1.0 and b.score_breakdown["novelty"] < 1.0
    assert b.impact_score < a.impact_score


def test_builder_novelty_resets_outside_window():
    a, b = build_signals([nlp(i=1, ts=T0), nlp(i=2, ts=T0 + timedelta(hours=30))], P, BANDS, reference_time=T0 + timedelta(hours=30))
    assert b.score_breakdown["novelty"] == 1.0


def test_builder_favourable_is_low_risk_but_keeps_impact():
    s = build_signals([nlp(event=E.EARNINGS, s=0.9)], P, BANDS)[0]
    assert s.direction == Direction.FAVOURABLE and s.risk_level == RiskLevel.LOW and s.impact_score > 4


def test_builder_relevance_gating():
    kept = build_signals([nlp(ticker=None, event=E.OTHER, i=1), nlp(ticker=None, event=E.GEOPOLITICAL, i=2),
                          nlp(ticker="AAPL", event=E.OTHER, i=3)], P, BANDS)
    assert {s.doc_id for s in kept} == {"d2", "d3"}
    assert len(build_signals([nlp(ticker=None, event=E.OTHER)], P, BANDS, relevant_only=False)) == 1


def test_builder_handles_naive_timestamps_and_stable_ids():
    naive = nlp(ts=datetime(2026, 10, 6, 9, 0))
    s1 = build_signals([naive, nlp(i=5, ts=T0 + timedelta(hours=1))], P, BANDS)
    s2 = build_signals([naive], P, BANDS)
    assert s1[0].id == s2[0].id and s1[0].timestamp.tzinfo is not None


def test_signal_fields_valid_and_explained():
    s = build_signals([nlp()], P, BANDS)[0]
    assert -1 <= s.sentiment_score <= 1 and 1 <= s.impact_score <= 10 and 0 <= s.confidence <= 1
    assert s.confidence == pytest.approx(math.sqrt(0.64), abs=1e-3)
    assert "Regulatory" in s.reason and str(round(s.impact_score, 1)) in s.reason


# ---- store
def test_store_roundtrip_filters_and_idempotent_upsert():
    st = SignalStore()
    sigs = build_signals([nlp(i=1), nlp(i=2, ticker="AAPL", event=E.SUPPLY_CHAIN), nlp(i=3, event=E.EARNINGS, s=0.9)], P, BANDS)
    assert st.upsert_many(sigs) == 3 and st.upsert_many(sigs) == 3 and st.count() == 3
    assert [s.ticker for s in st.query(ticker="AAPL")] == ["AAPL"]
    cut = sorted(x.impact_score for x in sigs)[1]
    hi = st.query(min_impact=cut)
    assert len(hi) == sum(x.impact_score >= cut for x in sigs) and all(x.impact_score >= cut for x in hi)
    top = st.query(order="impact", limit=1)[0]
    assert top.impact_score == max(s.impact_score for s in sigs)
    summ = st.summary()
    assert summ["total"] == 3 and summ["by_source"] == {"news": 3} and summ["top_risky_tickers"]
    assert st.query(limit=1)[0].score_breakdown  # JSON payload round-trips
    st.clear(); assert st.count() == 0


# ---- triggers
def test_stress_trigger_requires_adverse_and_threshold():
    adverse = build_signals([nlp(event=E.CREDIT_EVENT, s=-0.95, name="newsapi:Reuters")], P, BANDS)[0]
    positive = build_signals([nlp(event=E.EARNINGS, s=0.95, name="newsapi:Reuters")], P, BANDS)[0]
    assert adverse.impact_score >= 7 and should_trigger_stress(adverse, 7.0)
    assert not should_trigger_stress(adverse, adverse.impact_score + 0.1)
    assert positive.impact_score > 4 and not should_trigger_stress(positive, 4.0)
    assert trigger_signals([adverse, positive], 7.0) == [adverse]


# ---- engine end-to-end (offline, bundled synthetic sample)
@pytest.fixture
def engine():
    return RiskEngine(Settings(_env_file=None), SignalStore(), LexiconBackend(), EventClassifier(None))


def test_engine_end_to_end_offline(engine):
    sigs, rep = engine.ingest_and_score()
    assert len(sigs) > 20 and engine.store.count() == len(sigs)
    assert all(s.simulated for s in sigs) and {s.source for s in sigs} == {SourceType.NEWS, SourceType.SOCIAL}
    assert all(1 <= s.impact_score <= 10 for s in sigs)
    assert any(should_trigger_stress(s, 7.0) for s in sigs)   # offline demo path has a trigger-level adverse event
    assert {r.mode for r in rep.report} == {"sample"}


def test_engine_is_deterministic(engine):
    a, _ = engine.ingest_and_score()
    b, _ = engine.ingest_and_score()
    assert [(s.id, s.impact_score) for s in a] == [(s.id, s.impact_score) for s in b]


def test_analyze_text_not_persisted_by_default(engine):
    sigs = engine.analyze_text("Apple warns of iPhone production disruption after plant shutdown")
    assert sigs and sigs[0].ticker == "AAPL" and sigs[0].event_type == E.SUPPLY_CHAIN
    assert engine.store.count() == 0
    assert engine.analyze_text("The weather is nice today")  # no relevance gating for ad-hoc analysis
