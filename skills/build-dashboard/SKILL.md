---
name: build-dashboard
description: Rebuild, optionally refresh data for, and validate The ABS Edge Map self-contained HTML dashboard. Use when updating dashboard data, templates, metrics, config, or generated output in this repository, especially before handing off `outputs/dashboard/abs_catcher_dashboard.html`.
---

# Build Dashboard

Use this workflow for repeatable dashboard refreshes, including both data refresh and generated HTML refresh when needed.

## Decide Refresh Scope

- Use the cached-data build for normal template, metric, copy, or styling changes.
- Use the Statcast-refresh build only when the user asks for fresh data, the config date window changes, or the cache is missing.
- Keep this as one workflow. Do not create a separate Statcast refresh workflow unless data refresh becomes a frequent standalone task.

## Build With Existing Cache

From the repository root:

```bash
python -m src.render_html --config config/dashboard_config.json
```

## Refresh Data And Build

```bash
python -m src.render_html --config config/dashboard_config.json --refresh-statcast
```

## Validate

Run these checks before handoff:

```bash
python -m compileall src
```

```bash
node -e "const fs=require('fs'); const h=fs.readFileSync('outputs/dashboard/abs_catcher_dashboard.html','utf8'); const m=h.match(/<script>([\\s\\S]*)<\\/script>/); if(!m) throw new Error('No script tag found'); new Function(m[1]); console.log('generated dashboard script syntax ok');"
```

If layout or interaction changed, open or reload:

```text
outputs/dashboard/abs_catcher_dashboard.html
```

Check the browser view for:

- Zone Change appears first.
- The file works without a server.
- No mock data appears in coach-facing sections.
- The zone view uses a static catcher perspective.
- Tooltip and area-selection interactions still work.

## Data Rules

- Do not refresh Statcast cache unless the user asks, the config date window changes, or cache is missing and a real rebuild requires it.
- Do not introduce new data sources without user approval.
- Do not add report exports or Streamlit dependencies.
