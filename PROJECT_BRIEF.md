# Project Brief: The ABS Edge Map

## Summary

The ABS Edge Map is a single-file HTML dashboard for helping catching coaches understand how the ABS challenge era changes catcher value. It focuses on the pitching-team challenge perspective: how catchers read the new zone, choose when to challenge, and create or lose challenge value.

The dashboard is meant to be emailed or shared as a file. It should open directly in a browser without Streamlit, a local server, or a separate generated report.

## Audience

Primary audience:

- MLB catching coach

Secondary audience:

- Baseball operations analysts
- Pitching coaches
- Player development staff

The catching coach should be able to understand the page without needing a statistics explanation.

## Product Message

ABS does not remove catcher value. It changes catcher value from simply receiving pitches into managing the full strike-zone decision process:

- understanding the new called-strike shape
- receiving and presenting the pitch
- communicating conviction to the pitcher
- choosing when a challenge is worth using
- learning from challenge outcomes
- adjusting catcher/pitcher strategy going forward

## Current Scope

Approved inputs:

- `abs-challenges-2026-catcher.xlsx`
- pitch-level Statcast from `pybaseball.statcast`
- MLB Stats API game feeds for pitch-level ABS challenge events

The approved workbook, Statcast cache files, and MLB Stats API ABS challenge cache should remain committed so future rebuilds are reproducible without immediately re-pulling public data.

Current output:

- `outputs/dashboard/abs_catcher_dashboard.html`

Current sections:

1. Strike Zone Change
2. Challenge Strategy
3. Challenge Report Card

Out of scope for now:

- Streamlit
- exported PDF/PowerPoint/report workflows
- mock coach-facing data
- true missed-opportunity modeling beyond validated public pitch-level challenge linkage
- battery process value without internal charting fields
- receiving value until a separate receiving/framing model is approved

## Data Model

The workbook drives catcher-level challenge sections. Statcast drives the Strike Zone Change section and the run-value context for challenge strategy. MLB Stats API review details drive observed pitch-level challenge summaries.

The Statcast zone view is intentionally static from the catcher perspective:

- `plate_x` is not flipped by pitcher hand or batter side.
- Horizontal labels should refer to field orientation, not pitcher arm/glove side.
- Vertical location is normalized with `sz_top` and `sz_bot` so hitter height differences do not dominate the view.
- `fielder_2` is the catcher identifier.

The workbook is aggregate catcher data, so challenge results are not currently linked to individual pitch-zone cells.

Pitch-level ABS challenge events from MLB Stats API are useful but should be treated as validated public event data, not as a black box. When they are used in a coach-facing view, reconcile broad counts against trusted aggregate sources when possible and make the view descriptive unless the analysis has been validated as predictive.

## Page Intent

### 1. Strike Zone Change

Purpose: teach the league-wide called-strike shape under ABS compared with a comparable prior human-zone window.

Durable requirements:

- This page appears first.
- It should be educational, not a filter-heavy exploration page.
- It should remain a league-wide view; do not add team or catcher filters back to this page.
- It should use a catcher-view strike-zone visual.
- It should show called-strike rate changes by zone.
- It should allow coaches to inspect area-level called-strike rates before and after.
- It should not display zone-level challenge metrics until challenge data can be linked to pitch location.

Current thesis:

> The strike zone is getting more vertical, with more called strikes above and below the historical zone. Umpire biases or leniency on the edges is being removed by challenges.

### 2. Challenge Strategy

Purpose: give coaches a practical guide for when a catcher should ask for a pitching-team challenge.

This page should separate and then connect strategy inputs:

- the value of being right
- the cost of being wrong
- how many challenges remain
- observed evidence that a location or situation is actually reviewable

Include:

- count-based run swing
- conviction required
- challenge inventory, with only `2 left` and `1 left` states
- game-state context where it changes the decision
- catcher-view location evidence for challenge outcomes
- observed pitch-level challenge counts and overturn rates once MLB Stats API events are cached and joined
- pitch type or other splits as filters/drill-downs unless there is a clear standalone signal

Core rule:

> Challenge when catcher conviction is higher than the situation's required confidence.

Use the Savant breakeven idea:

```text
confidence required = 0.20 / (0.20 + run value of the call)
```

In the current dashboard, `0.20` is the estimated cost of losing a challenge when the team still has two challenges. With one challenge left, the model can add a last-challenge premium from observed future overturned challenge value. Explain this plainly: one left raises the bar because missing costs more.

Do not turn this into a black-box optimizer. Keep the page focused on selection, aggression, conviction, game situation, and the location evidence that creates confidence.

### 3. Challenge Report Card

Purpose: evaluate catcher challenge quality without grading only by success rate.

Use workbook fields for:

- challenges used
- successful challenges
- success rate
- expected success rate
- net challenge value
- overturns above or below expected
- aggression label

Do not include zone-specific missed opportunities until pitch-level challenge linkage exists.

## Visual And Language Guidance

- Use direct baseball language.
- Frame page and section titles around the decision or question the coach needs answered, not around internal report structure.
- Prefer one clear thesis per page over many small observations.
- Keep repeated insight labels short and consistent so coaches can scan the same pattern across sections.
- Do not overexplain obvious UI mechanics in the page copy.
- Avoid statistical jargon in coach-facing text.
- Keep tables and metrics short enough to scan.
- Label rates so the outcome is explicit. When showing `count / percentage`, make clear whether the percentage is successful, overturned, selected, expected, or another denominator.
- Use color to support interpretation, not as decoration.
- Use Arizona Diamondbacks-inspired styling throughout.
- If area names are shown on a catcher-view zone, prefer field-orientation language such as `Third-base side` and `First-base side`.
- Use compact visual encodings when the task is comparison. Avoid large tables unless they are the clearest way to answer the coach's question.
- Tooltips should behave like small stat panels: large differentiated values, short labels, and only the key context needed to interpret the hover target.
- Do not use tooltips to restate labels, colors, or recommendations already visible on the mark. Tooltips should add useful context or a second-level metric.
- When explaining a calculation, prefer a compact source/formula/example structure over a dense prose paragraph.
- Cut sections that do not add a decision insight. If a split does not show a clear signal, make it a filter or remove it from the coach-facing story.
- Keep concept, observed evidence, and recommendation connected but visually distinct.

## Working Process

When evolving the dashboard, use this loop:

1. Define the coach-facing decision or takeaway.
2. Verify the approved data can support it.
3. Choose the simplest visual form that makes the decision faster.
4. Add interaction only when it clarifies evidence or enables useful drill-down.
5. Rebuild and review the generated HTML in the browser.

If feedback says a section is confusing, first revisit the story and grouping. Avoid responding with isolated copy or styling changes when the underlying issue is that the view mixes concepts, duplicates another section, or makes a weak data claim.

When feedback removes or simplifies a section, look for the broader pattern before updating durable guidance. Promote only reusable preferences such as clearer denominators, shorter tooltip panels, better section jobs, or less UI-instruction copy.

## Implementation Shape

Current structure:

```text
config/dashboard_config.json
src/loaders.py
src/validation.py
src/features.py
src/metrics.py
src/render_html.py
templates/dashboard.html
data/cache/
outputs/dashboard/abs_catcher_dashboard.html
```

Build command:

```bash
python -m src.render_html --config config/dashboard_config.json
```

Refresh Statcast cache intentionally:

```bash
python -m src.render_html --config config/dashboard_config.json --refresh-statcast
```
