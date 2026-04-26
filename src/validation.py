from __future__ import annotations

from typing import Any

import pandas as pd


WORKBOOK_REQUIRED_COLUMNS = {
    "entity_name",
    "team_abbr",
    "level",
    "parent_org",
    "total_vs_expected",
    "net_for",
    "net_against",
    "n_challenges",
    "n_overturns",
    "n_confirms",
    "rate_overturns",
    "exp_chal",
    "exp_rate_overturns",
    "exp_rate_challenges_diff",
}

STATCAST_REQUIRED_COLUMNS = {
    "game_date",
    "game_pk",
    "inning",
    "inning_topbot",
    "home_team",
    "away_team",
    "pitcher",
    "player_name",
    "fielder_2",
    "pitch_type",
    "balls",
    "strikes",
    "description",
    "type",
    "plate_x",
    "plate_z",
    "sz_top",
    "sz_bot",
    "stand",
}

ABS_CHALLENGE_REQUIRED_COLUMNS = {
    "game_pk",
    "at_bat_number",
    "pitch_number",
    "call_description",
    "abs_overturned",
    "challenge_team_id",
    "challenge_side",
}


def validation_item(name: str, ok: bool, message: str) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "message": message}


def validate_workbook(df: pd.DataFrame) -> list[dict[str, Any]]:
    missing = sorted(WORKBOOK_REQUIRED_COLUMNS.difference(df.columns))
    return [
        validation_item(
            "Catcher workbook schema",
            not missing,
            "All required workbook columns are present."
            if not missing
            else "Missing workbook columns: " + ", ".join(missing),
        ),
        validation_item(
            "Catcher workbook rows",
            len(df) > 0,
            f"Workbook contains {len(df)} catcher rows.",
        ),
    ]


def validate_statcast(df: pd.DataFrame, season: int) -> list[dict[str, Any]]:
    if df.empty:
        return [
            validation_item(
                f"{season} Statcast data",
                False,
                f"No {season} Statcast rows are available in cache or pull output.",
            )
        ]
    missing = sorted(STATCAST_REQUIRED_COLUMNS.difference(df.columns))
    return [
        validation_item(
            f"{season} Statcast schema",
            not missing,
            "All required Statcast columns are present."
            if not missing
            else f"Missing {season} Statcast columns: " + ", ".join(missing),
        ),
        validation_item(
            f"{season} Statcast rows",
            len(df) > 0,
            f"{season} Statcast contains {len(df):,} pitch rows.",
        ),
    ]


def validate_abs_challenges(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return [
            validation_item(
                "ABS challenge event data",
                False,
                "No MLB Stats API ABS challenge rows are available in cache or pull output.",
            )
        ]
    missing = sorted(ABS_CHALLENGE_REQUIRED_COLUMNS.difference(df.columns))
    fielding = int(df["challenge_side"].eq("fielding").sum()) if "challenge_side" in df.columns else 0
    batting = int(df["challenge_side"].eq("batting").sum()) if "challenge_side" in df.columns else 0
    return [
        validation_item(
            "ABS challenge event schema",
            not missing,
            "All required MLB Stats API challenge columns are present."
            if not missing
            else "Missing ABS challenge columns: " + ", ".join(missing),
        ),
        validation_item(
            "ABS challenge event rows",
            len(df) > 0,
            f"Challenge cache contains {len(df):,} rows: {fielding:,} fielding-side and {batting:,} batting-side.",
        ),
    ]


def validate_join_quality(catcher_df: pd.DataFrame, statcast_df: pd.DataFrame) -> list[dict[str, Any]]:
    if statcast_df.empty or "catcher_name" not in statcast_df.columns:
        return [
            validation_item(
                "Catcher join quality",
                False,
                "Catcher join was not evaluated because Statcast catcher names are unavailable.",
            )
        ]
    workbook_names = set(catcher_df["entity_name"].dropna().astype(str).str.lower())
    statcast_names = set(statcast_df["catcher_name"].dropna().astype(str).str.lower())
    matched = sorted(workbook_names.intersection(statcast_names))
    unmatched = sorted(workbook_names.difference(statcast_names))
    message = f"Matched {len(matched)} of {len(workbook_names)} workbook catchers."
    if unmatched:
        message += " Unmatched examples: " + ", ".join(unmatched[:8])
    return [validation_item("Catcher join quality", len(matched) > 0, message)]
