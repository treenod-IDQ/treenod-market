---
name: dashboard-maker
description: Create and update Databricks Lakeview dashboards programmatically via the SDK. Use when users need to (1) create a new Lakeview dashboard from SQL queries, (2) update an existing dashboard's widgets or queries, (3) build dashboard JSON config with counters, bar charts, line charts, pie charts, tables, and filters. Requires databricks-sdk and DATABRICKS_HOST/DATABRICKS_TOKEN env vars.
---

## Prerequisites

- Environment variables: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`
- Package: `databricks-sdk` (auto-installed by `uv run --with`)
- Warehouse ID: required for `create_dashboard()` and `update_dashboard()` (find in SQL Warehouses > Connection details)

## Quick Start

Use `scripts/create_dashboard.py` as a template. Import builder functions:

```python
from scripts.create_dashboard import (
    build_config, create_dashboard, update_dashboard,
    text_widget, counter_widget, bar_widget, table_widget,
    line_widget, pie_widget, combo_widget,
    date_range_filter, multi_select_filter, single_select_filter,
)
```

Run with: `uv run --with databricks-sdk python3 <script>.py`

## Workflow

1. Gather requirements: SQL queries, chart types, layout
2. Plan the grid layout (6 columns wide, y increases downward)
3. Build datasets (SQL queries) and widgets (visualizations)
4. Create via SDK, publish with warehouse_id
5. Verify in browser

## Widget Builders

| Function | Widget Type | Version | Key Parameters |
|----------|-------------|---------|----------------|
| text_widget | text | - | name, lines, pos |
| counter_widget | counter | 2 | name, title, dataset, column, pos |
| bar_widget | bar | 3 | name, title, dataset, x_field, y_field, pos, x_type, aggregated |
| line_widget | line | 3 | name, title, dataset, x_field, y_field, pos, x_type, color_field |
| pie_widget | pie | 3 | name, title, dataset, label_field, value_field, pos |
| combo_widget | combo | 3 | name, title, dataset, x_field, primary_fields, secondary_fields, pos |
| table_widget | table | 3 | name, title, dataset, columns, pos |
| date_range_filter | filter-date-range-picker | 2 | name, title, dataset, date_column, pos |
| multi_select_filter | filter-multi-select | 2 | name, title, dataset, column, pos |
| single_select_filter | filter-single-select | 2 | name, title, dataset, column, pos |

## Critical Rules

- queryLines must use `\n` line endings, not `\r\n` (validated by build_config)
- Dataset `name` and widget `name` must never collide; use `ds_` prefix for datasets, `w_` prefix for widgets (validated by build_config)
- Widget `datasetName` must reference an existing dataset (validated by build_config)
- Counter widgets: `spec.version: 2`, `disaggregated: true` in query object (not in spec), `encodings.value.rowNumber: 1`
- Chart/table widgets: `spec.version: 3`, filter widgets: `spec.version: 2`
- Always pass `warehouse_id` when creating, and call `lakeview.publish()` after create/update
- SDK requires `Dashboard` object: `w.lakeview.create(Dashboard(display_name=..., serialized_dashboard=..., parent_path=..., warehouse_id=...))`
- Counter datasets should pre-aggregate values in SQL (one row result), not aggregate in widget fields

## Grid Layout

Dashboard is 6 columns wide. Position: `{"x": 0-5, "y": row, "width": 1-6, "height": units}`

Typical layout pattern:
```
y=0  h=2: Title text (width=6)
y=2  h=2: Filters (width=3 each)
y=4  h=3: Counters (width=2 each, 3 across)
y=7  h=6: Charts (width=3 each, 2 across)
y=13 h=6: More charts (width=3 each)
y=19 h=8: Table (width=6)
```

## Filter Pattern

Filters require an associativity field alongside the filter column:

```python
"fields": [
    {"name": "col", "expression": "`col`"},
    {"name": "col_associativity", "expression": "COUNT_IF(`associative_filter_predicate_group`)"},
]
```

## Update Existing Dashboard

```python
from scripts.create_dashboard import update_dashboard, build_config
config = build_config(datasets, layout)
update_dashboard("dashboard_id_here", config)
```

## Validation

`build_config()` runs 3 checks before returning the config:

1. `\r\n` in queryLines: raises ValueError with dataset name and line index
2. Name collision between datasets and widgets: raises ValueError with collision details
3. Widget references non-existent dataset: raises ValueError with available datasets

## Troubleshooting

### Blank dashboard after creation

- Check that `warehouse_id` is passed to `create_dashboard()`
- Verify `lakeview.publish()` was called after create

### API 400 error

- Check queryLines for `\r\n` (use `\n` only)
- Check for name collisions between datasets and widgets
- On update: include `etag` from `lakeview.get()` result

### Counter shows wrong value

- Ensure `disaggregated: true` is in the query object, not in spec
- Ensure `encodings.value.rowNumber: 1` is set
- Ensure SQL query returns exactly one row (pre-aggregate in SQL)

## References

For full JSON structure details, see [references/lakeview-guide.md](references/lakeview-guide.md).
