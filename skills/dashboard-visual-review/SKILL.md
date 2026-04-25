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

If code, template, or data changed, rebuild first with the `build-dashboard` workflow. Do not spend review effort on stale HTML.

## Review Priorities

Evaluate in this order:

1. What is the page trying to say, and is that story obvious within a few seconds?
2. Does the visual hierarchy guide the coach from thesis to evidence to detail?
3. Are the visuals simple enough to read without explanation?
4. Do cards, tables, legends, and tooltips add interpretation rather than clutter?
5. Are labels and baseball terms concrete, coach-facing, and consistent?
6. Does the layout feel polished at desktop and narrow widths?
7. Does the page use Arizona Diamondbacks-inspired styling consistently without overwhelming the data?

## Story Review

- Identify the page thesis before critiquing components.
- Prefer one strong thesis with a few supporting metrics over scattered observations.
- Remove or rewrite copy that repeats numbers already shown in cards or tables.
- Make supporting cards visually distinct and useful; avoid bland metric blocks that only restate labels.
- Keep coach-facing wording direct. Prefer `Top-zone calls are expanding` over abstract descriptions.
- Do not add explanatory text that describes obvious UI mechanics.

## Visual Simplicity

- Use the fewest visual encodings needed to explain the point.
- Make legends visually connected to the chart they explain.
- Use color intentionally: gained/lost, positive/negative, selected/unselected, or priority/status.
- Keep chart labels short and oriented to the coach's view.
- Avoid dense grids, over-labeled cells, and tables with notes that do not add insight.
- Keep whitespace, alignment, and sizing consistent across sections.

## Tooltips And Interaction

- Use tooltips for detail-on-demand: before/after rates, deltas, sample context, and secondary metrics.
- Keep tooltip text short, scannable, and formatted like a small stat panel.
- Keep key values on one line when possible.
- Make hover/click states visually distinct from permanent chart outlines.
- Default views should be understandable without requiring interaction.
- Selection behavior should be reversible and obvious when selected.

## Browser QA

When layout or interaction changed:

- Reload the standalone HTML in the browser.
- Check desktop width and a narrow/mobile width when practical.
- Hover a zone cell and confirm tooltip formatting is readable.
- Select and unselect an area in the Area Guide if that interaction is present.
- Confirm text does not overlap, truncate awkwardly, or wrap important values.
- Confirm the page still reads as a finished coaching product, not a data dump.

## Feedback Handling

- Treat screenshot annotations as task feedback, not automatic permanent project rules.
- Promote a preference into `AGENTS.md` or `PROJECT_BRIEF.md` only when the user confirms it as durable.
- Keep one-off visual tweaks in the implementation, not in permanent instructions.
