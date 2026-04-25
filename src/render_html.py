from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .features import prepare_statcast, prepare_workbook, zone_grid_definition
from .loaders import (
    load_catcher_workbook,
    load_config,
    load_or_build_catcher_lookup,
    load_or_pull_statcast,
    project_path,
)
from .metrics import build_catcher_rows, build_zone_rows, filters_from_rows
from .validation import validate_join_quality, validate_statcast, validate_workbook


def build_payload(config: dict[str, Any]) -> dict[str, Any]:
    workbook = load_catcher_workbook(project_path(config, "workbook_path"))
    workbook = prepare_workbook(workbook)
    validations = validate_workbook(workbook)

    raw_2026, status_2026 = load_or_pull_statcast(config, 2026)
    raw_2025, status_2025 = load_or_pull_statcast(config, 2025)
    validations.extend(validate_statcast(raw_2026, 2026))
    validations.extend(validate_statcast(raw_2025, 2025))

    catcher_ids: list[int] = []
    for frame in [raw_2026, raw_2025]:
        if not frame.empty and "fielder_2" in frame.columns:
            catcher_ids.extend(frame["fielder_2"].dropna().astype(int).tolist())
    lookup, lookup_status = load_or_build_catcher_lookup(config, catcher_ids)

    statcast_2026 = prepare_statcast(raw_2026, 2026, lookup)
    statcast_2025 = prepare_statcast(raw_2025, 2025, lookup)
    if not statcast_2026.empty:
        validations.extend(validate_join_quality(workbook, statcast_2026))

    catcher_rows = build_catcher_rows(workbook)
    zone_rows = build_zone_rows(statcast_2026, statcast_2025)
    filters = filters_from_rows(catcher_rows, zone_rows)

    return {
        "generatedAt": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "config": {
            "statcast2026Start": config["statcast_2026_start_date"],
            "statcast2026End": config["statcast_2026_end_date"],
            "statcast2025Start": config["statcast_2025_start_date"],
            "statcast2025End": config["statcast_2025_end_date"],
            "refreshStatcast": bool(config.get("refresh_statcast", False)),
        },
        "sourceStatus": {
            "statcast2026": status_2026,
            "statcast2025": status_2025,
            "catcherLookup": lookup_status,
        },
        "validations": validations,
        "catchers": catcher_rows,
        "zoneRows": zone_rows,
        "zoneGrid": zone_grid_definition(),
        "filters": filters,
    }


def render(config_path: str | Path, refresh_statcast: bool | None = None) -> Path:
    config = load_config(config_path)
    if refresh_statcast is not None:
        config["refresh_statcast"] = refresh_statcast
    payload = build_payload(config)
    template_path = Path(config["_project_root"]) / "templates" / "dashboard.html"
    template = template_path.read_text(encoding="utf-8")
    data_json = json.dumps(payload, ensure_ascii=True, allow_nan=False)
    html = template.replace("__DASHBOARD_DATA__", data_json)
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
    args = parser.parse_args()
    output = render(args.config, refresh_statcast=True if args.refresh_statcast else None)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
