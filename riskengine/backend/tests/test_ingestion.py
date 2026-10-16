import json
from datetime import datetime, timezone

import httpx
import pytest

from app.config import Settings
from app.ingestion import live, loaders
from app.ingestion.cleaning import clean_text, dedupe, make_id
from app.ingestion.service import collect
from app.schemas.document import RawDocument
from app.schemas.signal import SourceType


def _doc(text, src="news"):
    return RawDocument(id=make_id("t", text), source=SourceType(src), source_name="t",
                       timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), text=text)


def test_clean_text():
    assert clean_text("RT @bob: Big news &amp; more https://t.co/x  $AAPL up") == "Big news & more $AAPL up"


def test_dedupe_exact_and_near():
    a = _doc("Tesla faces federal probe over driver assistance crashes and regulators weigh recall")
    b = _doc("tesla faces federal probe over driver assistance crashes and regulators weigh recall!")
    c = _doc("Tesla faces federal probe over driver assistance crashes and regulators weigh a recall")
    d = _doc("Microsoft beats quarterly earnings estimates on strong cloud growth")
    out = dedupe([a, b, c, d])
    assert [x.text for x in out] == [a.text, d.text]


def test_phrasebank_loader(tmp_path):
    p = tmp_path / "all-data.csv"
    p.write_bytes("positive,Profit rose 10% in Q3\nnegative,Sales fell sharply\n".encode("latin-1"))
    docs = loaders.load_phrasebank_csv(p)
    assert [d.label for d in docs] == ["positive", "negative"]
    assert all(d.timestamp_is_ingest_time and not d.simulated for d in docs)


def test_tweets_loader_autodetect(tmp_path):
    p = tmp_path / "tweets.csv"
    p.write_text("Date,Tweet,Sentiment\n2020-01-02 10:00:00,$AAPL looks strong,1\n,no date here,-1\n")
    docs = loaders.load_tweets_csv(p)
    assert docs[0].label == "positive" and not docs[0].timestamp_is_ingest_time
    assert docs[1].label == "negative" and docs[1].timestamp_is_ingest_time


def test_tweets_loader_bad_schema(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        loaders.load_tweets_csv(p)


def test_parse_gdelt_documented_format():
    payload = {"articles": [{"url": "https://e.com/1", "title": "Bank &amp; lender merger announced",
                             "seendate": "20261006T080500Z", "domain": "e.com"}, {"title": ""}]}
    docs = live.parse_gdelt(payload)
    assert len(docs) == 1 and docs[0].text == "Bank & lender merger announced"
    assert docs[0].timestamp == datetime(2026, 10, 6, 8, 5, tzinfo=timezone.utc)


def test_parse_newsapi():
    payload = {"articles": [{"source": {"name": "Wire"}, "title": "Oil jumps", "description": "on supply fears",
                             "publishedAt": "2026-10-06T06:30:00Z", "url": "https://x"}]}
    d = live.parse_newsapi(payload)[0]
    assert d.text == "Oil jumps on supply fears" and d.source_name == "newsapi:Wire"


def test_newsapi_requires_key():
    with pytest.raises(live.IngestionError):
        live.fetch_newsapi(httpx.Client(), "")


def _settings(tmp_path, **kw):
    (tmp_path / "raw").mkdir(exist_ok=True)
    (tmp_path / "sample").mkdir(exist_ok=True)
    from app.config import ROOT
    for f in ("news_sample.jsonl", "tweets_sample.jsonl"):
        (tmp_path / "sample" / f).write_text((ROOT / "data/sample" / f).read_text())
    return Settings(data_dir=tmp_path, _env_file=None, **kw)


def test_fallback_when_live_fails(tmp_path):
    def boom(request):
        raise httpx.ConnectError("blocked")
    client = httpx.Client(transport=httpx.MockTransport(boom))
    res = collect(_settings(tmp_path, use_live_data=True, newsapi_key="k"), client)
    modes = {(s.name, s.mode) for s in res.report}
    assert ("gdelt", "live") in modes and ("news_sample.jsonl", "sample") in modes
    assert next(s for s in res.report if s.name == "gdelt").error
    assert {d.source for d in res.documents} == {SourceType.NEWS, SourceType.SOCIAL}
    assert all(d.simulated for d in res.documents)


def test_live_success_merges_with_fallback(tmp_path):
    body = {"articles": [{"url": "u", "title": "Central bank hikes rates unexpectedly",
                          "seendate": "20261006T080500Z", "domain": "d.com"}]}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    res = collect(_settings(tmp_path, use_live_data=True), client)
    assert any(d.source_name.startswith("gdelt:") and not d.simulated for d in res.documents)
    assert any(d.simulated for d in res.documents)


def test_offline_default_uses_real_local_file_over_sample(tmp_path):
    s = _settings(tmp_path)
    (tmp_path / "raw" / "all-data.csv").write_bytes(b"neutral,Company opens new office\n")
    res = collect(s)
    assert any(r.mode == "local" for r in res.report)
    assert not any(d.simulated for d in res.documents if d.source == SourceType.NEWS)


def test_bundled_sample_loads_and_dedups():
    from app.config import ROOT
    docs = loaders.load_sample_jsonl(ROOT / "data/sample/news_sample.jsonl")
    assert len(docs) == 28 and all(d.simulated for d in docs)
    assert len(dedupe(docs)) == len(docs)


def test_dedupe_keeps_distinct_template_headlines():
    a = _doc("Apple shares fall after supplier warns of production delays at key plant")
    b = _doc("Apple shares rise after supplier confirms production ahead of schedule at key plant")
    c = _doc("Tesla shares fall after regulator warns of safety issues in new vehicles")
    assert len(dedupe([a, b, c])) == 3
