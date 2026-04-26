# AGENTS.md

## Project

The ABS Edge Map is a coach-facing, self-contained HTML dashboard for evaluating ABS-era catcher strategy from the pitching-team challenge perspective.

The primary user is a catching coach. Prioritize clarity, direct baseball language, and fast interpretation over exhaustive analysis.

## Durable Instructions

- Build a standalone HTML dashboard that can be opened from `outputs/dashboard/abs_catcher_dashboard.html` without Streamlit, a server, or an exported report.
- Use only approved data sources unless the user explicitly expands scope:
  - `abs-challenges-2026-catcher.xlsx`
  - pitch-level Statcast data pulled with `pybaseball.statcast`
  - MLB Stats API game feeds for pitch-level ABS challenge events, after validating totals against trusted aggregates
- Keep the dashboard catcher-focused. Treat catchers as the primary decision-makers for pitching-team challenges.
- Do not show mock data in coach-facing views.
- Keep Zone Change as the first visible dashboard section.
- Keep Zone Change as a league-wide educational page. Do not add team or catcher filters back to that section unless the user explicitly changes direction.
- Use a single catcher-view strike zone. Do not flip horizontal pitch location by pitcher hand or batter side.
- Use raw Statcast `plate_x` for horizontal bins and normalize only vertical pitch location by `sz_top` / `sz_bot`.
- Use Arizona Diamondbacks-inspired styling throughout the dashboard.
- Keep the approved workbook, Statcast cache files, and MLB Stats API ABS challenge cache committed for reproducibility unless the user explicitly changes the data policy.
- Keep coach-facing language practical: use terms like called-strike shape, challenge value, selection, aggression, conviction, and catcher view.
- Avoid front-facing model jargon unless it is clearly separated into data or analyst notes.
- Do not add a report/export workflow until the user asks for it.

## Product Process

- Start each material dashboard change by identifying the coach-facing question the page or section should answer.
- Before building visuals, confirm the data supports the claim. If a split is noisy, incomplete, or not decision-useful, make it a filter/drill-down or cut it.
- Separate concept, evidence, and recommendation. A good section should make clear what is theory/math, what is observed data, and what action the coach should take.
- Prefer one cohesive story over several disconnected tables. Combine related views when they answer the same decision.
- When the user gives screenshot feedback, reassess the information architecture before polishing local styling. The issue is often story structure, not just spacing.
- Treat user-approved patterns as reusable only after they serve a broader dashboard purpose. Do not turn one-off comments into permanent rules unless they generalize.
- Keep coach-facing sections practical and concise; move data caveats and methodology detail into tooltips, compact notes, or Data Check.

## Visual And Interaction Standards

- Use compact visual encodings such as bars, small multiples, selectable areas, and direct labels when they reduce table-reading burden.
- Tooltips should be short stat panels with differentiated metrics and minimal prose.
- Default views must be understandable without hover. Hover and click should add detail, not rescue an unclear chart.
- Interactive controls must update all related visuals, legends, counts, and summary stats together.
- Strike-zone visuals should use a consistent catcher-view orientation and proportions that preserve baseball intuition.

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
