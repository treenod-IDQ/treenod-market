---
title: Lakeview Dashboard JSON Structure Guide
date: 2025-12-12
---

## Overview

Lakeview dashboard configuration is stored as JSON in the `serialized_dashboard` field. This guide explains the structure and parameters for programmatic dashboard creation/modification.

## Top-Level Structure

```
{
  "datasets": [...],      # Data sources (SQL queries)
  "pages": [...],         # Dashboard pages with widgets
  "uiSettings": {...}     # Theme and UI configuration
}
```

## Datasets

Datasets define the SQL queries that power widgets.

### Basic Dataset

```json
{
  "name": "unique_id",           # Internal ID (auto-generated 8-char hex)
  "displayName": "Human Name",   # Shown in UI
  "queryLines": [                # SQL query split by lines
    "SELECT\n",
    "  col1,\n",
    "  col2\n",
    "FROM table"
  ]
}
```

### Dataset with Default Catalog/Schema

```json
{
  "name": "abc12345",
  "displayName": "My Query",
  "queryLines": ["SELECT * FROM my_table"],
  "catalog": "gold_analytic",    # Default catalog
  "schema": "common"             # Default schema
}
```

### Dataset with Parameters

```json
{
  "name": "abc12345",
  "displayName": "Parameterized Query",
  "queryLines": [
    "SELECT * FROM table\n",
    "WHERE dt >= :fromDate"       # Parameter syntax :paramName
  ],
  "parameters": [
    {
      "name": "fromDate",
      "keyword": "fromDate"
    }
  ]
}
```

## Pages

### Page Types

| Type | Description |
|------|-------------|
| `PAGE_TYPE_CANVAS` | Regular dashboard page with widgets |
| `PAGE_TYPE_GLOBAL_FILTERS` | Special page for cross-page filters |

### Page Structure

```json
{
  "name": "page_id",             # Internal ID
  "displayName": "Page Title",   # Tab name shown in UI
  "layout": [...],               # Array of widget placements
  "pageType": "PAGE_TYPE_CANVAS"
}
```

## Widgets

### Widget Placement

Each widget is wrapped in a layout item with position:

```json
{
  "widget": {...},
  "position": {
    "x": 0,          # Column (0-5, dashboard is 6 columns wide)
    "y": 0,          # Row position
    "width": 3,      # Width in columns (1-6)
    "height": 6      # Height in grid units
  }
}
```

### Widget Types

| Type | Description | Key Encodings |
|------|-------------|---------------|
| `line` | Line chart | x, y, color |
| `bar` | Bar chart | x, y, color |
| `area` | Area chart | x, y, color |
| `scatter` | Scatter plot | x, y, size, color |
| `pie` | Pie/Donut chart | angle, color |
| `heatmap` | Heat map | x, y, color |
| `funnel` | Funnel chart | x, y |
| `combo` | Combo chart (dual axis) | x, y.primary, y.secondary |
| `table` | Data table | columns |
| `pivot` | Pivot table | rows, columns, cell |
| `counter` | Single value display | value |
| `filter-single-select` | Dropdown filter | fields |
| `filter-multi-select` | Multi-select filter | fields |
| `filter-date-picker` | Date picker | fields |
| `filter-date-range-picker` | Date range picker | fields |
| `range-slider` | Range slider | fields |

### Text Widget

```json
{
  "widget": {
    "name": "text_widget_id",
    "multilineTextboxSpec": {
      "lines": [
        "### Title\n",
        "\n",
        "- bullet point"
      ]
    }
  },
  "position": {"x": 0, "y": 0, "width": 6, "height": 2}
}
```

Supports markdown and HTML styling.

### Visualization Widget

```json
{
  "widget": {
    "name": "widget_id",
    "queries": [
      {
        "name": "main_query",
        "query": {
          "datasetName": "dataset_id",    # Reference to dataset
          "fields": [...],                # Field definitions
          "disaggregated": false          # true=raw data, false=aggregated
        }
      }
    ],
    "spec": {
      "version": 3,
      "widgetType": "line",
      "encodings": {...},
      "frame": {...}
    }
  }
}
```

## Query Fields

Fields define what data is pulled from the dataset and how it's transformed.

### Basic Field (Column Reference)

```json
{
  "name": "column_name",
  "expression": "`column_name`"
}
```

### Aggregation Field

```json
{
  "name": "sum(value)",
  "expression": "SUM(`value`)"
}
```

### Date Truncation

```json
{
  "name": "weekly(dt)",
  "expression": "DATE_TRUNC(\"WEEK\", `dt`)"
}
```

Supported truncations: `DAY`, `WEEK`, `MONTH`, `QUARTER`, `YEAR`

### Count Distinct

```json
{
  "name": "countdistinct(user_id)",
  "expression": "COUNT(DISTINCT `user_id`)"
}
```

## Encodings

### Scale Types

| Type | Use Case |
|------|----------|
| `quantitative` | Numeric values (continuous) |
| `temporal` | Date/time values |
| `categorical` | Discrete categories |

### Basic X-Y Encoding

```json
"encodings": {
  "x": {
    "fieldName": "date_field",
    "scale": {"type": "temporal"},
    "displayName": "Date"           # Optional axis label
  },
  "y": {
    "fieldName": "value_field",
    "scale": {"type": "quantitative"}
  }
}
```

### Color Encoding (Series/Groups)

```json
"encodings": {
  "x": {...},
  "y": {...},
  "color": {
    "fieldName": "category_field",
    "scale": {"type": "categorical"}
  }
}
```

### Dual Y-Axis (Primary/Secondary)

