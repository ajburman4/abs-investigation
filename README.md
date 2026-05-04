# The ABS Edge Map

This project builds a single self-contained HTML dashboard for reviewing catcher ABS challenge performance from the pitching-team perspective.

The dashboard is designed for a catching coach. It opens directly in a browser and does not require Streamlit, a local server, or a separate report export.

## Inputs

Approved inputs:

- `abs-challenges-2026-catcher.xlsx`
- Pitch-level Statcast data pulled with `pybaseball.statcast`
- MLB Stats API game feeds for pitch-level ABS challenge events

The workbook drives catcher-level challenge baselines. Statcast drives the Strike Zone Change and strategy context sections once cached or pulled. MLB Stats API feeds provide pitch-level ABS challenge events, cached locally for reproducibility.

## Setup

Install dependencies in the environment you use to build the file:

```bash
pip install -r requirements.txt
```

The current local bundled runtime already includes `pandas` and `openpyxl`, so the workbook-backed sections can be built without pulling Statcast.

## Configuration

Edit `config/dashboard_config.json`:

```json
{
  "workbook_path": "abs-challenges-2026-catcher.xlsx",
  "cache_dir": "data/cache",
  "output_html": "outputs/dashboard/abs_catcher_dashboard.html",
  "data_timezone": "America/Phoenix",
  "current_statcast_season": 2026,
  "historical_statcast_refresh": "missing_only",
  "refresh_statcast": false,
  "refresh_abs_challenges": false,
  "statcast_2026_start_date": "2026-03-26",
  "statcast_2026_end_date": "latest_complete_day",
  "statcast_2025_start_date": "2025-03-27",
  "statcast_2025_end_date": "2025-09-28"
}
```

`latest_complete_day` resolves to yesterday in `data_timezone`, which avoids partial same-day Statcast or review-feed data. The 2025 dates are a fixed full prior-season regular-season called-strike baseline.

`current_statcast_season` is the season refreshed by `--refresh-statcast`. Historical Statcast, such as the 2025 baseline, defaults to `missing_only`: the pipeline creates the missing full-season cache once, then reuses it because the completed-season data should not change.

Use `refresh_statcast: true` only when `pybaseball` is installed and you want to pull fresh Statcast data. Otherwise the generator looks for matching cached files in `data/cache`.

Use `refresh_abs_challenges: true` or `--refresh-abs-challenges` only when intentionally updating the MLB Stats API ABS challenge cache.

## Build

```bash
python -m src.render_html --config config/dashboard_config.json
```

To pull fresh Statcast data and refresh the cache:

```bash
python -m src.render_html --config config/dashboard_config.json --refresh-statcast
```

To refresh pitch-level ABS challenge events from MLB Stats API:

```bash
python -m src.render_html --config config/dashboard_config.json --refresh-abs-challenges
```

To update the dashboard with the latest complete current-season data in one run:

```bash
python -m src.render_html --config config/dashboard_config.json --refresh-statcast --refresh-abs-challenges
```

Open:

```text
outputs/dashboard/abs_catcher_dashboard.html
```

That file is the coach-shareable deliverable.

## Dashboard Sections

1. **Strike Zone Change**: first visible section. Shows 2026 called-strike rate changes versus a comparable 2025 window when Statcast cache is available.
2. **Challenge Strategy**: count, situation, location, and observed pitch-level challenge guide for when to spend a pitching-team challenge.
3. **Challenge Report Card**: gives catcher-level challenge feedback without grading only by success rate.

## Metric Notes

- Challenge Success Rate = overturns / challenges.
- Overturns Above Expected = actual overturns minus expected overturns from the workbook fields.
- Aggression Label uses the workbook expected challenge rate difference.
- Called Strike Rate Change = 2026 called-strike rate minus comparable 2025 called-strike rate for taken pitches.
- Strategy Run Swing = 2026 Statcast batting run expectancy on called balls minus called strikes for the same count.
- Conviction Needed = `0.20 / (0.20 + Strategy Run Swing)`.
- ABS Catcher Value MVP = Challenge Execution Value + Challenge Selection Value + Zone Adaptation Indicator.

## Known Limitations

- The current workbook is aggregate catcher data, not challenge-level pitch data.
- Pitch-level challenge events are extracted from MLB Stats API review details and should be reconciled against Baseball Savant aggregate totals before being used as a final grading source.
- Battery process value is not shown because internal charting fields are outside the approved data scope.
- Receiving value is held out until a separate framing or receiving model is approved.
- If Statcast cache is unavailable, Strike Zone Change shows a data-needed state instead of mock data.
