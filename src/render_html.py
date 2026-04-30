from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .features import prepare_statcast, prepare_workbook, zone_grid_definition
from .loaders import (
    load_catcher_workbook,
    load_config,
    load_or_pull_abs_challenges,
    load_or_build_catcher_lookup,
    load_or_pull_statcast,
    project_path,
)
from .metrics import (
    build_catcher_rows,
    build_strategy_guide,
    build_zone_rows,
    enrich_catcher_report_metrics,
    filters_from_rows,
)
from .validation import (
    validate_abs_challenges,
    validate_join_quality,
    validate_statcast,
    validate_workbook,
)


def build_payload(config: dict[str, Any]) -> dict[str, Any]:
    workbook = load_catcher_workbook(project_path(config, "workbook_path"))
    workbook = prepare_workbook(workbook)
    validations = validate_workbook(workbook)

    raw_2026, status_2026 = load_or_pull_statcast(config, 2026)
    raw_2025, status_2025 = load_or_pull_statcast(config, 2025)
    validations.extend(validate_statcast(raw_2026, 2026))
    validations.extend(validate_statcast(raw_2025, 2025))
    game_ids = raw_2026["game_pk"].dropna().astype(int).tolist() if "game_pk" in raw_2026.columns else []
    abs_challenges, abs_status = load_or_pull_abs_challenges(config, 2026, game_ids)
    validations.extend(validate_abs_challenges(abs_challenges))

    catcher_ids: list[int] = []
    for frame in [raw_2026, raw_2025]:
        if not frame.empty and "fielder_2" in frame.columns:
            catcher_ids.extend(frame["fielder_2"].dropna().astype(int).tolist())
    lookup, lookup_status = load_or_build_catcher_lookup(config, catcher_ids)

    statcast_2026 = prepare_statcast(raw_2026, 2026, lookup)
    statcast_2025 = prepare_statcast(raw_2025, 2025, lookup)
    if not statcast_2026.empty:
        validations.extend(validate_join_quality(workbook, statcast_2026))

    zone_rows = build_zone_rows(statcast_2026, statcast_2025)
    strategy = build_strategy_guide(statcast_2026, abs_challenges)
    catcher_rows = enrich_catcher_report_metrics(
        build_catcher_rows(workbook),
        statcast_2026,
        abs_challenges,
    )
    filters = filters_from_rows(catcher_rows, zone_rows)

    return {
        "generatedAt": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "config": {
            "statcast2026Start": config["statcast_2026_start_date"],
            "statcast2026End": config["statcast_2026_end_date"],
            "statcast2025Start": config["statcast_2025_start_date"],
            "statcast2025End": config["statcast_2025_end_date"],
            "refreshStatcast": bool(config.get("refresh_statcast", False)),
            "refreshAbsChallenges": bool(config.get("refresh_abs_challenges", False)),
        },
        "sourceStatus": {
            "statcast2026": status_2026,
            "statcast2025": status_2025,
            "absChallenges": abs_status,
            "catcherLookup": lookup_status,
        },
        "validations": validations,
        "catchers": catcher_rows,
        "zoneRows": zone_rows,
        "strategy": strategy,
        "zoneGrid": zone_grid_definition(),
        "filters": filters,
    }


def render(
    config_path: str | Path,
    refresh_statcast: bool | None = None,
    refresh_abs_challenges: bool | None = None,
) -> Path:
    config = load_config(config_path)
    if refresh_statcast is not None:
        config["refresh_statcast"] = refresh_statcast
    if refresh_abs_challenges is not None:
        config["refresh_abs_challenges"] = refresh_abs_challenges
    payload = build_payload(config)
    template_path = Path(config["_project_root"]) / "templates" / "dashboard.html"
    template = template_path.read_text(encoding="utf-8")
    data_json = json.dumps(payload, ensure_ascii=True, allow_nan=False)
    html = template.replace("window.__DASHBOARD_DATA__ = null;", f"window.__DASHBOARD_DATA__ = {data_json};")
    output_path = project_path(config, "output_html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ABS catcher dashboard HTML.")
    parser.add_argument(
        "--config",
        default="config/dashboard_config.json",
        help="Path to dashboard JSON config.",
    )
    parser.add_argument(
        "--refresh-statcast",
        action="store_true",
        help="Pull Statcast with pybaseball and update the local cache.",
    )
    parser.add_argument(
        "--refresh-abs-challenges",
        action="store_true",
        help="Pull MLB Stats API pitch-level ABS challenge events and update the local cache.",
    )
    args = parser.parse_args()
    output = render(
        args.config,
        refresh_statcast=True if args.refresh_statcast else None,
        refresh_abs_challenges=True if args.refresh_abs_challenges else None,
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
