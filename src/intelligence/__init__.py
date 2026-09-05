"""MVP5 Advanced Enterprise Intelligence package (`ADR-0008`)."""

from src.intelligence.drift import detect_drift
from src.intelligence.rationalization import rationalize_technologies
from src.intelligence.risk import RiskAssessment, compute_risk_score
from src.intelligence.team_rollup import (
    TeamOwnedRiskRollup,
    compute_team_owned_risk_rollup,
    simulate_team_portfolio_impact,
)
from src.intelligence.whatif import WhatIfResult, simulate_retirement

__all__ = [
    "RiskAssessment",
    "TeamOwnedRiskRollup",
    "WhatIfResult",
    "compute_risk_score",
    "compute_team_owned_risk_rollup",
    "detect_drift",
    "rationalize_technologies",
    "simulate_retirement",
    "simulate_team_portfolio_impact",
]
