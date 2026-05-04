from __future__ import annotations

import re

import numpy as np
import pandas as pd


TAKEN_DESCRIPTIONS = {
    "ball",
    "blocked_ball",
    "called_strike",
    "pitchout",
}

CALLED_STRIKE_DESCRIPTIONS = {"called_strike"}
SWINGING_STRIKE_DESCRIPTIONS = {
    "swinging_strike",
    "swinging_strike_blocked",
}

X_EDGES = [-2.0, -1.25, -0.83, -0.28, 0.28, 0.83, 1.25, 2.0]
X_LABELS = [
    "Far third-base",
    "Third-base chase",
    "Third-base edge",
    "Middle",
    "First-base edge",
    "First-base chase",
    "Far first-base",
]
Z_EDGES = [-0.5, 0.0, 0.25, 0.75, 1.0, 1.5]
Z_LABELS = ["Below", "Bottom", "Heart", "Top", "Above"]


def normalize_name(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    return re.sub(r"\s+", " ", text)


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0)
    return out


def prepare_workbook(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "total_vs_expected",
        "net_for",
        "net_against",
        "n_challenges",
        "n_overturns",
        "n_confirms",
        "rate_overturns",
        "exp_chal",
        "exp_chal_gained",
        "exp_chal_lost",
        "exp_rate_overturns",
        "net_chal_gained",
        "net_chal_lost",
        "n_strikeouts_flip",
        "n_walks_flip",
        "exp_rate_challenges",
        "exp_rate_challenges_diff",
        "rsn_opp",
        "rsn_chal",
        "perc_chal_rsn",
        "perc_rsn_taken",
    ]
    out = coerce_numeric(df, numeric_columns)
    out["normalized_name"] = out["entity_name"].map(normalize_name)
    out["team_abbr"] = out["team_abbr"].fillna("Unknown").astype(str)
    return out


def attach_catcher_names(statcast_df: pd.DataFrame, lookup_df: pd.DataFrame) -> pd.DataFrame:
    if statcast_df.empty:
        return statcast_df.copy()
    out = statcast_df.copy()
    out["catcher_id"] = pd.to_numeric(out.get("fielder_2"), errors="coerce")
    if "catcher_name" in out.columns and out["catcher_name"].notna().any():
        out["catcher_name"] = out["catcher_name"].fillna("Unknown Catcher").astype(str)
        return out
    if not lookup_df.empty and {"mlbam_id", "catcher_name"}.issubset(lookup_df.columns):
        lookup = lookup_df.copy()
        lookup["mlbam_id"] = pd.to_numeric(lookup["mlbam_id"], errors="coerce")
        out = out.merge(lookup, left_on="catcher_id", right_on="mlbam_id", how="left")
        out["catcher_name"] = out["catcher_name"].fillna(
            "Catcher " + out["catcher_id"].fillna(0).astype(int).astype(str)
        )
        return out
    out["catcher_name"] = "Catcher " + out["catcher_id"].fillna(0).astype(int).astype(str)
    return out


def prepare_statcast(df: pd.DataFrame, season: int, lookup_df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = attach_catcher_names(df, lookup_df)
    out["season"] = season
    out["game_date"] = pd.to_datetime(out["game_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["pitching_team"] = np.where(
        out["inning_topbot"].astype(str).str.lower().eq("top"),
        out["home_team"],
        out["away_team"],
    )
    out["pitcher_name"] = out.get("player_name", "Unknown Pitcher").fillna("Unknown Pitcher").astype(str)
    out["pitch_type"] = out.get("pitch_type", "Unknown").fillna("Unknown").astype(str)
    out["stand"] = out.get("stand", "Unknown").fillna("Unknown").astype(str)
    out["balls"] = pd.to_numeric(out["balls"], errors="coerce").fillna(0).astype(int)
    out["strikes"] = pd.to_numeric(out["strikes"], errors="coerce").fillna(0).astype(int)
    out["count"] = out["balls"].astype(str) + "-" + out["strikes"].astype(str)
    out["description"] = out["description"].fillna("").astype(str)
    out["is_taken_pitch"] = out["description"].isin(TAKEN_DESCRIPTIONS)
    out["is_called_strike"] = out["description"].isin(CALLED_STRIKE_DESCRIPTIONS)
    out["is_swinging_strike"] = out["description"].isin(SWINGING_STRIKE_DESCRIPTIONS)
    for column in ["plate_x", "plate_z", "sz_top", "sz_bot"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.dropna(subset=["plate_x", "plate_z", "sz_top", "sz_bot", "catcher_id"])
    height = (out["sz_top"] - out["sz_bot"]).replace(0, np.nan)
    out["z_norm"] = (out["plate_z"] - out["sz_bot"]) / height
    out = out.dropna(subset=["z_norm"])
    out["x_bin"] = pd.cut(out["plate_x"], bins=X_EDGES, labels=False, include_lowest=True)
    out["z_bin"] = pd.cut(out["z_norm"], bins=Z_EDGES, labels=False, include_lowest=True)
    out = out.dropna(subset=["x_bin", "z_bin"]).copy()
    out["x_bin"] = out["x_bin"].astype(int)
    out["z_bin"] = out["z_bin"].astype(int)
    out["zone_region"] = out.apply(zone_region, axis=1)
    return out


def zone_region(row: pd.Series) -> str:
    x_bin = int(row["x_bin"])
    z_bin = int(row["z_bin"])
    if x_bin == 3 and z_bin == 2:
        return "heart"
    if z_bin == 4:
        return "chase_top"
    if z_bin == 0:
        return "chase_bottom"
    if x_bin in (0, 1):
        return "chase_glove_side"
    if x_bin in (5, 6):
        return "chase_arm_side"
    if z_bin == 1:
        return "shadow_bottom"
    if z_bin == 3:
        return "shadow_top"
    if x_bin == 2:
        return "shadow_glove_side"
    if x_bin == 4:
        return "shadow_arm_side"
    return "heart"


def zone_grid_definition() -> dict[str, list[dict[str, object]]]:
    return {
        "x_bins": [{"index": i, "label": label} for i, label in enumerate(X_LABELS)],
        "z_bins": [{"index": i, "label": label} for i, label in enumerate(Z_LABELS)],
    }
