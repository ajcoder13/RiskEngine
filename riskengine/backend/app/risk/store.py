"""SQLite signal store (stdlib only). Upserts are idempotent on signal id."""
import sqlite3
from datetime import datetime
from pathlib import Path

from app.schemas.signal import RiskSignal

_SCHEMA = """CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY, ticker TEXT, event_type TEXT, source TEXT, timestamp TEXT,
  impact REAL, sentiment REAL, risk_level TEXT, direction TEXT, simulated INTEGER, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_ts ON signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_ticker ON signals(ticker);"""


class SignalStore:
    def __init__(self, path: str | Path = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript(_SCHEMA)

    def upsert_many(self, sigs: list[RiskSignal]) -> int:
        rows = [(s.id, s.ticker, s.event_type.value, s.source.value, s.timestamp.isoformat(), s.impact_score,
                 s.sentiment_score, s.risk_level.value, s.direction.value, int(s.simulated), s.model_dump_json())
                for s in sigs]
        with self.db:
            self.db.executemany("INSERT OR REPLACE INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        return len(rows)

    def query(self, limit: int = 50, ticker: str | None = None, event_type: str | None = None,
              source: str | None = None, min_impact: float | None = None, risk_level: str | None = None,
              since: datetime | None = None, order: str = "time") -> list[RiskSignal]:
        where, args = [], []
        for col, val in (("ticker", ticker), ("event_type", event_type), ("source", source), ("risk_level", risk_level)):
            if val:
                where.append(f"{col}=?"); args.append(val)
        if min_impact is not None:
            where.append("impact>=?"); args.append(min_impact)
        if since:
            where.append("timestamp>=?"); args.append(since.isoformat())
        sql = "SELECT payload FROM signals" + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY impact DESC, timestamp DESC" if order == "impact" else " ORDER BY timestamp DESC, impact DESC"
        rows = self.db.execute(sql + " LIMIT ?", (*args, limit)).fetchall()
        return [RiskSignal.model_validate_json(r[0]) for r in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

    def summary(self) -> dict:
        q = lambda sql: self.db.execute(sql).fetchall()
        return {"total": self.count(),
                "by_risk_level": dict(q("SELECT risk_level, COUNT(*) FROM signals GROUP BY 1")),
                "by_event_type": dict(q("SELECT event_type, COUNT(*) FROM signals GROUP BY 1")),
                "by_source": dict(q("SELECT source, COUNT(*) FROM signals GROUP BY 1")),
                "simulated_share": (q("SELECT AVG(simulated) FROM signals")[0][0] or 0.0),
                "top_risky_tickers": [{"ticker": t, "max_impact": m, "signals": n} for t, m, n in q(
                    "SELECT ticker, MAX(impact), COUNT(*) FROM signals WHERE direction='adverse' AND ticker IS NOT NULL "
                    "GROUP BY ticker ORDER BY MAX(impact) DESC LIMIT 5")]}

    def event_stats(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT event_type, COUNT(*), AVG(impact), MAX(impact), SUM(direction='adverse') "
            "FROM signals GROUP BY event_type ORDER BY COUNT(*) DESC").fetchall()
        return [{"event_type": e, "count": n, "avg_impact": round(a, 2), "max_impact": m, "adverse_count": int(adv)}
                for e, n, a, m, adv in rows]

    def clear(self) -> None:
        with self.db:
            self.db.execute("DELETE FROM signals")
