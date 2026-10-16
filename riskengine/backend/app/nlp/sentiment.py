"""Sentiment backends. FinBERT (finance-specific) is primary; a small lexicon scorer is the offline fallback.
Both output class probabilities, normalised to score = P(pos) - P(neg) in [-1, 1]; confidence = max prob."""
import logging
import math
import re
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger(__name__)
LABELS = ("positive", "negative", "neutral")


@dataclass
class Sentiment:
    score: float
    probs: dict[str, float]
    confidence: float


def from_probs(probs: dict[str, float]) -> Sentiment:
    total = sum(probs.get(k, 0.0) for k in LABELS) or 1.0
    p = {k: probs.get(k, 0.0) / total for k in LABELS}
    return Sentiment(score=max(-1.0, min(1.0, p["positive"] - p["negative"])), probs=p, confidence=max(p.values()))


def label_from_probs(probs: dict[str, float]) -> str:
    return max(LABELS, key=lambda k: probs.get(k, 0.0))


class SentimentBackend(Protocol):
    name: str
    def predict(self, texts: list[str]) -> list[Sentiment]: ...


class FinBERTBackend:
    """ProsusAI/finbert: BERT further pre-trained on financial text and fine-tuned on Financial PhraseBank.
    Chosen over generic sentiment models because finance language is polarity-shifted
    ('liability', 'cut guidance', 'beat estimates')."""
    name = "ProsusAI/finbert"

    def __init__(self, model_id: str = "ProsusAI/finbert", batch_size: int = 16):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer  # lazy: heavy
        import torch
        self._torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id).eval()
        self.id2label = {int(i): l.lower() for i, l in self.model.config.id2label.items()}
        self.batch_size = batch_size

    def predict(self, texts: list[str]) -> list[Sentiment]:
        out: list[Sentiment] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            enc = self.tok(batch, padding=True, truncation=True, max_length=128, return_tensors="pt")
            with self._torch.no_grad():
                probs = self._torch.softmax(self.model(**enc).logits, dim=-1).tolist()
            for row in probs:
                out.append(from_probs({self.id2label[j]: p for j, p in enumerate(row)}))
        return out


_NEG = {"fall": 1, "falls": 1, "fell": 1, "falling": 1, "slide": 1, "slides": 1, "tumble": 1.5, "tumbles": 1.5,
        "plunge": 2, "plunges": 2, "slump": 1.5, "drop": 1, "drops": 1, "decline": 1, "declines": 1, "loss": 1.5,
        "losses": 1.5, "miss": 1.5, "misses": 1.5, "missed": 1.5, "warn": 1.5, "warns": 1.5, "warning": 1.5,
        "probe": 1.5, "investigation": 1, "recall": 1.5, "lawsuit": 1.5, "delay": 1.5, "delays": 1.5, "delayed": 1.5,
        "shortage": 1.5, "shortages": 1.5, "disruption": 1.5, "shuts": 1, "bankruptcy": 3, "default": 2,
        "downgrade": 2, "fraud": 2.5, "cyberattack": 2, "breach": 2, "hacked": 2, "threat": 1.5, "threatens": 1.5,
        "escalation": 1.5, "escalates": 1.5, "sanctions": 1.5, "strike": 1, "defects": 1.5, "deteriorate": 1.5,
        "deteriorating": 1.5, "antitrust": 1, "restrictions": 1, "concerns": 1, "crash": 2, "crashes": 1.5,
        "sell-off": 2, "selloff": 2, "volatility": 1, "risk": 0.7, "cut": 1, "struggle": 1, "weak": 1, "slow": 1,
        "slows": 1, "hit": 1, "hammer": 1.5, "freefall": 2, "dip": 0.7, "tighten": 1, "tightened": 1,
        "massive": 0.5, "chapter": 0.5, "liability": 1}
_POS = {"beat": 1.5, "beats": 1.5, "rise": 1, "rises": 1, "rose": 1, "rally": 1.5, "surge": 1.5, "surges": 1.5,
        "jump": 1, "jumps": 1, "gain": 1, "gains": 1, "growth": 1.2, "strong": 1.2, "approval": 1.5, "approved": 1.5,
        "wins": 1.5, "raises": 1, "record": 1, "profit": 0.8, "upgrade": 1.5, "exceed": 1, "resilient": 1,
        "steady": 0.5, "crushing": 1.5, "unstoppable": 1.5, "huge": 1, "flying": 1.2, "buying": 0.7,
        "unveils": 0.7, "launch": 0.5, "expansion": 1, "outperform": 1.5, "improve": 1, "improves": 1}
_NEGATORS = {"not", "no", "never", "without", "isn't", "wasn't", "doesn't", "didn't", "won't", "hope"}
_TOK = re.compile(r"[a-z][a-z\-']*")


class LexiconBackend:
    """Hand-built finance lexicon with 3-token negation window. Offline FALLBACK only: not trained,
    confidence is NOT calibrated, and it cannot handle context-dependent polarity
    (e.g. 'unemployment claims fall' is good news)."""
    name = "lexicon-fallback"

    def _score(self, text: str) -> float:
        toks = _TOK.findall(text.lower())
        raw = 0.0
        for i, t in enumerate(toks):
            w = _POS.get(t, 0.0) - _NEG.get(t, 0.0)
            if w and any(x in _NEGATORS for x in toks[max(0, i - 3):i]):
                w = -0.8 * w
            raw += w
        return raw

    def predict(self, texts: list[str]) -> list[Sentiment]:
        res = []
        for t in texts:
            raw = self._score(t)
            if raw == 0:
                res.append(from_probs({"positive": 0.2, "negative": 0.2, "neutral": 0.6}))  # no lexical evidence: low confidence
                continue
            s = math.tanh(abs(raw) / 2.0)          # magnitude in (0,1)
            mass = 0.15 + 0.80 * s                 # non-neutral probability mass
            pol = {"positive": 0.0, "negative": 0.0}
            pol["positive" if raw > 0 else "negative"] = mass
            res.append(from_probs({**pol, "neutral": 1.0 - mass}))
        return res


def get_backend(preferred: str = "finbert") -> tuple[SentimentBackend, str]:
    """Returns (backend, info). Never raises: falls back to the lexicon and says so in `info`."""
    if preferred == "finbert":
        try:
            b = FinBERTBackend()
            return b, b.name
        except Exception as e:
            log.warning("FinBERT unavailable (%s); using lexicon fallback", e)
            return LexiconBackend(), f"lexicon-fallback (finbert unavailable: {type(e).__name__})"
    return LexiconBackend(), "lexicon-fallback"
