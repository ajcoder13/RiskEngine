"""Text normalisation and de-duplication (exact + near-duplicate)."""
import hashlib
import html
import re
from collections import defaultdict

from app.schemas.document import RawDocument

_URL = re.compile(r"https?://\S+|www\.\S+")
_RT = re.compile(r"^\s*RT\s+@\w+:?\s*", re.I)
_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9$]+")


def clean_text(text: str) -> str:
    """Unescape HTML, drop URLs and retweet prefixes, collapse whitespace. Cashtags ($AAPL) are kept."""
    t = html.unescape(text or "")
    t = _RT.sub("", t)
    t = _URL.sub("", t)
    return _WS.sub(" ", t).strip()


def normalise_key(text: str) -> str:
    return " ".join(_TOKEN.findall(text.lower()))


def make_id(source_name: str, text: str) -> str:
    return hashlib.sha1(f"{source_name}|{normalise_key(text)}".encode()).hexdigest()[:16]


def _shingles(key: str, n: int = 3) -> set[str]:
    toks = key.split()
    if len(toks) <= n:
        return {key}
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def dedupe(docs: list[RawDocument], threshold: float = 0.7) -> list[RawDocument]:
    """Drop exact duplicates, then near-duplicates (word-3gram Jaccard >= threshold; default 0.7, tunable).
    Earlier documents win. Uses an inverted shingle index so it scales past O(n^2) on real corpora."""
    kept: list[RawDocument] = []
    kept_sh: list[set[str]] = []
    index: dict[str, list[int]] = defaultdict(list)
    seen_keys: set[str] = set()
    for d in docs:
        key = normalise_key(d.text)
        if not key or key in seen_keys:
            continue
        sh = _shingles(key)
        cands = {i for s in sh for i in index.get(s, ())}
        if any(jaccard(sh, kept_sh[i]) >= threshold for i in cands):
            continue
        seen_keys.add(key)
        idx = len(kept)
        kept.append(d)
        kept_sh.append(sh)
        for s in sh:
            index[s].append(idx)
    return kept
