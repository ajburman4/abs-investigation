from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
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
        return "Light"
    if rate_diff > 0.005:
        return "Heavy"
    return "Average"


def value_label(value: float) -> str:
    if value > 2.0:
        return "Positive"
    if value < -2.0:
        return "Negative"
    return "Neutral"


def _normalize_name(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    return re.sub(r"\s+", " ", text)


def letter_grade(score: float) -> str:
    if score >= 0.85:
        return "A"
    if score >= 0.70:
        return "B"
    if score >= 0.55:
        return "C"
    if score >= 0.40:
        return "D"
    return "F"


def archetype_from_values(total: float, success: float, aggression: str) -> str:
    if total > 5 and aggression == "Average":
        return "Battery Captain"
    if total > 2 and aggression in {"Light", "Very Light"}:
        return "Passive Receiver"
    if total < -2 and aggression in {"Heavy", "Very Heavy"}:
        return "Gambler"
    if total < -2:
        return "At-Risk Receiver"
    if success >= 0.7 and total <= 1:
        return "Traditional Receiver"
    if total >= 0:
        return "Technician"
    return "At-Risk Receiver"


def archetype(row: pd.Series) -> str:
    aggression = aggression_label(safe_float(row.get("exp_rate_challenges_diff")))
    total = safe_float(row.get("net_for"))
    success = safe_float(row.get("rate_overturns"))
    return archetype_from_values(total, success, aggression)


def _grade_thresholds(
    rows: list[dict[str, Any]],
    key: str,
    *,
    higher_is_better: bool = True,
    min_challenges: int = 5,
    min_sample_key: str = "challenges",
    source: str = "League catchers with 5+ challenges",
) -> dict[str, Any]:
    values = [
        safe_float(row.get(key), math.nan)
        for row in rows
        if safe_float(row.get(min_sample_key)) >= min_challenges
        and not math.isnan(safe_float(row.get(key), math.nan))
    ]
    if len(values) < 5:
        values = [
            safe_float(row.get(key), math.nan)
            for row in rows
            if not math.isnan(safe_float(row.get(key), math.nan))
        ]
    if not values:
        return {
            "higherIsBetter": higher_is_better,
            "source": source,
            "A": 0.9 if higher_is_better else 0.1,
            "B": 0.75 if higher_is_better else 0.25,
            "D": 0.25 if higher_is_better else 0.75,
            "F": 0.1 if higher_is_better else 0.9,
        }
    series = pd.Series(values, dtype="float64")
    if higher_is_better:
        cuts = series.quantile([0.9, 0.75, 0.25, 0.1]).to_dict()
        return {
            "higherIsBetter": True,
            "source": source,
            "A": float(cuts[0.9]),
            "B": float(cuts[0.75]),
            "D": float(cuts[0.25]),
            "F": float(cuts[0.1]),
        }
    cuts = series.quantile([0.1, 0.25, 0.75, 0.9]).to_dict()
    return {
        "higherIsBetter": False,
        "source": source,
        "A": float(cuts[0.1]),
        "B": float(cuts[0.25]),
        "D": float(cuts[0.75]),
        "F": float(cuts[0.9]),
    }


def _grade_from_thresholds(value: float, thresholds: dict[str, Any]) -> str:
    if thresholds.get("higherIsBetter", True):
        if value >= safe_float(thresholds.get("A")):
            return "A"
        if value >= safe_float(thresholds.get("B")):
            return "B"
        if value >= safe_float(thresholds.get("D")):
            return "C"
        if value >= safe_float(thresholds.get("F")):
            return "D"
        return "F"
    if value <= safe_float(thresholds.get("A")):
        return "A"
    if value <= safe_float(thresholds.get("B")):
        return "B"
    if value <= safe_float(thresholds.get("D")):
        return "C"
    if value <= safe_float(thresholds.get("F")):
        return "D"
    return "F"


def _percentile_rank(value: float, values: list[float]) -> float:
    valid = [item for item in values if not math.isnan(item)]
    if not valid:
        return 0.5
    lower = sum(1 for item in valid if item < value)
    equal = sum(1 for item in valid if item == value)
    return (lower + 0.5 * equal) / len(valid)


def _usage_thresholds(rows: list[dict[str, Any]], min_challenges: int = 5) -> dict[str, Any]:
    values = [
        safe_float(row.get("expectedChallengeDiff"), math.nan)
        for row in rows
        if safe_float(row.get("challenges")) >= min_challenges
        and not math.isnan(safe_float(row.get("expectedChallengeDiff"), math.nan))
    ]
    if len(values) < 5:
        values = [
            safe_float(row.get("expectedChallengeDiff"), math.nan)
            for row in rows
            if not math.isnan(safe_float(row.get("expectedChallengeDiff"), math.nan))
        ]
    if not values:
        return {
            "light": 0.25,
            "heavy": 0.75,
            "veryLightMax": -0.02,
            "lightMax": -0.01,
            "heavyMin": 0.01,
            "veryHeavyMin": 0.02,
            "source": "Fallback usage percentile band",
            "values": [],
        }
    series = pd.Series(values, dtype="float64")
    cutoffs = series.quantile([0.10, 0.25, 0.75, 0.90]).to_dict()
    return {
        "light": 0.25,
        "heavy": 0.75,
        "veryLightMax": float(cutoffs.get(0.10, -0.02)),
        "lightMax": float(cutoffs.get(0.25, -0.01)),
        "heavyMin": float(cutoffs.get(0.75, 0.01)),
        "veryHeavyMin": float(cutoffs.get(0.90, 0.02)),
        "source": "League usage percentile by expected challenge-rate difference, 5+ challenge catchers",
        "values": [float(value) for value in values],
    }


def _usage_percentile(rate_diff: float, thresholds: dict[str, Any]) -> float:
    return _percentile_rank(rate_diff, thresholds.get("values", []))


def _usage_label_from_percentile(percentile: float) -> str:
    if percentile < 0.10:
        return "Very Light"
    if percentile < 0.25:
        return "Light"
    if percentile <= 0.75:
        return "Average"
    if percentile <= 0.90:
        return "Heavy"
    return "Very Heavy"


def build_catcher_rows(catcher_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in catcher_df.iterrows():
        challenges = safe_float(row.get("n_challenges"))
        overturns = safe_float(row.get("n_overturns"))
        success_rate = safe_float(row.get("rate_overturns"))
        if challenges and not success_rate:
            success_rate = overturns / challenges
        expected_overturns = safe_float(row.get("exp_chal_gained"))
        overturns_above_expected = overturns - expected_overturns
        challenge_value_for = safe_float(row.get("net_for"))
        savant_net_vs_expected = safe_float(row.get("total_vs_expected"))
        opponent_challenge_value = safe_float(row.get("net_against"))
        execution_value = challenge_value_for
        selection_value = challenge_value_for
        zone_indicator = 0.0
        total_value = selection_value + zone_indicator
        rate_diff = safe_float(row.get("exp_rate_challenges_diff"))
        expected_challenge_rate = safe_float(row.get("exp_rate_challenges"))
        actual_challenge_rate = expected_challenge_rate + rate_diff
        expected_success_rate = safe_float(row.get("exp_rate_overturns"))
        selection_reasonable_rate = safe_float(row.get("perc_chal_rsn"))
        selection_taken_rate = safe_float(row.get("perc_rsn_taken"))
        rows.append(
            {
                "name": str(row.get("entity_name", "Unknown")),
                "normalizedName": _normalize_name(row.get("entity_name", "Unknown")),
                "team": str(row.get("team_abbr", "Unknown")),
                "level": str(row.get("level", "")),
                "parentOrg": str(row.get("parent_org", "")),
                "challenges": int(challenges),
                "overturns": int(overturns),
                "confirms": int(safe_float(row.get("n_confirms"))),
                "successRate": success_rate,
                "successPct": pct(success_rate),
                "expectedSuccessRate": expected_success_rate,
                "expectedSuccessPct": pct(row.get("exp_rate_overturns")),
                "successRateAboveExpected": success_rate - expected_success_rate,
                "expectedOverturns": expected_overturns,
                "overturnsAboveExpected": overturns_above_expected,
                "expectedChallenges": safe_float(row.get("exp_chal")),
                "expectedConfirms": safe_float(row.get("exp_chal_lost")),
                "confirmsAboveExpected": safe_float(row.get("n_confirms")) - safe_float(row.get("exp_chal_lost")),
                "expectedChallengeRate": expected_challenge_rate,
                "actualChallengeRate": actual_challenge_rate,
                "netFor": challenge_value_for,
                "netAgainst": opponent_challenge_value,
                "savantNetVsExpected": savant_net_vs_expected,
                "totalVsExpected": challenge_value_for,
                "challengeValueFor": challenge_value_for,
                "opponentChallengeValue": opponent_challenge_value,
                "expectedChallengeDiff": rate_diff,
                "aggressionLabel": aggression_label(rate_diff),
                "valueLabel": value_label(challenge_value_for),
                "executionValue": execution_value,
                "selectionValue": selection_value,
                "selectionReasonableRate": selection_reasonable_rate,
                "selectionTakenRate": selection_taken_rate,
                "reasonableOpportunities": int(safe_float(row.get("rsn_opp"))),
                "reasonableChallenges": int(safe_float(row.get("rsn_chal"))),
                "forValue": execution_value,
                "againstValue": opponent_challenge_value,
                "zoneAdaptation": zone_indicator,
                "overallValue": total_value,
                "archetype": archetype(row),
                "executionGrade": letter_grade(success_rate),
                "selectionGrade": letter_grade(0.65 + max(min(selection_value / 20.0, 0.2), -0.25)),
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


def _count_order(count: str) -> int:
    try:
        balls, strikes = count.split("-")
        return int(balls) * 10 + int(strikes)
    except (AttributeError, ValueError):
        return 99


def _base_state(row: pd.Series) -> str:
    occupied = [
        "1" if pd.notna(row.get("on_1b")) else "",
        "2" if pd.notna(row.get("on_2b")) else "",
        "3" if pd.notna(row.get("on_3b")) else "",
    ]
    state = "".join(occupied)
    return state if state else "Empty"


def _inning_bucket(inning: object) -> str:
    value = safe_float(inning)
    if value <= 3:
        return "Early"
    if value <= 6:
        return "Middle"
    return "Late"


def _score_bucket(row: pd.Series) -> str:
    margin = abs(safe_float(row.get("fld_score")) - safe_float(row.get("bat_score")))
    if margin <= 1:
        return "Tie / 1 run"
    if margin <= 3:
        return "2-3 runs"
    return "4+ runs"


def _challenge_band(run_value: float, confidence: float) -> str:
    if run_value >= 0.30 or confidence <= 0.40:
        return "Green"
    if run_value >= 0.13 or confidence <= 0.62:
        return "Yellow"
    return "Red"


def _combined_band(run_value: float, success_rate: float | None = None) -> str:
    if success_rate is None:
        return _challenge_band(run_value, _confidence_required(run_value))
    if run_value >= 0.18 and success_rate >= 0.60:
        return "Green"
    if run_value >= 0.13 and success_rate >= 0.45:
        return "Yellow"
    return "Red"


def _confidence_required(run_value: float, challenge_cost: float = 0.20) -> float:
    if run_value <= 0:
        return 1.0
    return challenge_cost / (challenge_cost + run_value)


def _recommendation_from_cost(run_value: float, challenge_cost: float) -> tuple[float, str]:
    confidence = _confidence_required(run_value, challenge_cost)
    if confidence <= 0.45:
        return confidence, "Challenge"
    if confidence <= 0.62:
        return confidence, "Lean"
    return confidence, "Hold"


def _called_pitch_frame(statcast_2026: pd.DataFrame) -> pd.DataFrame:
    if statcast_2026.empty:
        return pd.DataFrame()
    needed = {"description", "delta_run_exp", "balls", "strikes"}
    if not needed.issubset(statcast_2026.columns):
        return pd.DataFrame()
    called = statcast_2026[
        statcast_2026["description"].isin(["ball", "blocked_ball", "called_strike"])
    ].copy()
    called["delta_run_exp"] = pd.to_numeric(called["delta_run_exp"], errors="coerce")
    called = called.dropna(subset=["delta_run_exp"])
    called["count"] = called["balls"].astype(int).astype(str) + "-" + called["strikes"].astype(int).astype(str)
    called["is_called_ball"] = called["description"].isin(["ball", "blocked_ball"])
    called["is_called_strike"] = called["description"].eq("called_strike")
    return called


def _count_run_values(called: pd.DataFrame) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    if called.empty:
        return values
    for count, group in called.groupby("count"):
        balls = group[group["is_called_ball"]]["delta_run_exp"]
        strikes = group[group["is_called_strike"]]["delta_run_exp"]
        if len(balls) < 50 or len(strikes) < 50:
            continue
        run_value = max(0.0, float(balls.mean() - strikes.mean()))
        confidence = _confidence_required(run_value)
        values[count] = {
            "count": count,
            "calledPitches": int(len(group)),
            "calledBalls": int(len(balls)),
            "calledStrikes": int(len(strikes)),
            "ballRunValue": float(balls.mean()),
            "strikeRunValue": float(strikes.mean()),
            "runValue": run_value,
            "confidenceRequired": confidence,
            "band": _challenge_band(run_value, confidence),
        }
    return values


def _run_value_summary(group: pd.DataFrame, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    balls = group[group["is_called_ball"]]["delta_run_exp"]
    strikes = group[group["is_called_strike"]]["delta_run_exp"]
    enough = len(group) >= 80 and len(balls) >= 20 and len(strikes) >= 20
    if enough:
        ball_value = float(balls.mean())
        strike_value = float(strikes.mean())
        run_value = max(0.0, ball_value - strike_value)
    else:
        ball_value = safe_float((fallback or {}).get("ballRunValue"))
        strike_value = safe_float((fallback or {}).get("strikeRunValue"))
        run_value = safe_float((fallback or {}).get("runValue"))
    return {
        "calledPitches": int(len(group)),
        "calledBalls": int(len(balls)),
        "calledStrikes": int(len(strikes)),
        "ballRunValue": ball_value,
        "strikeRunValue": strike_value,
        "runValue": run_value,
        "fallbackUsed": not enough,
    }


def _add_challenge_inventory(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty or "challenge_team_id" not in events.columns:
        events["challengesLeft"] = np.nan
        return events
    ordered = events.sort_values(
        ["game_pk", "challenge_team_id", "at_bat_number", "event_index", "pitch_number"],
        na_position="last",
    ).copy()
    ordered["challengesLeft"] = np.nan
    for _, group in ordered.groupby(["game_pk", "challenge_team_id"], dropna=False):
        misses = 0
        for index, row in group.iterrows():
            left = max(0, 2 - misses)
            ordered.at[index, "challengesLeft"] = left
            if not bool(row.get("abs_overturned")):
                misses += 1
    return ordered.sort_index()


def _inventory_costs(statcast_2026: pd.DataFrame, abs_challenges: pd.DataFrame, count_values: dict[str, dict[str, Any]]) -> dict[str, Any]:
    base_cost = 0.20
    if statcast_2026.empty or abs_challenges.empty or not count_values:
        return {
            "1": {"cost": 0.28, "premium": 0.08, "sample": 0, "source": "fallback"},
            "2": {"cost": base_cost, "premium": 0.0, "sample": 0, "source": "Savant breakeven cost"},
        }
    events = _add_challenge_inventory(abs_challenges.copy())
    for column in ["game_pk", "at_bat_number", "pitch_number"]:
        events[column] = pd.to_numeric(events[column], errors="coerce")
    pitches = statcast_2026.copy()
    for column in ["game_pk", "at_bat_number", "pitch_number"]:
        pitches[column] = pd.to_numeric(pitches[column], errors="coerce")
    joined = events.merge(
        pitches[["game_pk", "at_bat_number", "pitch_number", "balls", "strikes"]],
        on=["game_pk", "at_bat_number", "pitch_number"],
        how="left",
    )
    joined = joined.dropna(subset=["balls", "strikes", "challenge_team_id"])
    if joined.empty:
        return {
            "1": {"cost": 0.28, "premium": 0.08, "sample": 0, "source": "fallback"},
            "2": {"cost": base_cost, "premium": 0.0, "sample": 0, "source": "Savant breakeven cost"},
        }
    joined["count"] = joined["balls"].astype(int).astype(str) + "-" + joined["strikes"].astype(int).astype(str)
    joined["runValue"] = joined["count"].map({count: item["runValue"] for count, item in count_values.items()})
    joined = joined.dropna(subset=["runValue"])
    future_values: list[float] = []
    for _, group in joined.sort_values(["at_bat_number", "event_index", "pitch_number"]).groupby(
        ["game_pk", "challenge_team_id"], dropna=False
    ):
        values = group["runValue"].astype(float).to_list()
        overturned = group["abs_overturned"].astype(bool).to_list()
        left = group["challengesLeft"].astype(float).to_list()
        for index, challenges_left in enumerate(left):
            if challenges_left != 1:
                continue
            future_overturned = [values[j] for j in range(index + 1, len(values)) if overturned[j]]
            if future_overturned:
                future_values.append(max(future_overturned))
    premium = float(np.nanmedian(future_values)) if future_values else 0.08
    premium = max(0.04, min(0.14, premium))
    return {
        "1": {
            "cost": base_cost + premium,
            "premium": premium,
            "sample": len(future_values),
            "source": "observed future overturned challenge value",
        },
        "2": {"cost": base_cost, "premium": 0.0, "sample": int(len(joined)), "source": "Savant breakeven cost"},
    }


def _edge_distance_inches(frame: pd.DataFrame) -> pd.Series:
    horizontal = (frame["plate_x"].abs() - 0.83).clip(lower=0) * 12.0
    vertical_low = (frame["sz_bot"] - frame["plate_z"]).clip(lower=0) * 12.0
    vertical_high = (frame["plate_z"] - frame["sz_top"]).clip(lower=0) * 12.0
    return pd.concat([horizontal, vertical_low, vertical_high], axis=1).max(axis=1)


def _zone_label(row: pd.Series) -> str:
    if pd.isna(row.get("z_bin")) or pd.isna(row.get("x_bin")):
        return "Location unavailable"
    z_bin = int(row.get("z_bin", -1))
    x_bin = int(row.get("x_bin", -1))
    if z_bin == 4:
        return "Top edge / above"
    if z_bin == 0:
        return "Bottom edge / below"
    if x_bin in (0, 1, 2):
        return "Third-base side"
    if x_bin in (4, 5, 6):
        return "First-base side"
    return "Middle lane"


def _observed_challenge_summary(
    statcast_2026: pd.DataFrame, abs_challenges: pd.DataFrame, count_values: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    empty = {
        "total": 0,
        "ballChallenges": 0,
        "strikeChallenges": 0,
        "ballOverturnRate": 0.0,
        "strikeOverturnRate": 0.0,
        "joinedPitchingTeam": [],
        "byCount": [],
        "byLocation": [],
        "byLocationCell": [],
        "ballChallengePoints": [],
        "strikeChallengePoints": [],
        "usablePitchReviews": 0,
    }
    if statcast_2026.empty or abs_challenges.empty:
        return empty
    events = _add_challenge_inventory(abs_challenges.copy())
    for column in ["game_pk", "at_bat_number", "pitch_number"]:
        events[column] = pd.to_numeric(events[column], errors="coerce")
    pitches = statcast_2026.copy()
    for column in ["game_pk", "at_bat_number", "pitch_number"]:
        pitches[column] = pd.to_numeric(pitches[column], errors="coerce")
    joined = events.merge(
        pitches,
        on=["game_pk", "at_bat_number", "pitch_number"],
        how="left",
        suffixes=("_abs", ""),
    )
    joined = joined[
        joined["description"].notna()
        & joined["call_description"].isin(["Ball", "Called Strike"])
        & joined["challenge_side"].isin(["fielding", "batting"])
    ].copy()
    if joined.empty:
        empty.update(total=int(len(events)))
        return empty
    joined["abs_overturned"] = joined["abs_overturned"].astype(bool)
    joined["zoneLabel"] = joined.apply(_zone_label, axis=1)
    joined["z_norm"] = pd.to_numeric(joined.get("z_norm"), errors="coerce")
    joined["plate_x"] = pd.to_numeric(joined.get("plate_x"), errors="coerce")
    joined["originalCall"] = np.where(joined["challenge_side"].eq("fielding"), "Ball", "Strike")
    run_value_by_count = {count: item["runValue"] for count, item in count_values.items()}
    confidence_by_count = {count: item["confidenceRequired"] for count, item in count_values.items()}
    joined["runValue"] = joined["count"].map(run_value_by_count).fillna(0.0)
    joined["confidenceRequired"] = joined["count"].map(confidence_by_count).fillna(1.0)
    ball_challenges = joined[joined["originalCall"].eq("Ball")].copy()
    strike_challenges = joined[joined["originalCall"].eq("Strike")].copy()
    by_count = (
        joined.groupby(["originalCall", "count"], dropna=False)
        .agg(challenges=("game_pk", "size"), overturns=("abs_overturned", "sum"))
        .reset_index()
    )
    by_count["successRate"] = by_count["overturns"] / by_count["challenges"]
    by_location = (
        joined.groupby(["originalCall", "zoneLabel"], dropna=False)
        .agg(challenges=("game_pk", "size"), overturns=("abs_overturned", "sum"))
        .reset_index()
    )
    by_location["successRate"] = by_location["overturns"] / by_location["challenges"]
    by_location_cell = (
        joined.dropna(subset=["x_bin", "z_bin"])
        .groupby(["originalCall", "x_bin", "z_bin", "zoneLabel"], dropna=False)
        .agg(challenges=("game_pk", "size"), overturns=("abs_overturned", "sum"))
        .reset_index()
    )
    by_location_cell["successRate"] = by_location_cell["overturns"] / by_location_cell["challenges"]
    point_columns = [
        "plate_x",
        "z_norm",
        "x_bin",
        "z_bin",
        "count",
        "game_date",
        "inning",
        "inning_topbot",
        "zoneLabel",
        "abs_overturned",
        "description",
        "pitch_type",
        "catcher_name",
        "pitcher_name",
        "challenge_side",
        "challengesLeft",
        "call_description",
        "runValue",
        "confidenceRequired",
    ]
    ball_points = ball_challenges.dropna(subset=["plate_x", "z_norm"])[
        [column for column in point_columns if column in ball_challenges.columns]
    ].copy()
    ball_points["originalCall"] = "Ball"
    ball_points["result"] = ball_points["abs_overturned"].map(
        {True: "Overturned to strike", False: "Upheld as ball"}
    )
    strike_points = strike_challenges.dropna(subset=["plate_x", "z_norm"])[
        [column for column in point_columns if column in strike_challenges.columns]
    ].copy()
    strike_points["originalCall"] = "Strike"
    strike_points["result"] = strike_points["abs_overturned"].map(
        {True: "Overturned to ball", False: "Upheld as strike"}
    )
    return {
        "total": int(len(events)),
        "usablePitchReviews": int(len(joined)),
        "ballChallenges": int(len(ball_challenges)),
        "strikeChallenges": int(len(strike_challenges)),
        "ballOverturnRate": float(ball_challenges["abs_overturned"].mean()) if not ball_challenges.empty else 0.0,
        "strikeOverturnRate": float(strike_challenges["abs_overturned"].mean()) if not strike_challenges.empty else 0.0,
        "joinedPitchingTeam": joined[
            [
                "game_date",
                "inning",
                "inning_topbot",
                "count",
                "call_description",
                "description",
                "pitch_type",
                "pitcher_name",
                "catcher_name",
                "zoneLabel",
                "abs_overturned",
            ]
        ]
        .head(20)
        .to_dict(orient="records"),
        "byCount": by_count.sort_values("challenges", ascending=False).head(8).to_dict(orient="records"),
        "byLocation": by_location.sort_values("challenges", ascending=False).to_dict(orient="records"),
        "byLocationCell": by_location_cell.sort_values(
            ["successRate", "challenges"], ascending=[False, False]
        ).to_dict(orient="records"),
        "ballChallengePoints": ball_points.to_dict(orient="records"),
        "strikeChallengePoints": strike_points.to_dict(orient="records"),
    }


def _pitch_sort_key(row: pd.Series) -> tuple[float, float, float]:
    return (
        safe_float(row.get("at_bat_number")),
        safe_float(row.get("pitch_number")),
        safe_float(row.get("event_index")),
    )


def _before_pitch(event: pd.Series, pitch: pd.Series) -> bool:
    return _pitch_sort_key(event) < _pitch_sort_key(pitch)


def _missed_opportunity_rows(
    statcast_2026: pd.DataFrame, abs_challenges: pd.DataFrame
) -> dict[str, dict[str, Any]]:
    if statcast_2026.empty or abs_challenges.empty:
        return {}
    called = _called_pitch_frame(statcast_2026)
    count_values = _count_run_values(called)
    if called.empty or not count_values:
        return {}
    inventory_costs = _inventory_costs(statcast_2026, abs_challenges, count_values)
    key_cols = ["game_pk", "at_bat_number", "pitch_number"]
    events = abs_challenges.copy()
    pitches = statcast_2026.copy()
    for frame in [events, pitches]:
        for column in key_cols:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    pitch_context_cols = key_cols + [
        "pitching_team",
        "catcher_name",
        "pitcher_name",
        "count",
        "description",
        "plate_x",
        "plate_z",
        "sz_top",
        "sz_bot",
        "z_norm",
        "x_bin",
        "z_bin",
        "game_date",
        "inning",
        "inning_topbot",
        "pitch_type",
    ]
    available_cols = [column for column in pitch_context_cols if column in pitches.columns]
    joined_events = events.merge(
        pitches[available_cols],
        on=key_cols,
        how="left",
    )
    fielding_events = joined_events[
        joined_events["challenge_side"].eq("fielding") & joined_events["pitching_team"].notna()
    ].copy()
    challenged_keys = {
        (int(row.game_pk), int(row.at_bat_number), int(row.pitch_number))
        for row in fielding_events.dropna(subset=key_cols).itertuples()
    }

    called_balls = called[called["is_called_ball"]].copy()
    called_balls = called_balls.dropna(subset=key_cols + ["pitching_team", "catcher_name"])
    called_balls["runValue"] = called_balls["count"].map(
        {count: item["runValue"] for count, item in count_values.items()}
    )
    called_balls = called_balls.dropna(subset=["runValue", "plate_x", "plate_z", "sz_top", "sz_bot"])
    if called_balls.empty:
        return {}
    called_balls["edgeDistanceInches"] = _edge_distance_inches(called_balls)
    called_balls["zoneLabel"] = called_balls.apply(_zone_label, axis=1)
    called_balls["normalizedCatcher"] = called_balls["catcher_name"].map(_normalize_name)
    called_balls["wasFieldingChallenge"] = called_balls.apply(
        lambda row: (
            int(row["game_pk"]),
            int(row["at_bat_number"]),
            int(row["pitch_number"]),
        )
        in challenged_keys,
        axis=1,
    )

    summaries: dict[str, dict[str, Any]] = {}
    for normalized_name, group in called_balls.groupby("normalizedCatcher", dropna=False):
        summaries[normalized_name] = {
            "reviewHoldCount": 0,
            "greenHoldCount": 0,
            "leanHoldCount": 0,
            "reviewHoldValue": 0.0,
            "calledBallCandidates": int(len(group)),
            "topReviewHolds": [],
        }

    fielding_events = fielding_events.sort_values(key_cols + ["event_index"], na_position="last")
    for (game_pk, pitching_team), group in called_balls.sort_values(key_cols).groupby(
        ["game_pk", "pitching_team"], dropna=False
    ):
        event_group = fielding_events[
            fielding_events["game_pk"].eq(game_pk) & fielding_events["pitching_team"].eq(pitching_team)
        ].copy()
        event_records = [row for _, row in event_group.iterrows()]
        for _, pitch in group.iterrows():
            normalized_name = str(pitch.get("normalizedCatcher", ""))
            if not normalized_name or bool(pitch.get("wasFieldingChallenge")):
                continue
            prior_losses = sum(
                1
                for event in event_records
                if _before_pitch(event, pitch) and not bool(event.get("abs_overturned"))
            )
            challenges_left = max(0, 2 - prior_losses)
            if challenges_left <= 0:
                continue
            run_value = safe_float(pitch.get("runValue"))
            cost_meta = inventory_costs[str(int(min(challenges_left, 2)))]
            confidence, recommendation = _recommendation_from_cost(run_value, safe_float(cost_meta.get("cost")))
            near_edge = safe_float(pitch.get("edgeDistanceInches")) <= 3.0
            if not near_edge or recommendation not in {"Challenge", "Lean"}:
                continue
            review_value = max(0.0, run_value - safe_float(cost_meta.get("cost")))
            summary = summaries.setdefault(
                normalized_name,
                {
                    "reviewHoldCount": 0,
                    "greenHoldCount": 0,
                    "leanHoldCount": 0,
                    "reviewHoldValue": 0.0,
                    "calledBallCandidates": 0,
                    "topReviewHolds": [],
                },
            )
            summary["reviewHoldCount"] += 1
            summary["reviewHoldValue"] += review_value
            if recommendation == "Challenge":
                summary["greenHoldCount"] += 1
            else:
                summary["leanHoldCount"] += 1
            summary["topReviewHolds"].append(
                {
                    "gameDate": pitch.get("game_date"),
                    "count": pitch.get("count"),
                    "inning": pitch.get("inning"),
                    "inningTopBot": pitch.get("inning_topbot"),
                    "pitcher": pitch.get("pitcher_name"),
                    "pitchType": pitch.get("pitch_type"),
                    "zoneLabel": pitch.get("zoneLabel"),
                    "runValue": run_value,
                    "reviewValue": review_value,
                    "confidenceRequired": confidence,
                    "challengesLeft": int(challenges_left),
                    "recommendation": recommendation,
                    "edgeDistanceInches": safe_float(pitch.get("edgeDistanceInches")),
                }
            )

    for summary in summaries.values():
        summary["topReviewHolds"] = sorted(
            summary["topReviewHolds"],
            key=lambda item: (-safe_float(item.get("reviewValue")), safe_float(item.get("confidenceRequired"))),
        )[:5]
        summary["reviewHoldValue"] = float(summary["reviewHoldValue"])
    return summaries


def _empty_strategy_summary() -> dict[str, Any]:
    return {
        "actionableDecisions": 0,
        "followedPlanCount": 0,
        "missedRecommendedCount": 0,
        "outsidePlanChallengeCount": 0,
        "redLightHoldCount": 0,
        "actualStrategyChallenges": 0,
        "strategyAdherenceRate": 0.0,
    }


def _recommendation_for_decision(
    count: object,
    challenges_left: object,
    count_values: dict[str, dict[str, Any]],
    inventory_costs: dict[str, Any],
) -> tuple[float, float, str]:
    run_value = safe_float((count_values.get(str(count)) or {}).get("runValue"))
    left_key = str(int(min(max(safe_float(challenges_left, 2.0), 1.0), 2.0)))
    cost = safe_float((inventory_costs.get(left_key) or inventory_costs.get("2") or {}).get("cost"), 0.20)
    _, recommendation = _recommendation_from_cost(run_value, cost)
    return run_value, cost, recommendation


def _strategy_adherence_rows(
    statcast_2026: pd.DataFrame, abs_challenges: pd.DataFrame
) -> dict[str, dict[str, Any]]:
    if statcast_2026.empty or abs_challenges.empty:
        return {}
    called = _called_pitch_frame(statcast_2026)
    count_values = _count_run_values(called)
    if called.empty or not count_values:
        return {}
    inventory_costs = _inventory_costs(statcast_2026, abs_challenges, count_values)
    key_cols = ["game_pk", "at_bat_number", "pitch_number"]
    events = _add_challenge_inventory(abs_challenges.copy())
    pitches = statcast_2026.copy()
    for frame in [events, pitches]:
        for column in key_cols:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    pitch_context_cols = key_cols + [
        "pitching_team",
        "catcher_name",
        "count",
        "description",
        "plate_x",
        "plate_z",
        "sz_top",
        "sz_bot",
        "game_date",
        "inning",
        "inning_topbot",
        "pitch_type",
        "pitcher_name",
    ]
    available_cols = [column for column in pitch_context_cols if column in pitches.columns]
    joined_events = events.merge(pitches[available_cols], on=key_cols, how="left")
    fielding_events = joined_events[
        joined_events["challenge_side"].eq("fielding")
        & joined_events["pitching_team"].notna()
        & joined_events["catcher_name"].notna()
    ].copy()

    summaries: dict[str, dict[str, Any]] = {}
    if not fielding_events.empty:
        fielding_events = fielding_events.dropna(subset=key_cols + ["plate_x", "plate_z", "sz_top", "sz_bot"])
        if not fielding_events.empty:
            fielding_events["edgeDistanceInches"] = _edge_distance_inches(fielding_events)
            fielding_events["normalizedCatcher"] = fielding_events["catcher_name"].map(_normalize_name)
            for _, event in fielding_events.iterrows():
                normalized_name = str(event.get("normalizedCatcher", ""))
                if not normalized_name:
                    continue
                summary = summaries.setdefault(normalized_name, _empty_strategy_summary())
                _, _, recommendation = _recommendation_for_decision(
                    event.get("count"),
                    event.get("challengesLeft"),
                    count_values,
                    inventory_costs,
                )
                near_edge = safe_float(event.get("edgeDistanceInches")) <= 3.0
                follows_plan = near_edge and recommendation in {"Challenge", "Lean"}
                summary["actionableDecisions"] += 1
                summary["actualStrategyChallenges"] += 1
                if follows_plan:
                    summary["followedPlanCount"] += 1
                else:
                    summary["outsidePlanChallengeCount"] += 1

    challenged_keys = {
        (int(row.game_pk), int(row.at_bat_number), int(row.pitch_number))
        for row in fielding_events.dropna(subset=key_cols).itertuples()
    }
    called_balls = called[called["is_called_ball"]].copy()
    called_balls = called_balls.dropna(subset=key_cols + ["pitching_team", "catcher_name"])
    called_balls = called_balls.dropna(subset=["plate_x", "plate_z", "sz_top", "sz_bot"])
    if called_balls.empty:
        for summary in summaries.values():
            actions = int(summary["actionableDecisions"])
            summary["strategyAdherenceRate"] = safe_float(summary["followedPlanCount"]) / actions if actions else 0.0
        return summaries

    called_balls["edgeDistanceInches"] = _edge_distance_inches(called_balls)
    called_balls["normalizedCatcher"] = called_balls["catcher_name"].map(_normalize_name)
    called_balls["wasFieldingChallenge"] = called_balls.apply(
        lambda row: (
            int(row["game_pk"]),
            int(row["at_bat_number"]),
            int(row["pitch_number"]),
        )
        in challenged_keys,
        axis=1,
    )

    fielding_events = fielding_events.sort_values(key_cols + ["event_index"], na_position="last")
    for (game_pk, pitching_team), group in called_balls.sort_values(key_cols).groupby(
        ["game_pk", "pitching_team"], dropna=False
    ):
        event_group = fielding_events[
            fielding_events["game_pk"].eq(game_pk) & fielding_events["pitching_team"].eq(pitching_team)
        ].copy()
        event_records = [row for _, row in event_group.iterrows()]
        for _, pitch in group.iterrows():
            normalized_name = str(pitch.get("normalizedCatcher", ""))
            if not normalized_name or bool(pitch.get("wasFieldingChallenge")):
                continue
            prior_losses = sum(
                1
                for event in event_records
                if _before_pitch(event, pitch) and not bool(event.get("abs_overturned"))
            )
            challenges_left = max(0, 2 - prior_losses)
            if challenges_left <= 0 or safe_float(pitch.get("edgeDistanceInches")) > 3.0:
                continue
            _, _, recommendation = _recommendation_for_decision(
                pitch.get("count"),
                challenges_left,
                count_values,
                inventory_costs,
            )
            summary = summaries.setdefault(normalized_name, _empty_strategy_summary())
            summary["actionableDecisions"] += 1
            if recommendation in {"Challenge", "Lean"}:
                summary["missedRecommendedCount"] += 1
            else:
                summary["followedPlanCount"] += 1
                summary["redLightHoldCount"] += 1

    for summary in summaries.values():
        actions = int(summary["actionableDecisions"])
        summary["strategyAdherenceRate"] = safe_float(summary["followedPlanCount"]) / actions if actions else 0.0
    return summaries


def enrich_catcher_report_metrics(
    catcher_rows: list[dict[str, Any]], statcast_2026: pd.DataFrame, abs_challenges: pd.DataFrame
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in catcher_rows]
    missed = _missed_opportunity_rows(statcast_2026, abs_challenges)
    strategy = _strategy_adherence_rows(statcast_2026, abs_challenges)
    pitch_counts: dict[str, int] = {}
    if not statcast_2026.empty and "catcher_name" in statcast_2026.columns:
        pitch_counts = (
            statcast_2026.assign(normalizedCatcher=statcast_2026["catcher_name"].map(_normalize_name))
            .groupby("normalizedCatcher", dropna=False)
            .size()
            .astype(int)
            .to_dict()
        )
    success_values = [
        safe_float(row.get("successRate"), math.nan)
        for row in rows
        if safe_float(row.get("challenges")) >= 5
        and not math.isnan(safe_float(row.get("successRate"), math.nan))
    ]
    above_expected_values = [
        safe_float(row.get("successRateAboveExpected"), math.nan)
        for row in rows
        if safe_float(row.get("challenges")) >= 5
        and not math.isnan(safe_float(row.get("successRateAboveExpected"), math.nan))
    ]
    reasonable_rate_values = [
        safe_float(row.get("selectionReasonableRate"), math.nan)
        for row in rows
        if safe_float(row.get("challenges")) >= 5
        and not math.isnan(safe_float(row.get("selectionReasonableRate"), math.nan))
    ]
    reasonable_taken_values = [
        safe_float(row.get("selectionTakenRate"), math.nan)
        for row in rows
        if safe_float(row.get("challenges")) >= 5
        and not math.isnan(safe_float(row.get("selectionTakenRate"), math.nan))
    ]
    for row in rows:
        missed_row = missed.get(row.get("normalizedName", ""), {})
        strategy_row = strategy.get(row.get("normalizedName", ""), {})
        row["missedOpportunityCount"] = int(safe_float(missed_row.get("reviewHoldCount")))
        row["missedOpportunityGreen"] = int(safe_float(missed_row.get("greenHoldCount")))
        row["missedOpportunityLean"] = int(safe_float(missed_row.get("leanHoldCount")))
        row["missedOpportunityValue"] = safe_float(missed_row.get("reviewHoldValue"))
        row["calledBallCandidates"] = int(safe_float(missed_row.get("calledBallCandidates")))
        row["catcherPitchCount"] = int(pitch_counts.get(str(row.get("normalizedName", "")), 0))
        denominator = row["catcherPitchCount"] or row["calledBallCandidates"]
        row["missedOpportunityRate"] = row["missedOpportunityCount"] / denominator if denominator else 0.0
        row["topMissedOpportunities"] = missed_row.get("topReviewHolds", [])
        row["successRatePercentile"] = _percentile_rank(safe_float(row.get("successRate")), success_values)
        row["successRateAboveExpectedPercentile"] = _percentile_rank(
            safe_float(row.get("successRateAboveExpected")),
            above_expected_values,
        )
        row["resultsScore"] = 0.5 * safe_float(row.get("successRatePercentile")) + 0.5 * safe_float(
            row.get("successRateAboveExpectedPercentile")
        )
        row["selectionReasonableRatePercentile"] = _percentile_rank(
            safe_float(row.get("selectionReasonableRate")),
            reasonable_rate_values,
        )
        row["selectionReasonableChallengePercentile"] = row["selectionReasonableRatePercentile"]
        row["selectionTakenPercentile"] = _percentile_rank(
            safe_float(row.get("selectionTakenRate")),
            reasonable_taken_values,
        )
        row["selectionScore"] = 0.5 * safe_float(
            row.get("selectionReasonableChallengePercentile")
        ) + 0.5 * safe_float(row.get("selectionTakenPercentile"))
        row["strategyActionableDecisions"] = int(safe_float(strategy_row.get("actionableDecisions")))
        row["strategyFollowedCount"] = int(safe_float(strategy_row.get("followedPlanCount")))
        row["strategyMissedRecommendedCount"] = int(safe_float(strategy_row.get("missedRecommendedCount")))
        row["strategyOutsidePlanChallengeCount"] = int(safe_float(strategy_row.get("outsidePlanChallengeCount")))
        row["strategyRedLightHoldCount"] = int(safe_float(strategy_row.get("redLightHoldCount")))
        row["actualStrategyChallenges"] = int(safe_float(strategy_row.get("actualStrategyChallenges")))
        row["strategyAdherenceRate"] = safe_float(strategy_row.get("strategyAdherenceRate"))

    value_rates = [
        safe_float(row.get("totalVsExpected")) / safe_float(row.get("catcherPitchCount")) * 1000.0
        for row in rows
        if safe_float(row.get("challenges")) >= 5 and safe_float(row.get("catcherPitchCount")) > 0
    ]
    league_value_per_1000 = float(np.nanmean(value_rates)) if value_rates else 0.0
    league_value_per_1000_std = float(np.nanstd(value_rates)) if len(value_rates) > 1 else 0.0
    for row in rows:
        pitch_count = safe_float(row.get("catcherPitchCount"))
        row["netOverturnsPer1000"] = (
            safe_float(row.get("totalVsExpected")) / pitch_count * 1000.0 if pitch_count > 0 else 0.0
        )
        row["absValuePlusLeagueAverage"] = league_value_per_1000
        row["absValuePlusLeagueStdDev"] = league_value_per_1000_std
        row["absValuePlus"] = (
            100.0 + 15.0 * (row["netOverturnsPer1000"] - league_value_per_1000) / league_value_per_1000_std
            if league_value_per_1000_std > 0
            else 100.0
        )

    thresholds = {
        "absValuePlus": _grade_thresholds(
            rows,
            "absValuePlus",
            source="ABS Value+ from Savant net_for among workbook catchers with 5+ challenges",
        ),
        "resultsScore": _grade_thresholds(
            rows,
            "resultsScore",
            source="Blended success and expected-adjusted result score, 5+ challenge catchers",
        ),
        "selectionScore": _grade_thresholds(
            rows,
            "selectionScore",
            source="Blended reasonable-challenge rate and reasonable-opportunity take rate, 5+ challenge catchers",
        ),
        "totalVsExpected": _grade_thresholds(
            rows,
            "totalVsExpected",
            source="Savant net_for among league catchers with 5+ challenges",
        ),
        "missedOpportunityValue": _grade_thresholds(
            rows,
            "missedOpportunityValue",
            higher_is_better=False,
            source="Review-hold value from Statcast called balls, 5+ challenge catchers",
        ),
        "strategyAdherenceRate": _grade_thresholds(
            rows,
            "strategyAdherenceRate",
            min_sample_key="strategyActionableDecisions",
            source="Count Strategy among catchers with 5+ actionable strategy decisions",
        ),
        "usage": _usage_thresholds(rows),
    }
    for row in rows:
        row["absValuePlusGrade"] = _grade_from_thresholds(
            safe_float(row.get("absValuePlus")), thresholds["absValuePlus"]
        )
        row["resultsGrade"] = _grade_from_thresholds(safe_float(row.get("resultsScore")), thresholds["resultsScore"])
        row["executionGrade"] = row["resultsGrade"]
        row["selectionGrade"] = _grade_from_thresholds(
            safe_float(row.get("selectionScore")), thresholds["selectionScore"]
        )
        row["overallGrade"] = _grade_from_thresholds(
            safe_float(row.get("totalVsExpected")), thresholds["totalVsExpected"]
        )
        row["missedOpportunityGrade"] = _grade_from_thresholds(
            safe_float(row.get("missedOpportunityValue")), thresholds["missedOpportunityValue"]
        )
        row["strategyAdherenceGrade"] = (
            _grade_from_thresholds(safe_float(row.get("strategyAdherenceRate")), thresholds["strategyAdherenceRate"])
            if safe_float(row.get("strategyActionableDecisions")) >= 5
            else "NA"
        )
        usage_percentile = _usage_percentile(safe_float(row.get("expectedChallengeDiff")), thresholds["usage"])
        row["usagePercentile"] = usage_percentile
        row["aggressionLabel"] = _usage_label_from_percentile(usage_percentile)
        row["archetype"] = archetype_from_values(
            safe_float(row.get("totalVsExpected")),
            safe_float(row.get("successRate")),
            str(row.get("aggressionLabel", "Average")),
        )
        row["gradeThresholds"] = thresholds
    return sorted(rows, key=lambda item: item["totalVsExpected"], reverse=True)


def build_strategy_guide(
    statcast_2026: pd.DataFrame, abs_challenges: pd.DataFrame
) -> dict[str, Any]:
    called = _called_pitch_frame(statcast_2026)
    count_values = _count_run_values(called)
    count_rows = sorted(count_values.values(), key=lambda row: (-row["runValue"], _count_order(row["count"])))
    inventory_costs = _inventory_costs(statcast_2026, abs_challenges, count_values)
    count_order = ["0-0", "0-1", "1-0", "0-2", "1-1", "2-0", "1-2", "2-1", "3-0", "2-2", "3-1", "3-2"]
    game_states = [
        {"key": "all", "label": "Any state"},
        {"key": "risp", "label": "RISP"},
        {"key": "late_close", "label": "Late close"},
    ]
    strategy_matrix_rows: list[dict[str, Any]] = []
    challenge_left_values = [2, 1]

    situation_rows: list[dict[str, Any]] = []
    game_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    if not called.empty:
        enriched = called.copy()
        enriched["baseState"] = enriched.apply(_base_state, axis=1)
        enriched["inningBucket"] = enriched["inning"].map(_inning_bucket)
        enriched["scoreBucket"] = enriched.apply(_score_bucket, axis=1)
        enriched["baseBucket"] = np.select(
            [
                enriched["on_2b"].notna() | enriched["on_3b"].notna(),
                enriched["on_1b"].notna(),
            ],
            ["RISP", "Runner on first"],
            default="Empty",
        )
        enriched["isLateClose"] = (enriched["inning"].map(safe_float) >= 7) & (
            (enriched["fld_score"].map(safe_float) - enriched["bat_score"].map(safe_float)).abs() <= 1
        )
        for count in count_order:
            if count not in count_values:
                continue
            count_group = enriched[enriched["count"].eq(count)]
            row_cells: list[dict[str, Any]] = []
            for game_state in game_states:
                if game_state["key"] == "risp":
                    state_group = count_group[count_group["baseBucket"].eq("RISP")]
                elif game_state["key"] == "late_close":
                    state_group = count_group[count_group["isLateClose"]]
                else:
                    state_group = count_group
                summary = _run_value_summary(state_group, count_values[count])
                for challenges_left in challenge_left_values:
                    cost_meta = inventory_costs[str(challenges_left)]
                    confidence, recommendation = _recommendation_from_cost(summary["runValue"], cost_meta["cost"])
                    row_cells.append(
                        {
                            "gameState": game_state["key"],
                            "gameStateLabel": game_state["label"],
                            "challengesLeft": challenges_left,
                            "runValue": summary["runValue"],
                            "recommendation": recommendation,
                            "confidenceRequired": confidence,
                            "challengeCost": cost_meta["cost"],
                            "inventoryPremium": cost_meta["premium"],
                            "inventorySample": cost_meta["sample"],
                            "inventorySource": cost_meta["source"],
                            "calledPitches": summary["calledPitches"],
                            "calledBalls": summary["calledBalls"],
                            "calledStrikes": summary["calledStrikes"],
                            "ballRunValue": summary["ballRunValue"],
                            "strikeRunValue": summary["strikeRunValue"],
                            "fallbackUsed": summary["fallbackUsed"],
                        }
                    )
            strategy_matrix_rows.append({"count": count, "cells": row_cells})
        for (count, base_state), group in enriched.groupby(["count", "baseState"]):
            balls = group[group["is_called_ball"]]["delta_run_exp"]
            strikes = group[group["is_called_strike"]]["delta_run_exp"]
            fallback = count_values.get(count, {}).get("runValue", 0.0)
            if len(group) < 60 or len(balls) < 15 or len(strikes) < 15:
                run_value = float(fallback)
            else:
                run_value = max(0.0, float(balls.mean() - strikes.mean()))
            confidence = _confidence_required(run_value)
            situation_rows.append(
                {
                    "count": count,
                    "baseState": base_state,
                    "samples": int(len(group)),
                    "runValue": run_value,
                    "confidenceRequired": confidence,
                    "band": _challenge_band(run_value, confidence),
                }
            )
        situation_rows = sorted(
            situation_rows,
            key=lambda row: (-row["runValue"], row["baseState"], _count_order(row["count"])),
        )[:18]
        if "delta_home_win_exp" in enriched.columns:
            enriched["delta_home_win_exp"] = pd.to_numeric(enriched["delta_home_win_exp"], errors="coerce")
            is_bottom = enriched["inning_topbot"].astype(str).str.lower().eq("bot")
            enriched["batWinDelta"] = enriched["delta_home_win_exp"].where(is_bottom, -enriched["delta_home_win_exp"])
            enriched = enriched.dropna(subset=["batWinDelta"])
            for (inning_bucket, score_bucket), group in enriched.groupby(["inningBucket", "scoreBucket"]):
                balls = group[group["is_called_ball"]]
                strikes = group[group["is_called_strike"]]
                if len(group) < 200 or len(balls) < 50 or len(strikes) < 50:
                    continue
                run_value = max(0.0, float(balls["delta_run_exp"].mean() - strikes["delta_run_exp"].mean()))
                win_swing = max(0.0, float(balls["batWinDelta"].mean() - strikes["batWinDelta"].mean()))
                game_rows.append(
                    {
                        "inningBucket": inning_bucket,
                        "scoreBucket": score_bucket,
                        "samples": int(len(group)),
                        "runValue": run_value,
                        "winSwing": win_swing,
                        "band": _challenge_band(run_value, _confidence_required(run_value)),
                    }
                )
            game_rows = sorted(
                game_rows,
                key=lambda row: (-row["winSwing"], row["inningBucket"], row["scoreBucket"]),
            )
            for (count, inning_bucket, score_bucket, base_bucket), group in enriched.groupby(
                ["count", "inningBucket", "scoreBucket", "baseBucket"]
            ):
                balls = group[group["is_called_ball"]]
                strikes = group[group["is_called_strike"]]
                if len(group) < 120 or len(balls) < 25 or len(strikes) < 25:
                    continue
                run_value = max(0.0, float(balls["delta_run_exp"].mean() - strikes["delta_run_exp"].mean()))
                win_swing = max(0.0, float(balls["batWinDelta"].mean() - strikes["batWinDelta"].mean()))
                confidence = _confidence_required(run_value)
                decision_rows.append(
                    {
                        "count": count,
                        "inningBucket": inning_bucket,
                        "scoreBucket": score_bucket,
                        "baseBucket": base_bucket,
                        "samples": int(len(group)),
                        "runValue": run_value,
                        "winSwing": win_swing,
                        "confidenceRequired": confidence,
                        "band": _challenge_band(run_value, confidence),
                    }
                )
            decision_rows = sorted(
                decision_rows,
                key=lambda row: (
                    row["band"] != "Green",
                    row["band"] != "Yellow",
                    -row["runValue"],
                    -row["winSwing"],
                ),
            )[:16]

    location_rows: list[dict[str, Any]] = []
    if not called.empty and count_values:
        called_balls = called[called["is_called_ball"]].copy()
        called_balls["runValue"] = called_balls["count"].map(
            {count: item["runValue"] for count, item in count_values.items()}
        )
        called_balls = called_balls.dropna(subset=["runValue", "plate_x", "plate_z", "sz_top", "sz_bot"])
        called_balls["edgeDistanceInches"] = _edge_distance_inches(called_balls)
        called_balls["nearEdge"] = called_balls["edgeDistanceInches"] <= 3.0
        called_balls["highValue"] = called_balls["runValue"] >= 0.30
        called_balls["zoneLabel"] = called_balls.apply(_zone_label, axis=1)
        grouped = (
            called_balls.groupby(["x_bin", "z_bin", "zoneLabel"], dropna=False)
            .agg(
                calledBalls=("description", "size"),
                avgRunValue=("runValue", "mean"),
                nearEdgeRate=("nearEdge", "mean"),
                highValueRate=("highValue", "mean"),
            )
            .reset_index()
        )
        grouped = grouped[grouped["calledBalls"] >= 40]
        grouped["challengeScore"] = grouped["avgRunValue"] * (0.5 + grouped["nearEdgeRate"])
        location_rows = grouped.sort_values("challengeScore", ascending=False).head(18).to_dict(orient="records")

    observed = _observed_challenge_summary(statcast_2026, abs_challenges, count_values)
    theory_by_cell = {
        (int(row["x_bin"]), int(row["z_bin"])): row
        for row in location_rows
        if pd.notna(row.get("x_bin")) and pd.notna(row.get("z_bin"))
    }
    combined_location_rows: list[dict[str, Any]] = []
    for row in observed.get("byLocationCell", []):
        if safe_float(row.get("challenges")) < 8:
            continue
        key = (int(row["x_bin"]), int(row["z_bin"]))
        theory = theory_by_cell.get(key)
        run_value = safe_float(theory.get("avgRunValue")) if theory else 0.0
        success_rate = safe_float(row.get("successRate"))
        combined_location_rows.append(
            {
                "x_bin": int(row["x_bin"]),
                "z_bin": int(row["z_bin"]),
                "zoneLabel": row.get("zoneLabel"),
                "challenges": int(safe_float(row.get("challenges"))),
                "overturns": int(safe_float(row.get("overturns"))),
                "successRate": success_rate,
                "avgRunValue": run_value,
                "decisionScore": run_value * success_rate,
                "band": _combined_band(run_value, success_rate),
            }
        )
    combined_location_rows = sorted(
        combined_location_rows,
        key=lambda row: (-row["decisionScore"], -row["challenges"]),
    )

    return {
        "countRows": count_rows,
        "strategyMatrixRows": strategy_matrix_rows,
        "strategyGameStates": game_states,
        "strategyChallengeLeftValues": challenge_left_values,
        "inventoryCosts": inventory_costs,
        "situationRows": situation_rows,
        "gameRows": game_rows,
        "decisionRows": decision_rows,
        "locationRows": location_rows,
        "combinedLocationRows": combined_location_rows,
        "observed": observed,
        "notes": [
            "Run value is estimated from 2026 Statcast called pitches as the batting run expectancy swing between a called ball and a called strike.",
            "Confidence required uses Savant's breakeven idea with a 0.20 run challenge cost.",
            "Pitch-level challenge events come from MLB Stats API reviewDetails and are joined to Statcast by game, plate appearance, and pitch number.",
        ],
    }


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
