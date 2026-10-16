from datetime import datetime, timezone

import pytest

from app.evaluation.metrics import event_report, sentiment_report
from app.nlp import entities as ent
from app.nlp.events import EventClassifier, rule_scores
from app.nlp.pipeline import analyze
from app.nlp.sentiment import LexiconBackend, from_probs, get_backend, label_from_probs
from app.schemas.document import RawDocument
from app.schemas.signal import EventType as E, SourceType


# ---- sentiment normalisation
def test_from_probs_normalises_and_scores():
    s = from_probs({"positive": 0.7, "negative": 0.1, "neutral": 0.2})
    assert s.score == pytest.approx(0.6) and s.confidence == pytest.approx(0.7)
    assert -1 <= from_probs({"positive": 0, "negative": 1, "neutral": 0}).score == -1.0


def test_from_probs_renormalises_unnormalised_input():
    s = from_probs({"positive": 2, "negative": 1, "neutral": 1})
    assert sum(s.probs.values()) == pytest.approx(1.0) and s.score == pytest.approx(0.25)


def test_label_from_probs():
    assert label_from_probs({"positive": .1, "negative": .6, "neutral": .3}) == "negative"


def test_lexicon_direction_and_negation():
    lb = LexiconBackend()
    pos, neg, neu, negated = lb.predict(["Company beats estimates and shares surge on strong growth",
                                         "Firm warns of losses after fraud probe",
                                         "The company will hold its annual meeting on Tuesday",
                                         "Earnings did not beat expectations"])
    assert pos.score > 0.3 and neg.score < -0.3 and abs(neu.score) < 0.1
    assert negated.score < 0


def test_backend_falls_back_when_finbert_unavailable():
    b, info = get_backend("finbert")  # transformers is not installed in CI/sandbox
    assert b.predict(["x"]) and ("lexicon" in info)


# ---- entities / tickers
def test_company_to_ticker():
    assert ent.extract("Apple and Microsoft beat estimates").tickers == ["AAPL", "MSFT"]


def test_cashtag_and_alias_dedup():
    assert ent.extract("$TSLA recall; Tesla shares slide").tickers == ["TSLA"]


@pytest.mark.parametrize("text", ["Apple juice sales rose in Europe", "Metadata leak at a startup",
                                  "The BA flight was delayed", "Amazon rainforest fires worsen",
                                  "apple pie recipes trending", "nothing here"])
def test_no_false_tickers(text):
    assert ent.extract(text).tickers == []


def test_ampersand_names_and_unknown_cashtag():
    assert ent.extract("Johnson & Johnson hit with lawsuit").tickers == ["JNJ"]
    assert ent.extract("$ZZZZ is pumping").tickers == []


def test_country_sector_person():
    e = ent.extract("Fed chair Jerome Powell said; China tightens chip export rules, hitting NVIDIA")
    assert "China" in e.countries and "Technology" in e.sectors and e.tickers == ["NVDA"]
    assert "Jerome Powell" in e.people


# ---- event classification (rules path)
@pytest.mark.parametrize("text,expected", [
    ("Microsoft discloses cyberattack on internal systems", E.CYBERSECURITY),
    ("Major retailer files for Chapter 11 bankruptcy protection", E.CREDIT_EVENT),
    ("Amazon to acquire logistics software firm in $4.5 billion all-cash deal", E.MNA),
    ("Microsoft beats quarterly earnings estimates on strong cloud growth", E.EARNINGS),
    ("Apple unveils new MacBook lineup with faster chips", E.PRODUCT_LAUNCH),
    ("Tesla faces federal probe, regulators weigh mandatory recall", E.REGULATORY),
    ("Johnson & Johnson hit with new product-liability lawsuit", E.LEGAL),
    ("Pfizer faces supply disruption at key manufacturing site", E.SUPPLY_CHAIN),
    ("Goldman Sachs names new head of investment banking following executive departure", E.MANAGEMENT_CHANGE),
    ("Global equities tumble in broad sell-off as volatility index spikes", E.MARKET_SHOCK),
    ("Exxon Mobil and Chevron rally as crude oil surges on supply fears", E.COMMODITY_SHOCK),
    ("Military escalation in the Middle East threatens shipping lanes; crude oil jumps 7%", E.GEOPOLITICAL),
    ("Central bank signals further interest rate hikes as inflation stays above target", E.MACROECONOMIC),
])
def test_event_rules(text, expected):
    r = EventClassifier(None).classify(text)
    assert r.event_type == expected and r.method == "rules" and 0 < r.confidence <= 0.95


def test_event_other_when_nothing_matches():
    r = EventClassifier(None).classify("The cat sat on the mat")
    assert r.event_type == E.OTHER and r.method == "none" and r.confidence <= 0.3


def test_event_confidence_lower_when_ambiguous():
    clear = EventClassifier(None).classify("Company files for bankruptcy")
    mixed = EventClassifier(None).classify("Company files for bankruptcy after lawsuit")
    assert mixed.confidence < clear.confidence


def test_hybrid_blends_zero_shot():
    class FakeZS:
        def probs(self, text):
            return {e: (0.9 if e == E.LEGAL else 0.1 / 13) for e in E}
    r = EventClassifier(FakeZS()).classify("Company hit with lawsuit")
    assert r.event_type == E.LEGAL and r.method == "hybrid"
    assert sum(rule_scores("lawsuit").values()) > 0


# ---- pipeline
def _doc(text):
    return RawDocument(id=text[:8], source=SourceType.NEWS, source_name="t",
                       timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), text=text, simulated=True)


def test_pipeline_fans_out_per_company_and_keeps_simulated_flag():
    res = analyze([_doc("Exxon Mobil and Chevron rally as crude oil surges"), _doc("Rates rise again")],
                  LexiconBackend(), EventClassifier(None), "lexicon")
    assert [r.ticker for r in res] == ["XOM", "CVX", None]
    assert all(r.simulated for r in res) and res[0].sentiment_score > 0
    assert -1 <= res[2].sentiment_score <= 1


def test_pipeline_empty():
    assert analyze([], LexiconBackend(), EventClassifier(None)) == []


# ---- metrics
def test_sentiment_report_perfect_and_imperfect():
    r = sentiment_report(["positive", "negative", "neutral"], ["positive", "negative", "neutral"])
    assert r["accuracy"] == 1.0 and r["macro_f1"] == 1.0
    r2 = sentiment_report(["positive", "negative"], ["positive", "positive"])
    assert r2["accuracy"] == 0.5 and r2["per_class"]["negative"]["recall"] == 0.0


def test_event_report_confusion_shape():
    r = event_report(["Legal", "Earnings", "Legal"], ["Legal", "Legal", "Legal"])
    assert len(r["confusion_matrix"]) == len(r["labels"]) == 2 and r["accuracy"] == pytest.approx(2 / 3)


# ---- regressions found by inspecting sample output
@pytest.mark.parametrize("text,expected", [
    ("Tesla shares slide as safety regulator escalates investigation into Autopilot", E.REGULATORY),
    ("Oil spiking on Middle East headlines, energy names flying", E.GEOPOLITICAL),
    ("$JPM provisioning up, credit cycle might be turning", E.CREDIT_EVENT),
    ("$BA delays again... this company can't catch a break", E.SUPPLY_CHAIN),
])
def test_event_regressions(text, expected):
    assert EventClassifier(None).classify(text).event_type == expected


def test_lexicon_no_evidence_is_low_confidence():
    s = LexiconBackend().predict(["Company will hold its annual meeting"])[0]
    assert s.confidence <= 0.6 and abs(s.score) < 1e-9
