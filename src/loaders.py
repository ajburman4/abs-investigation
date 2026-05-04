from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _date_string(value: date) -> str:
    return value.isoformat()


def _today(config: dict[str, Any]) -> date:
    timezone = str(config.get("data_timezone", "America/Phoenix"))
    return datetime.now(ZoneInfo(timezone)).date()


def _resolve_date_token(config: dict[str, Any], value: str) -> str:
    token = value.strip().lower()
    if token in {"latest_complete_day", "yesterday"}:
        return _date_string(_today(config) - timedelta(days=1))
    if token == "today":
        return _date_string(_today(config))
    return value


def resolve_date_config(config: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(config)
    raw_dates = {
        key: resolved.get(key)
        for key in [
            "statcast_2026_start_date",
            "statcast_2026_end_date",
            "statcast_2025_start_date",
            "statcast_2025_end_date",
        ]
    }

    for key in ["statcast_2026_start_date", "statcast_2026_end_date", "statcast_2025_start_date"]:
        resolved[key] = _resolve_date_token(resolved, str(resolved[key]))

    comparison_end = str(resolved["statcast_2025_end_date"]).strip().lower()
    if comparison_end in {"match_2026_window", "match_current_window", "same_elapsed_days"}:
        current_days = _parse_date(resolved["statcast_2026_end_date"]) - _parse_date(
            resolved["statcast_2026_start_date"]
        )
        resolved["statcast_2025_end_date"] = _date_string(
            _parse_date(resolved["statcast_2025_start_date"]) + current_days
        )
    else:
        resolved["statcast_2025_end_date"] = _resolve_date_token(
            resolved, str(resolved["statcast_2025_end_date"])
        )

    for season in [2026, 2025]:
        start = _parse_date(resolved[f"statcast_{season}_start_date"])
        end = _parse_date(resolved[f"statcast_{season}_end_date"])
        if end < start:
            raise ValueError(f"statcast_{season}_end_date must be on or after statcast_{season}_start_date")

    comparison_window = (
        "2025 uses a fixed full prior-season regular-season baseline."
        if str(raw_dates["statcast_2025_end_date"]).strip().lower()
        not in {"match_2026_window", "match_current_window", "same_elapsed_days"}
        else "2025 end date matches the elapsed days in the 2026 window."
    )
    resolved["_raw_dates"] = raw_dates
    resolved["_date_policy"] = {
        "timezone": str(resolved.get("data_timezone", "America/Phoenix")),
        "latest_complete_day": _date_string(_today(resolved) - timedelta(days=1)),
        "comparison_window": comparison_window,
    }
    return resolved


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config["_config_path"] = str(path)
    config["_project_root"] = str(path.resolve().parents[1])
    return resolve_date_config(config)


def project_path(config: dict[str, Any], key: str) -> Path:
    root = Path(config["_project_root"])
    return root / str(config[key])


def load_catcher_workbook(workbook_path: str | Path) -> pd.DataFrame:
    path = Path(workbook_path)
    if not path.exists():
        raise FileNotFoundError(f"Catcher workbook not found: {path}")
    if path.name.startswith("~$"):
        raise ValueError(f"Refusing to read Excel lock file: {path}")
    return pd.read_excel(path)


def statcast_cache_path(config: dict[str, Any], season: int) -> Path:
    cache_dir = project_path(config, "cache_dir")
    start = config[f"statcast_{season}_start_date"]
    end = config[f"statcast_{season}_end_date"]
    return cache_dir / f"statcast_{season}_{start}_{end}.csv.gz"


def abs_challenge_cache_path(config: dict[str, Any], season: int) -> Path:
    cache_dir = project_path(config, "cache_dir")
    start = config[f"statcast_{season}_start_date"]
    end = config[f"statcast_{season}_end_date"]
    return cache_dir / f"abs_challenges_statsapi_{season}_{start}_{end}.csv"


def load_or_pull_statcast(config: dict[str, Any], season: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    cache_path = statcast_cache_path(config, season)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    refresh_requested = bool(config.get("refresh_statcast", False))
    current_season = int(config.get("current_statcast_season", 2026))
    historical_refresh = str(config.get("historical_statcast_refresh", "missing_only")).strip().lower()
    status: dict[str, Any] = {
        "season": season,
        "start_date": config[f"statcast_{season}_start_date"],
        "end_date": config[f"statcast_{season}_end_date"],
        "cache_path": str(cache_path),
        "source": "missing",
        "message": "",
    }

    should_pull = refresh_requested and (
        season == current_season
        or historical_refresh == "always"
        or (historical_refresh == "missing_only" and not cache_path.exists())
    )

    if cache_path.exists() and not should_pull:
        df = pd.read_csv(cache_path, low_memory=False)
        status["source"] = "cache"
        if refresh_requested and season != current_season:
            status["message"] = (
                f"Loaded cached historical Statcast data for {season}; "
                f"historical_statcast_refresh={historical_refresh}."
            )
        else:
            status["message"] = f"Loaded cached Statcast data for {season}."
        status["rows"] = int(len(df))
        return df, status

    if not should_pull:
        status["message"] = (
            "No cached Statcast file found for this resolved date window. Set "
            "refresh_statcast to true after installing pybaseball, allow historical "
            "missing-only refreshes, or place a matching cache file in data/cache."
        )
        status["rows"] = 0
        return pd.DataFrame(), status

    try:
        from pybaseball import statcast
    except ImportError:
        status["message"] = (
            "pybaseball is not installed in this runtime. Install requirements.txt "
            "or use an existing Statcast cache."
        )
        status["rows"] = 0
        return pd.DataFrame(), status

    try:
        df = statcast(status["start_date"], status["end_date"])
    except Exception as exc:  # pybaseball surfaces network and Savant errors broadly.
        status["message"] = f"Statcast pull failed: {type(exc).__name__}: {exc}"
        status["rows"] = 0
        return pd.DataFrame(), status
    df.to_csv(cache_path, index=False, compression="gzip")
    status["source"] = "pybaseball"
    status["message"] = f"Pulled Statcast data for {season} and wrote cache."
    status["rows"] = int(len(df))
    return df, status


def _team_ids_from_game(payload: dict[str, Any]) -> dict[str, int | None]:
    teams = payload.get("gameData", {}).get("teams", {})
    return {
        "home": teams.get("home", {}).get("id"),
        "away": teams.get("away", {}).get("id"),
    }


def _fetch_game_feed(game_pk: int) -> dict[str, Any]:
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    request = urllib.request.Request(url, headers={"User-Agent": "abs-edge-map/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _challenge_rows_from_game(game_pk: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    team_ids = _team_ids_from_game(payload)
    rows: list[dict[str, Any]] = []
    for play in payload.get("liveData", {}).get("plays", {}).get("allPlays", []):
        about = play.get("about", {})
        at_bat_index = about.get("atBatIndex")
        if at_bat_index is None:
            continue
        is_top = bool(about.get("isTopInning"))
        batting_team_id = team_ids["away"] if is_top else team_ids["home"]
        fielding_team_id = team_ids["home"] if is_top else team_ids["away"]
        for event in play.get("playEvents", []):
            details = event.get("details") or {}
            review = event.get("reviewDetails") or details.get("reviewDetails")
            if not review and not details.get("hasReview"):
                continue
            challenge_team_id = review.get("challengeTeamId") if review else None
            challenge_side = "unknown"
            if challenge_team_id == batting_team_id:
                challenge_side = "batting"
            elif challenge_team_id == fielding_team_id:
                challenge_side = "fielding"
            player = review.get("player", {}) if review else {}
            count = event.get("count") or {}
            call = details.get("call") or {}
            rows.append(
                {
                    "game_pk": int(game_pk),
                    "at_bat_index": int(at_bat_index),
                    "at_bat_number": int(at_bat_index) + 1,
                    "event_index": event.get("index"),
                    "pitch_number": event.get("pitchNumber"),
                    "play_id": event.get("playId"),
                    "call_description": call.get("description") or details.get("description"),
                    "balls_after_pitch": count.get("balls"),
                    "strikes_after_pitch": count.get("strikes"),
                    "outs_after_pitch": count.get("outs"),
                    "abs_overturned": bool(review.get("isOverturned")) if review else None,
                    "abs_in_progress": bool(review.get("inProgress")) if review else None,
                    "review_type": review.get("reviewType") if review else None,
                    "challenge_team_id": challenge_team_id,
                    "batting_team_id": batting_team_id,
                    "fielding_team_id": fielding_team_id,
                    "challenge_side": challenge_side,
                    "abs_player_id": player.get("id"),
                    "abs_player_name": player.get("fullName"),
                }
            )
    return rows


def load_or_pull_abs_challenges(
    config: dict[str, Any], season: int, game_ids: list[int]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    cache_path = abs_challenge_cache_path(config, season)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {
        "season": season,
        "cache_path": str(cache_path),
        "source": "missing",
        "message": "",
        "rows": 0,
        "games": 0,
    }
    if cache_path.exists() and not config.get("refresh_abs_challenges", False):
        df = pd.read_csv(cache_path)
        status.update(
            source="cache",
            message=f"Loaded cached MLB Stats API ABS challenge events for {season}.",
            rows=int(len(df)),
            games=int(df["game_pk"].nunique()) if "game_pk" in df.columns and not df.empty else 0,
        )
        return df, status

    ids = sorted({int(game_id) for game_id in game_ids if pd.notna(game_id)})
    if not ids:
        status["message"] = "No Statcast game IDs were available for ABS challenge extraction."
        return pd.DataFrame(), status

    if not config.get("refresh_abs_challenges", False):
        status["message"] = (
            "No cached MLB Stats API ABS challenge file found. Rebuild with "
            "--refresh-abs-challenges to create it."
        )
        return pd.DataFrame(), status

    rows: list[dict[str, Any]] = []
    failures = 0
    for index, game_pk in enumerate(ids):
        try:
            rows.extend(_challenge_rows_from_game(game_pk, _fetch_game_feed(game_pk)))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            failures += 1
        if index and index % 25 == 0:
            time.sleep(0.2)

    columns = [
        "game_pk",
        "at_bat_index",
        "at_bat_number",
        "event_index",
        "pitch_number",
        "play_id",
        "call_description",
        "balls_after_pitch",
        "strikes_after_pitch",
        "outs_after_pitch",
        "abs_overturned",
        "abs_in_progress",
        "review_type",
        "challenge_team_id",
        "batting_team_id",
        "fielding_team_id",
        "challenge_side",
        "abs_player_id",
        "abs_player_name",
    ]
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(cache_path, index=False)
    status.update(
        source="mlb_stats_api",
        message=(
            f"Pulled ABS challenge events from {len(ids) - failures:,} MLB game feeds"
            + (f"; {failures:,} feeds failed." if failures else ".")
        ),
        rows=int(len(df)),
        games=int(df["game_pk"].nunique()) if not df.empty else 0,
    )
    return df, status


def load_or_build_catcher_lookup(
    config: dict[str, Any], catcher_ids: list[int]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    cache_dir = project_path(config, "cache_dir")
    lookup_path = cache_dir / "catcher_lookup.csv"
    status: dict[str, Any] = {
        "cache_path": str(lookup_path),
        "source": "missing",
        "message": "",
        "rows": 0,
    }
    if lookup_path.exists():
        lookup = pd.read_csv(lookup_path)
        status.update(
            source="cache",
            message="Loaded catcher ID lookup from cache.",
            rows=int(len(lookup)),
        )
        return lookup, status

    ids = sorted({int(c) for c in catcher_ids if pd.notna(c)})
    if not ids:
        status["message"] = "No Statcast catcher IDs were available for lookup."
        return pd.DataFrame(columns=["mlbam_id", "catcher_name"]), status

    try:
        from pybaseball import playerid_reverse_lookup
    except ImportError:
        status["message"] = (
            "pybaseball is not installed, so catcher ID lookup could not be built."
        )
        return pd.DataFrame(columns=["mlbam_id", "catcher_name"]), status

    lookup = playerid_reverse_lookup(ids, key_type="mlbam")
    if lookup.empty:
        status["message"] = "pybaseball returned an empty catcher lookup."
        return pd.DataFrame(columns=["mlbam_id", "catcher_name"]), status

    lookup = lookup.rename(columns={"key_mlbam": "mlbam_id"}).copy()
    lookup["catcher_name"] = (
        lookup.get("name_first", "").fillna("").astype(str).str.strip()
        + " "
        + lookup.get("name_last", "").fillna("").astype(str).str.strip()
    ).str.strip()
    lookup = lookup[["mlbam_id", "catcher_name"]].drop_duplicates()
    lookup.to_csv(lookup_path, index=False)
    status.update(
        source="pybaseball",
        message="Built catcher ID lookup with pybaseball.",
        rows=int(len(lookup)),
    )
    return lookup, status
