# The ABS Edge Map

This project builds a single self-contained HTML dashboard for reviewing catcher ABS challenge performance from the pitching-team perspective.

The dashboard is designed for a catching coach. It opens directly in a browser and does not require Streamlit, a local server, or a separate report export.

## Inputs

Approved inputs:

- `abs-challenges-2026-catcher.xlsx`
- Pitch-level Statcast data pulled with `pybaseball.statcast`

The workbook drives the catcher challenge sections. Statcast drives the Zone Change section once cached or pulled.

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
  "refresh_statcast": false,
  "statcast_2026_start_date": "2026-03-26",
  "statcast_2026_end_date": "2026-04-24",
  "statcast_2025_start_date": "2025-03-27",
  "statcast_2025_end_date": "2025-04-25"
}
```

Use `refresh_statcast: true` only when `pybaseball` is installed and you want to pull fresh Statcast data. Otherwise the generator looks for matching cached files in `data/cache`.

## Build

```bash
python -m src.render_html --config config/dashboard_config.json
```

To pull fresh Statcast data and refresh the cache:

```bash
python -m src.render_html --config config/dashboard_config.json --refresh-statcast
```

Open:

```text
outputs/dashboard/abs_catcher_dashboard.html
```

That file is the coach-shareable deliverable.

## Dashboard Sections

1. **Zone Change**: first visible section. Shows 2026 called-strike rate changes versus a comparable 2025 window when Statcast cache is available.
2. **Catcher Overview**: ranks catchers from the workbook by challenge value, success, and aggression signal.
3. **Challenge Report Card**: gives catcher-level challenge feedback without grading only by success rate.
4. **Catcher Evaluation**: transparent MVP value formula using available challenge components.
5. **Data Check**: source, schema, and join-readiness checks.

## Metric Notes

- Challenge Success Rate = overturns / challenges.
- Overturns Above Expected = actual overturns minus expected overturns from the workbook fields.
- Aggression Label uses the workbook expected challenge rate difference.
- Called Strike Rate Change = 2026 called-strike rate minus comparable 2025 called-strike rate for taken pitches.
- ABS Catcher Value MVP = Challenge Execution Value + Challenge Selection Value + Zone Adaptation Indicator.

## Known Limitations

- The current workbook is aggregate catcher data, not challenge-level pitch data.
- Zone-specific missed opportunities are not shown until pitch-level challenge linkage is available.
- Battery process value is not shown because internal charting fields are outside the approved data scope.
- Receiving value is held out until a separate framing or receiving model is approved.
- If Statcast cache is unavailable, Zone Change shows a data-needed state instead of mock data.
