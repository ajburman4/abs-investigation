---
name: dashboard-visual-review
description: Review The ABS Edge Map dashboard for styling, formatting, story clarity, visual simplicity, tooltip quality, and user experience. Use when asked to inspect screenshots, address browser annotations, refine coach-facing storytelling, or make dashboard visuals cleaner and easier to interpret.
---

# Dashboard Visual Review

Use this workflow to review the generated dashboard as a coach-facing product. Focus on whether the page tells the right baseball story with clean visuals, clear hierarchy, and low cognitive load.

## Start With The Current Artifact

Review:

```text
outputs/dashboard/abs_catcher_dashboard.html
```

If code, template, or data changed, rebuild first. Do not spend review effort on stale HTML.

Primary rebuild command:

```bash
python -m src.render_html --config config/dashboard_config.json
```

## Review Priorities

Evaluate in this order:

1. What is the page trying to say, and is that story obvious within a few seconds?
2. Does the visual hierarchy guide the coach from thesis to evidence to detail?
3. Are the visuals simple enough to read without explanation?
4. Do cards, tables, legends, and tooltips add interpretation rather than clutter?
5. Are labels and baseball terms concrete, coach-facing, and consistent?
6. Does the layout feel polished at desktop and narrow widths?
7. Does the page use Arizona Diamondbacks-inspired styling consistently without overwhelming the data?

## Analysis Review

For analytical dashboard pages, identify three layers before judging the visuals:

- **Concept**: the theory, model, rule, or baseball idea.
- **Evidence**: the observed data supporting or challenging that concept.
- **Recommendation**: the coach-facing action, risk, or interpretation.

Good pages keep those layers connected but not muddled. If a section mixes them without explaining the relationship, recommend restructuring before visual polish.

Checklist:

- Confirm the data supports the claim being made.
- Treat noisy or non-decisive splits as filters, drill-downs, or cuts.
- Prefer visuals that answer one decision quickly over tables that require the coach to assemble the story.
- Make constraints explicit when they change the recommendation.
- Avoid adding situational language unless the visual shows where and why the situation matters.

## Story Review

- Identify the page thesis before critiquing components.
- Prefer one strong thesis with a few supporting metrics over scattered observations.
- Remove or rewrite copy that repeats numbers already shown in cards or tables.
- Make supporting cards visually distinct and useful; avoid bland metric blocks that only restate labels.
- Keep coach-facing wording direct. Prefer `Top-zone calls are expanding` over abstract descriptions.
- Do not add explanatory text that describes obvious UI mechanics.
- Cut sections that are technically interesting but do not change the coach's decision.

## Visual Simplicity

- Use the fewest visual encodings needed to explain the point.
- Make legends visually connected to the chart they explain.
- Use color intentionally: gained/lost, positive/negative, selected/unselected, or priority/status.
- Keep chart labels short and oriented to the coach's view.
- Avoid dense grids, over-labeled cells, and tables with notes that do not add insight.
- Keep whitespace, alignment, and sizing consistent across sections.
- When comparing counts or recommendations, use compact bars with readable labels and values.
- Make strike-zone visuals square or proportioned like a normal zone; avoid wide plots that distort baseball intuition.
- Do not use separate tables when a clickable/selectable visual can show the same relationship more directly.

## Tooltips And Interaction

- Use tooltips for detail-on-demand: before/after rates, deltas, sample context, and secondary metrics.
- Keep tooltip text short, scannable, and formatted like a small stat panel.
- Keep key values on one line when possible.
- Make hover/click states visually distinct from permanent chart outlines.
- Default views should be understandable without requiring interaction.
- Selection behavior should be reversible and obvious when selected.
- For analytical tooltips, lead with the critical metrics, then add only the shortest useful context. Avoid paragraph tooltips.
- Use larger differentiated metric values in tooltips, similar to the Zone Detail pattern.
- For selectable groups, allow deselection, update summary stats, and make selected/unselected states visually clear without hiding the data.

## Browser QA

When layout or interaction changed:

- Reload the standalone HTML in the browser.
- Check desktop width and a narrow/mobile width when practical.
- Hover a zone cell and confirm tooltip formatting is readable.
- Select and unselect an area in the Area Guide if that interaction is present.
- On any interactive page, hover the main chart marks, click selectable groups, and test filters/toggles.
- Confirm visible counts, plots, legends, and summaries update together.
- Confirm text does not overlap, truncate awkwardly, or wrap important values.
- Confirm the page still reads as a finished coaching product, not a data dump.

## Feedback Handling

- Treat screenshot annotations as task feedback, not automatic permanent project rules.
- Promote a preference into `AGENTS.md` or `PROJECT_BRIEF.md` only when the user confirms it as durable.
- Keep one-off visual tweaks in the implementation, not in permanent instructions.
- If the user says a section does not pass the gut check, verify the data path and visual encoding before polishing the design.
- If a split has no meaningful signal, remove it or turn it into a filter rather than defending a weak section.
