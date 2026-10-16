"""Hybrid event classifier: weighted high-precision rules + optional zero-shot NLI model.
- Rules alone (offline fallback): keyword-pattern scores -> normalised distribution. This IS keyword matching
  and is labelled method='rules'.
- With transformers installed: zero-shot (facebook/bart-large-mnli) probabilities are blended 50/50 with the
  rule distribution (method='hybrid'). If no rule fires, the zero-shot output is used alone.
No supervised event model is trained: no labelled event data exists. Accuracy must be measured on a hand-labelled sheet."""
import logging
import re
from dataclasses import dataclass

from app.schemas.signal import EventType as E

log = logging.getLogger(__name__)

_R = lambda p: re.compile(p, re.I)
RULES: dict[E, list[tuple[re.Pattern, float]]] = {
    E.CYBERSECURITY: [(_R(r"ransomware|cyber-?attack|data breach|hack(?:ed|ers?)\b|breach(?:ed)? of"), 3.0)],
    E.CREDIT_EVENT: [(_R(r"bankruptcy|chapter 11|insolven|\bdefault(?:s|ed)?\b|downgrad|loan-?loss|credit (?:rating|quality|conditions|cycle)|provisioning|debt restructur"), 3.0)],
    E.MNA: [(_R(r"\bacquir\w*|acquisition|merger|takeover|buyout|to buy\b"), 3.0)],
    E.EARNINGS: [(_R(r"\bearnings\b|quarterly (?:profit|results|revenue)|\bguidance\b|same-store sales|trading revenue|profit expectations"), 2.5),
                 (_R(r"\b(?:beats?|misses?|exceed\w*|tops?)\b[^.]{0,25}\b(?:estimates|expectations|forecasts)"), 3.0)],
    E.PRODUCT_LAUNCH: [(_R(r"\bunveil\w*|\blaunch\w*|announces? (?:a )?new|introduces|rolls? out|\bnew (?:gpu|chip|iphone|model|product)\w* announcement|announcement"), 2.5)],
    E.REGULATORY: [(_R(r"regulator\w*|\bprobe\b|investigation|\brecall\b|antitrust|\bapproval\b|export (?:restrictions|curbs|controls)|\bfine[ds]?\b"), 3.0)],
    E.LEGAL: [(_R(r"lawsuit|\bsues?\b|\bsued\b|litigation|class action|settlement|\bcourt\b"), 3.0)],
    E.SUPPLY_CHAIN: [(_R(r"supply (?:shortage|disruption|chain|constraint)|production (?:disruption|delay)|plant shuts?|shuts down|delivery (?:schedule|delay)|manufacturing defects?|shortages?"), 3.0),
                     (_R(r"\bdelays?\b|\bdelayed\b"), 1.5),
                     (_R(r"\bstrike\b"), 1.5)],
    E.MANAGEMENT_CHANGE: [(_R(r"names? (?:a )?new (?:ceo|head|chief|chair)|steps? down|resign\w*|executive departure|appoints?"), 3.0)],
    E.MARKET_SHOCK: [(_R(r"sell-?off|tumbl\w+|plunge\w*|volatility index|\bvix\b|freefall|market crash|circuit breaker"), 3.0)],
    E.COMMODITY_SHOCK: [(_R(r"\bcrude\b|oil (?:price\w*|jumps?|surges?|spik\w+)|natural gas|gold price|commodit\w+|\bwheat\b"), 2.0)],
    E.GEOPOLITICAL: [(_R(r"military|\bwar\b|sanctions?|conflict|military escalat\w+|escalat\w+ (?:in|of) (?:tensions|the conflict|hostilities)|tensions escalat\w+|invasion|missile|embargo|geopolitic\w+|shipping lanes|ceasefire|middle east"), 3.0)],
    E.MACROECONOMIC: [(_R(r"interest rates?|rate hikes?|inflation|central bank|unemployment|\bgdp\b|bond yields?|recession|jobs report|\bcpi\b"), 3.0)],
}

ZS_LABELS: dict[E, str] = {
    E.GEOPOLITICAL: "geopolitical conflict, war, or sanctions", E.MACROECONOMIC: "macroeconomic data or central bank policy",
    E.CREDIT_EVENT: "credit event, bankruptcy, or debt default", E.MNA: "merger or acquisition",
    E.EARNINGS: "corporate earnings results or guidance", E.PRODUCT_LAUNCH: "new product launch",
    E.REGULATORY: "regulatory action or government investigation", E.LEGAL: "lawsuit or legal dispute",
    E.SUPPLY_CHAIN: "supply chain or production disruption", E.MANAGEMENT_CHANGE: "executive or management change",
    E.CYBERSECURITY: "cyberattack or data breach", E.MARKET_SHOCK: "broad stock market sell-off or volatility spike",
    E.COMMODITY_SHOCK: "commodity price shock", E.OTHER: "other general business news",
}


@dataclass
class EventResult:
    event_type: E
    confidence: float
    method: str                    # rules | hybrid | zero-shot | none
    scores: dict[str, float]       # top-3 distribution


def rule_scores(text: str) -> dict[E, float]:
    out: dict[E, float] = {}
    for ev, pats in RULES.items():
        s = sum(w for p, w in pats if p.search(text))
        if s:
            out[ev] = s
    return out


class ZeroShot:
    def __init__(self, model: str = "facebook/bart-large-mnli"):
        from transformers import pipeline  # lazy
        self.pipe = pipeline("zero-shot-classification", model=model)
        self.labels = list(ZS_LABELS.values())
        self.rev = {v: k for k, v in ZS_LABELS.items()}

    def probs(self, text: str) -> dict[E, float]:
        r = self.pipe(text, self.labels, hypothesis_template="This news is about {}.", multi_label=False)
        return {self.rev[l]: s for l, s in zip(r["labels"], r["scores"])}


class EventClassifier:
    def __init__(self, zero_shot: ZeroShot | None = None):
        self.zs = zero_shot

    @classmethod
    def auto(cls) -> "EventClassifier":
        try:
            return cls(ZeroShot())
        except Exception as e:
            log.warning("Zero-shot unavailable (%s); using rules only", type(e).__name__)
            return cls(None)

    def classify(self, text: str) -> EventResult:
        rs = rule_scores(text)
        rule_dist = {k: v / sum(rs.values()) for k, v in rs.items()} if rs else {}
        zs = self.zs.probs(text) if self.zs else {}
        if rule_dist and zs:
            dist, method = {e: 0.5 * rule_dist.get(e, 0) + 0.5 * zs.get(e, 0) for e in E}, "hybrid"
        elif zs:
            dist, method = zs, "zero-shot"
        elif rule_dist:
            top = sorted(rs.values(), reverse=True)
            # confidence shrinks when a second event also fires; capped: rules are not calibrated
            conf = min(0.95, top[0] / (top[0] + (top[1] if len(top) > 1 else 0) + 1.0))
            ev = max(rs, key=rs.get)
            rest = {k: (1 - conf) * v / (sum(rs.values()) - rs[ev] or 1) for k, v in rs.items() if k != ev}
            dist, method = {ev: conf, **rest}, "rules"
        else:
            return EventResult(E.OTHER, 0.30, "none", {E.OTHER.value: 0.30})
        ranked = sorted(dist.items(), key=lambda kv: -kv[1])
        return EventResult(ranked[0][0], round(ranked[0][1], 4), method,
                           {k.value: round(v, 4) for k, v in ranked[:3]})
