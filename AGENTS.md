# AGENTS.md

## Project

The ABS Edge Map is a coach-facing, self-contained HTML dashboard for evaluating ABS-era catcher strategy from the pitching-team challenge perspective.

The primary user is a catching coach. Prioritize clarity, direct baseball language, and fast interpretation over exhaustive analysis.

## Durable Instructions

- Build a standalone HTML dashboard that can be opened from `outputs/dashboard/abs_catcher_dashboard.html` without Streamlit, a server, or an exported report.
- Use only approved data sources unless the user explicitly expands scope:
  - `abs-challenges-2026-catcher.xlsx`
  - pitch-level Statcast data pulled with `pybaseball.statcast`
- Keep the dashboard catcher-focused. Treat catchers as the primary decision-makers for pitching-team challenges.
- Do not show mock data in coach-facing views.
- Keep Zone Change as the first visible dashboard section.
- Keep Zone Change as a league-wide educational page. Do not add team or catcher filters back to that section unless the user explicitly changes direction.
- Use a single catcher-view strike zone. Do not flip horizontal pitch location by pitcher hand or batter side.
- Use raw Statcast `plate_x` for horizontal bins and normalize only vertical pitch location by `sz_top` / `sz_bot`.
- Use Arizona Diamondbacks-inspired styling throughout the dashboard.
- Keep the approved workbook and Statcast cache files committed for reproducibility unless the user explicitly changes the data policy.
- Keep coach-facing language practical: use terms like called-strike shape, challenge value, selection, aggression, conviction, and catcher view.
- Avoid front-facing model jargon unless it is clearly separated into data or analyst notes.
- Do not add a report/export workflow until the user asks for it.

## Build And Validation

Primary build command:

```bash
python -m src.render_html --config config/dashboard_config.json
```

Use `--refresh-statcast` only when intentionally updating the Statcast cache.

Before handing off dashboard changes:

- Rebuild `outputs/dashboard/abs_catcher_dashboard.html`.
- Run Python compile checks on `src`.
- Check generated dashboard JavaScript syntax.
- Open or reload the generated HTML in a browser when layout changed.
