from __future__ import annotations

import math
from typing import Any

import pandas as pd


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value: object) -> float:
    return safe_float(value) * 100.0


def aggression_label(rate_diff: float) -> str:
    if rate_diff < -0.005:
        return "Too Passive"
    if rate_diff > 0.005:
        return "Too Aggressive"
    return "Balanced"


def value_label(value: float) -> str:
    if value > 2.0:
        return "Positive"
    if value < -2.0:
        return "Negative"
    return "Neutral"


def letter_grade(score: float) -> str:
    if score >= 0.85:
        return "A"
    if score >= 0.72:
        return "B+"
    if score >= 0.60:
        return "B"
    if score >= 0.48:
        return "C"
    return "D"


def archetype(row: pd.Series) -> str:
    aggression = aggression_label(safe_float(row.get("exp_rate_challenges_diff")))
    total = safe_float(row.get("total_vs_expected"))
    success = safe_float(row.get("rate_overturns"))
    if total > 5 and aggression == "Balanced":
        return "Battery Captain"
    if total > 2 and aggression == "Too Passive":
        return "Passive Receiver"
    if total < -2 and aggression == "Too Aggressive":
        return "Gambler"
    if success >= 0.7 and total <= 1:
        return "Traditional Receiver"
    if total >= 0:
        return "Technician"
    return "At-Risk Receiver"


def build_catcher_rows(catcher_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in catcher_df.iterrows():
        challenges = safe_float(row.get("n_challenges"))
        overturns = safe_float(row.get("n_overturns"))
        success_rate = safe_float(row.get("rate_overturns"))
        if challenges and not success_rate:
            success_rate = overturns / challenges
        expected_overturns = challenges * safe_float(row.get("exp_rate_overturns"))
        overturns_above_expected = overturns - expected_overturns
        execution_value = safe_float(row.get("net_for"))
        selection_value = safe_float(row.get("total_vs_expected")) - execution_value
        zone_indicator = 0.0
        total_value = execution_value + selection_value + zone_indicator
        rate_diff = safe_float(row.get("exp_rate_challenges_diff"))
        rows.append(
            {
                "name": str(row.get("entity_name", "Unknown")),
                "team": str(row.get("team_abbr", "Unknown")),
                "level": str(row.get("level", "")),
                "parentOrg": str(row.get("parent_org", "")),
                "challenges": int(challenges),
                "overturns": int(overturns),
                "confirms": int(safe_float(row.get("n_confirms"))),
                "successRate": success_rate,
                "successPct": pct(success_rate),
                "expectedSuccessRate": safe_float(row.get("exp_rate_overturns")),
                "expectedSuccessPct": pct(row.get("exp_rate_overturns")),
                "expectedOverturns": expected_overturns,
                "overturnsAboveExpected": overturns_above_expected,
                "netFor": safe_float(row.get("net_for")),
                "netAgainst": safe_float(row.get("net_against")),
                "totalVsExpected": safe_float(row.get("total_vs_expected")),
                "expectedChallengeDiff": rate_diff,
                "aggressionLabel": aggression_label(rate_diff),
                "valueLabel": value_label(safe_float(row.get("total_vs_expected"))),
                "executionValue": execution_value,
                "selectionValue": selection_value,
                "zoneAdaptation": zone_indicator,
                "overallValue": total_value,
                "archetype": archetype(row),
                "executionGrade": letter_grade(success_rate),
                "selectionGrade": letter_grade(0.65 + max(min(overturns_above_expected / 20.0, 0.2), -0.25)),
                "nStrikeoutsFlip": int(safe_float(row.get("n_strikeouts_flip"))),
                "nWalksFlip": int(safe_float(row.get("n_walks_flip"))),
            }
        )
    return sorted(rows, key=lambda item: item["totalVsExpected"], reverse=True)


def build_zone_rows(statcast_2026: pd.DataFrame, statcast_2025: pd.DataFrame) -> list[dict[str, Any]]:
    frames = [frame for frame in [statcast_2026, statcast_2025] if not frame.empty]
    if not frames:
        return []
    combined = pd.concat(frames, ignore_index=True)
    if combined.empty:
        return []
    grouped = (
        combined.groupby(
            [
                "season",
                "x_bin",
                "z_bin",
                "zone_region",
            ],
            dropna=False,
        )
        .agg(
            called_strikes=("is_called_strike", "sum"),
            taken=("is_taken_pitch", "sum"),
            swinging_strikes=("is_swinging_strike", "sum"),
            pitches=("description", "size"),
        )
        .reset_index()
    )
    grouped["called_strikes"] = grouped["called_strikes"].astype(int)
    grouped["taken"] = grouped["taken"].astype(int)
    grouped["swinging_strikes"] = grouped["swinging_strikes"].astype(int)
    grouped["pitches"] = grouped["pitches"].astype(int)
    return grouped.to_dict(orient="records")


def filters_from_rows(catcher_rows: list[dict[str, Any]], zone_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    teams = sorted({row["team"] for row in catcher_rows if row.get("team")})
    catchers = sorted({row["name"] for row in catcher_rows if row.get("name")})
    return {
        "teams": teams,
        "catchers": catchers,
        "zoneTeams": [],
        "zoneCatchers": [],
        "pitchers": [],
        "pitchTypes": [],
        "sides": [],
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value
