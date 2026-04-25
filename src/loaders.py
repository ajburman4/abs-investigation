from __future__ import annotations

import json
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
