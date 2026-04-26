from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config["_config_path"] = str(path)
    config["_project_root"] = str(path.resolve().parents[1])
    return config


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
    status: dict[str, Any] = {
        "season": season,
        "start_date": config[f"statcast_{season}_start_date"],
        "end_date": config[f"statcast_{season}_end_date"],
        "cache_path": str(cache_path),
        "source": "missing",
        "message": "",
    }

    if cache_path.exists() and not config.get("refresh_statcast", False):
        df = pd.read_csv(cache_path, low_memory=False)
        status["source"] = "cache"
        status["message"] = f"Loaded cached Statcast data for {season}."
        status["rows"] = int(len(df))
        return df, status

    if not config.get("refresh_statcast", False):
        status["message"] = (
            "No cached Statcast file found. Set refresh_statcast to true after "
            "installing pybaseball, or place a matching cache file in data/cache."
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