```json
"encodings": {
  "x": {...},
  "y": {
    "primary": {
      "fields": [
        {"fieldName": "metric1", "displayName": "Metric 1"}
      ],
      "scale": {"type": "quantitative"}
    },
    "secondary": {
      "fields": [
        {"fieldName": "metric2", "displayName": "Metric 2"}
      ],
      "scale": {"type": "quantitative"}
    }
  }
}
```

### Categorical Sorting

```json
"scale": {
  "type": "categorical",
  "sort": {
    "by": "y-reversed"      # Sort by y-value descending
  }
}
```

Sort options: `y-reversed`, `y`, `natural-order`, `custom-order`

### Custom Order

```json
"scale": {
  "type": "categorical",
  "sort": {
    "by": "custom-order",
    "orderedValues": ["A", "B", "C", "D"]
  }
}
```

## Frame (Title/Description)

```json
"frame": {
  "showTitle": true,
  "title": "Chart Title",
  "showDescription": false
}
```

## Filter Widgets

### Date Range Filter

```json
{
  "widget": {
    "name": "dt_filter",
    "queries": [
      {
        "name": "filter_query_name",
        "query": {
          "datasetName": "dataset_id",
          "fields": [
            {"name": "dt", "expression": "`dt`"},
            {"name": "dt_associativity", "expression": "COUNT_IF(`associative_filter_predicate_group`)"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 2,
      "widgetType": "filter-date-range-picker",
      "encodings": {
        "fields": [
          {
            "fieldName": "dt",
            "queryName": "filter_query_name"
          }
        ]
      },
      "selection": {
        "defaultSelection": {
          "range": {
            "dataType": "DATE",
            "min": {"value": "now-7d/d"},
            "max": {"value": "now/d"}
          }
        }
      },
      "frame": {"showTitle": true}
    }
  }
}
```

Date range shortcuts: `now`, `now/d` (start of day), `now-7d/d` (7 days ago)

### Single Select Filter

```json
{
  "widget": {
    "name": "category_filter",
    "queries": [
      {
        "name": "filter_query",
        "query": {
          "datasetName": "dataset_id",
          "fields": [
            {"name": "category", "expression": "`category`"},
            {"name": "category_associativity", "expression": "COUNT_IF(`associative_filter_predicate_group`)"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 2,
      "widgetType": "filter-single-select",
      "encodings": {
        "fields": [
          {"fieldName": "category", "queryName": "filter_query"}
        ]
      },
      "frame": {"showTitle": true, "title": "Category"}
    }
  }
}
```

## Styling Extensions

```json
{
  "widget": {...},
  "specExtensions": {
    "widgetBackgroundColor": {
      "light": "#CEE8D7"
    },
    "widgetBorderColor": {
      "light": "#004B3E"
    }
  }
}
```

## UI Settings

```json
"uiSettings": {
  "theme": {
    "widgetHeaderAlignment": "ALIGNMENT_UNSPECIFIED"
  },
  "applyModeEnabled": false    # Manual apply button for filters
}
```

## Common Patterns

### Creating a New Widget

1. Create dataset with SQL query
2. Reference dataset in widget's `query.datasetName`
3. Define fields to extract/aggregate
4. Configure encodings based on widget type
5. Set position

### Modifying SQL Query

Update `queryLines` array in the dataset:

```python
config["datasets"][0]["queryLines"] = [
    "SELECT * FROM new_table\n",
    "WHERE condition"
]
```

### Adding a New Page

```python
config["pages"].insert(-1, {  # Insert before Global Filters page
    "name": "new_page_id",
    "displayName": "New Page",
    "layout": [],
    "pageType": "PAGE_TYPE_CANVAS"
})
```

### Key Parameters to Edit

| What to Change | Where |
|----------------|-------|
| SQL query | `datasets[n].queryLines` |
| Chart title | `widget.spec.frame.title` |
| Widget size/position | `layout[n].position` |
| Axis field | `widget.spec.encodings.x/y.fieldName` |
| Aggregation | `widget.queries[0].query.fields[n].expression` |
| Date truncation | `widget.queries[0].query.fields[n].expression` with `DATE_TRUNC` |
| Series grouping | `widget.spec.encodings.color.fieldName` |
| Filter default | `widget.spec.selection.defaultSelection` |

## API Usage

### Get Dashboard

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import Dashboard
import json

w = WorkspaceClient()
dashboard = w.lakeview.get(dashboard_id="...")
config = json.loads(dashboard.serialized_dashboard)
```

### Update Dashboard

```python
existing = w.lakeview.get(dashboard_id="...")
config = json.loads(existing.serialized_dashboard)

# Modify config...
config["datasets"][0]["displayName"] = "Updated Name"

w.lakeview.update(
    dashboard_id="...",
    Dashboard(
        display_name=existing.display_name,
        serialized_dashboard=json.dumps(config),
        warehouse_id="your_warehouse_id",
        etag=existing.etag,
    ),
)
w.lakeview.publish(
    dashboard_id="...",
    embed_credentials=True,
    warehouse_id="your_warehouse_id",
)
```

### Create New Dashboard

```python
dashboard = w.lakeview.create(
    Dashboard(
        display_name="My Dashboard",
        serialized_dashboard=json.dumps(config),
        parent_path="/Users/user@example.com",
        warehouse_id="your_warehouse_id",
    )
)
w.lakeview.publish(
    dashboard.dashboard_id,
    embed_credentials=True,
    warehouse_id="your_warehouse_id",
)
```

## References

- SDK: https://databricks-sdk-py.readthedocs.io
- PyPI: https://pypi.org/project/databricks-sdk/
