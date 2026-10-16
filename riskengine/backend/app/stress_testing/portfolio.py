"""Synthetic wholesale banking portfolio.

Asset composition: corporate loans, government bonds, corporate bonds, equities, derivatives, cash.
Values are illustrative (~$89.92M total across 20 positions) and clearly labelled as SIMULATED.
All assumptions documented inline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PortfolioPosition:
    asset_id: str
    asset_type: Literal["Corporate Loan", "Government Bond", "Corporate Bond",
                         "Equity", "Derivative", "Cash"]
    name: str
    notional: float
    market_value: float
    sector: str
    geography: str
    credit_rating: str      # AAA, AA, A, BBB, BB, B, CCC, D
    duration: float         # years; 0 for equity / cash
    interest_rate_sensitivity: float  # DV01 proxy: MV change per 1 bp
    equity_exposure: float  # fraction of market_value with equity-like payoff
    counterparty: str
    default_probability: float   # annual PD
    recovery_rate: float         # LGD = 1 - RR
    weight: float = field(default=0.0)  # set after build

    def __post_init__(self):
        # DV01 proxy: duration × market_value × 0.0001
        if self.interest_rate_sensitivity == 0.0 and self.duration > 0:
            self.interest_rate_sensitivity = self.duration * self.market_value * 0.0001


def build_portfolio() -> list[PortfolioPosition]:
    """Construct a ~$100 M synthetic wholesale banking portfolio."""
    positions = [
        # ---- Corporate Loans -----------------------------------------------
        PortfolioPosition("CL001", "Corporate Loan", "TechCorp Senior Secured",
                          10_000_000, 9_800_000, "Technology", "North America",
                          "BBB", 3.5, 0.0, 0.0, "JPMorgan Chase", 0.012, 0.55),
        PortfolioPosition("CL002", "Corporate Loan", "EnergyGlobal Term Loan",
                          8_000_000, 7_750_000, "Energy", "Europe",
                          "BB", 4.0, 0.0, 0.0, "Goldman Sachs", 0.025, 0.45),
        PortfolioPosition("CL003", "Corporate Loan", "RetailChain Revolving Credit",
                          5_000_000, 4_900_000, "Consumer", "North America",
                          "B",  2.0, 0.0, 0.0, "Bank of America", 0.040, 0.35),
        PortfolioPosition("CL004", "Corporate Loan", "PharmaCo Acquisition Facility",
                          6_000_000, 5_950_000, "Healthcare", "North America",
                          "A",  5.0, 0.0, 0.0, "Citigroup", 0.008, 0.60),
        PortfolioPosition("CL005", "Corporate Loan", "IndustrialMfg Project Finance",
                          7_000_000, 6_800_000, "Industrials", "Asia Pacific",
                          "BB", 7.0, 0.0, 0.0, "HSBC", 0.022, 0.42),

        # ---- Government Bonds ----------------------------------------------
        PortfolioPosition("GB001", "Government Bond", "US Treasury 10Y",
                          12_000_000, 11_500_000, "Sovereign", "North America",
                          "AAA", 9.2, 0.0, 0.0, "US Treasury", 0.0001, 0.70),
        PortfolioPosition("GB002", "Government Bond", "German Bund 5Y",
                          8_000_000, 7_850_000, "Sovereign", "Europe",
                          "AAA", 4.8, 0.0, 0.0, "Bundesrepublik", 0.0001, 0.80),
        PortfolioPosition("GB003", "Government Bond", "UK Gilt 7Y",
                          5_000_000, 4_900_000, "Sovereign", "Europe",
                          "AA",  6.5, 0.0, 0.0, "HM Treasury", 0.0003, 0.78),

        # ---- Corporate Bonds -----------------------------------------------
        PortfolioPosition("CB001", "Corporate Bond", "Apple 5Y Senior",
                          4_000_000, 3_950_000, "Technology", "North America",
                          "AA",  4.7, 0.0, 0.0, "Apple Inc", 0.003, 0.65),
        PortfolioPosition("CB002", "Corporate Bond", "ExxonMobil 10Y",
                          3_500_000, 3_380_000, "Energy", "North America",
                          "A",   9.1, 0.0, 0.0, "ExxonMobil", 0.005, 0.60),
        PortfolioPosition("CB003", "Corporate Bond", "Emerging Market Sovereign 5Y",
                          4_000_000, 3_750_000, "Sovereign", "Emerging Markets",
                          "BB",  4.5, 0.0, 0.0, "EM Basket", 0.030, 0.40),
        PortfolioPosition("CB004", "Corporate Bond", "European Financials HY",
                          3_000_000, 2_850_000, "Finance", "Europe",
                          "B",   3.8, 0.0, 0.0, "EU Banks", 0.045, 0.35),

        # ---- Equities ------------------------------------------------------
        PortfolioPosition("EQ001", "Equity", "US Large Cap Tech Basket",
                          5_000_000, 5_200_000, "Technology", "North America",
                          "NR",  0.0, 0.0, 1.0, "Multiple", 0.0, 0.0),
        PortfolioPosition("EQ002", "Equity", "European Financial Equities",
                          3_000_000, 3_050_000, "Finance", "Europe",
                          "NR",  0.0, 0.0, 1.0, "Multiple", 0.0, 0.0),
        PortfolioPosition("EQ003", "Equity", "Emerging Market Equities",
                          2_500_000, 2_400_000, "Diversified", "Emerging Markets",
                          "NR",  0.0, 0.0, 1.0, "Multiple", 0.0, 0.0),
        PortfolioPosition("EQ004", "Equity", "Energy Sector ETF",
                          2_000_000, 2_100_000, "Energy", "Global",
                          "NR",  0.0, 0.0, 1.0, "Multiple", 0.0, 0.0),

        # ---- Derivatives ---------------------------------------------------
        PortfolioPosition("DV001", "Derivative", "S&P 500 Put Protection",
                          3_000_000, 850_000, "Diversified", "North America",
                          "NR",  0.0, 0.0, -0.30, "Goldman Sachs", 0.0, 0.0),  # negative equity exposure = hedge
        PortfolioPosition("DV002", "Derivative", "EUR/USD Forward",
                          2_000_000, 120_000, "FX", "Europe",
                          "NR",  0.0, 0.0, 0.0, "Deutsche Bank", 0.0, 0.0),
        PortfolioPosition("DV003", "Derivative", "Interest Rate Swap (Pay Fixed)",
                          5_000_000, -180_000, "Rates", "North America",
                          "NR",  7.5, 0.0, 0.0, "JPMorgan Chase", 0.0, 0.0),

        # ---- Cash ----------------------------------------------------------
        PortfolioPosition("CA001", "Cash", "USD Money Market",
                          3_000_000, 3_000_000, "Cash", "North America",
                          "AAA", 0.0, 0.0, 0.0, "Internal", 0.0, 1.0),
    ]

    total_mv = sum(abs(p.market_value) for p in positions)
    for p in positions:
        p.weight = round(p.market_value / total_mv, 6)
    return positions


PORTFOLIO: list[PortfolioPosition] = build_portfolio()
TOTAL_VALUE: float = sum(p.market_value for p in PORTFOLIO)
