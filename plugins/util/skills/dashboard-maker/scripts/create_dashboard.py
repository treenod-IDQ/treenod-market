#!/usr/bin/env python3
"""Template for creating a Lakeview dashboard via Databricks SDK.

Customize DASHBOARD_NAME, PARENT_PATH, WAREHOUSE_ID, DATASETS, and widget
functions for your use case, then run:

    uv run --with databricks-sdk python3 create_dashboard.py
"""

import json

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import Dashboard

# --- Config (customize these) ---
DASHBOARD_NAME = "My Dashboard"
PARENT_PATH = "/Users/you@example.com"
WAREHOUSE_ID = "your_warehouse_id"

# --- Datasets ---
DATASETS = [
    {
        "name": "ds_main",
        "displayName": "Main Data",
        "queryLines": [
            "SELECT\n",
            "  date_col as dt,\n",
            "  category,\n",
            "  COUNT(*) as cnt\n",
            "FROM catalog.schema.table\n",
            "GROUP BY 1, 2",
        ],
    },
]


# --- Widget builders ---

def text_widget(name, lines, pos):
    return {
        "widget": {"name": name, "multilineTextboxSpec": {"lines": lines}},
        "position": pos,
    }


def counter_widget(name, title, dataset, column, pos):
    """Counter: version 2, disaggregated true, rowNumber 1."""
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": [{"name": column, "expression": f"`{column}`"}],
                    "disaggregated": True,
                },
            }],
            "spec": {
                "version": 2,
                "widgetType": "counter",
                "encodings": {"value": {"fieldName": column, "rowNumber": 1}},
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def bar_widget(name, title, dataset, x_field, y_field, pos,
               x_type="categorical", aggregated=True):
    fields = [
        {"name": x_field, "expression": f"`{x_field}`"},
        {"name": f"sum({y_field})", "expression": f"SUM(`{y_field}`)"},
    ]
    y_name = f"sum({y_field})"
    if not aggregated:
        fields = [
            {"name": x_field, "expression": f"`{x_field}`"},
            {"name": y_field, "expression": f"`{y_field}`"},
        ]
        y_name = y_field

    x_scale = {"type": x_type}
    if x_type == "categorical":
        x_scale["sort"] = {"by": "y-reversed"}

    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": fields,
                    "disaggregated": not aggregated,
                },
            }],
            "spec": {
                "version": 3,
                "widgetType": "bar",
                "encodings": {
                    "x": {"fieldName": x_field, "scale": x_scale, "displayName": x_field},
                    "y": {"fieldName": y_name, "scale": {"type": "quantitative"}, "displayName": y_field},
                },
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def table_widget(name, title, dataset, columns, pos):
    fields = [{"name": c, "expression": f"`{c}`"} for c in columns]
    col_encodings = [{"fieldName": c, "displayName": c} for c in columns]
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": fields,
                    "disaggregated": True,
                },
            }],
            "spec": {
                "version": 3,
                "widgetType": "table",
                "encodings": {"columns": col_encodings},
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def date_range_filter(name, title, dataset, date_column, pos,
                      default_min="now-30d/d", default_max="now/d"):
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": [
                        {"name": date_column, "expression": f"`{date_column}`"},
                        {"name": f"{date_column}_associativity",
                         "expression": "COUNT_IF(`associative_filter_predicate_group`)"},
                    ],
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 2,
                "widgetType": "filter-date-range-picker",
                "encodings": {
                    "fields": [{"fieldName": date_column, "queryName": "main_query"}],
                },
                "selection": {
                    "defaultSelection": {
                        "range": {
                            "dataType": "DATE",
                            "min": {"value": default_min},
                            "max": {"value": default_max},
                        }
                    }
                },
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def multi_select_filter(name, title, dataset, column, pos):
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": [
                        {"name": column, "expression": f"`{column}`"},
                        {"name": f"{column}_associativity",
                         "expression": "COUNT_IF(`associative_filter_predicate_group`)"},
                    ],
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 2,
                "widgetType": "filter-multi-select",
                "encodings": {
                    "fields": [{"fieldName": column, "queryName": "main_query"}],
                },
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def line_widget(name, title, dataset, x_field, y_field, pos,
                x_type="temporal", color_field=None):
    """Line chart for time-series data."""
    fields = [
        {"name": x_field, "expression": f"`{x_field}`"},
        {"name": f"sum({y_field})", "expression": f"SUM(`{y_field}`)"},
    ]
    encodings = {
        "x": {"fieldName": x_field, "scale": {"type": x_type}, "displayName": x_field},
        "y": {"fieldName": f"sum({y_field})", "scale": {"type": "quantitative"}, "displayName": y_field},
    }
    if color_field:
        fields.append({"name": color_field, "expression": f"`{color_field}`"})
        encodings["color"] = {"fieldName": color_field, "scale": {"type": "categorical"}}

    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": fields,
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 3,
                "widgetType": "line",
                "encodings": encodings,
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def pie_widget(name, title, dataset, label_field, value_field, pos):
    """Pie/donut chart for composition data."""
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": [
                        {"name": label_field, "expression": f"`{label_field}`"},
                        {"name": f"sum({value_field})", "expression": f"SUM(`{value_field}`)"},
                    ],
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 3,
                "widgetType": "pie",
                "encodings": {
                    "angle": {"fieldName": f"sum({value_field})", "scale": {"type": "quantitative"}},
                    "color": {"fieldName": label_field, "scale": {"type": "categorical"}},
                },
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def combo_widget(name, title, dataset, x_field, primary_fields, secondary_fields, pos):
    """Combo chart with dual y-axis."""
    fields = [{"name": x_field, "expression": f"`{x_field}`"}]
    for f in primary_fields + secondary_fields:
        fields.append({"name": f"sum({f})", "expression": f"SUM(`{f}`)"})

    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": fields,
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 3,
                "widgetType": "combo",
                "encodings": {
                    "x": {"fieldName": x_field, "scale": {"type": "temporal"}, "displayName": x_field},
                    "y": {
                        "primary": {
                            "fields": [{"fieldName": f"sum({f})", "displayName": f} for f in primary_fields],
                            "scale": {"type": "quantitative"},
                        },
                        "secondary": {
                            "fields": [{"fieldName": f"sum({f})", "displayName": f} for f in secondary_fields],
                            "scale": {"type": "quantitative"},
                        },
                    },
                },
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


def single_select_filter(name, title, dataset, column, pos):
    """Single-select dropdown filter."""
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": [
                        {"name": column, "expression": f"`{column}`"},
                        {"name": f"{column}_associativity",
                         "expression": "COUNT_IF(`associative_filter_predicate_group`)"},
                    ],
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 2,
                "widgetType": "filter-single-select",
                "encodings": {
                    "fields": [{"fieldName": column, "queryName": "main_query"}],
                },
                "frame": {"showTitle": True, "title": title},
            },
        },
        "position": pos,
    }


# --- Build and deploy ---

def build_config(datasets, layout):
    # Validate: no \r\n in queryLines
    for ds in datasets:
        for i, line in enumerate(ds.get("queryLines", [])):
            if "\r\n" in line:
                raise ValueError(
                    f"Dataset '{ds['name']}' has \\r\\n in queryLines at index {i}. "
                    "Use \\n instead."
                )

    # Validate: no name collisions between datasets and widgets
    ds_names = {ds["name"] for ds in datasets}
    w_names = set()
    for item in layout:
        w = item.get("widget", {})
        if "name" in w:
            w_names.add(w["name"])
    collisions = ds_names & w_names
    if collisions:
        raise ValueError(
            f"Name collision between datasets and widgets: {collisions}. "
            "Use 'ds_' prefix for datasets, 'w_' prefix for widgets."
        )

    # Validate: widget dataset references exist
    for item in layout:
        w = item.get("widget", {})
        widget_name = w.get("name", "unknown")
        for q in w.get("queries", []):
            ds_name = q.get("query", {}).get("datasetName")
            if ds_name and ds_name not in ds_names:
                raise ValueError(
                    f"Widget '{widget_name}' references non-existent dataset "
                    f"'{ds_name}'. Available: {sorted(ds_names)}"
                )

    return {
        "datasets": datasets,
        "pages": [{
            "name": "main_page",
            "displayName": "Overview",
            "layout": layout,
            "pageType": "PAGE_TYPE_CANVAS",
        }],
    }


def create_dashboard(config, name=DASHBOARD_NAME, parent=PARENT_PATH,
                     warehouse=WAREHOUSE_ID):
    w = WorkspaceClient()
    dashboard = w.lakeview.create(
        Dashboard(
            display_name=name,
            serialized_dashboard=json.dumps(config),
            parent_path=parent,
            warehouse_id=warehouse,
        )
    )
    w.lakeview.publish(
        dashboard.dashboard_id,
        embed_credentials=True,
        warehouse_id=warehouse,
    )
    host = w.config.host.rstrip("/")
    url = f"{host}/sql/dashboardsv3/{dashboard.dashboard_id}"
    print(f"Dashboard created: {url}")
    return dashboard.dashboard_id


def update_dashboard(dashboard_id, config, warehouse=WAREHOUSE_ID):
    w = WorkspaceClient()
    existing = w.lakeview.get(dashboard_id)
    w.lakeview.update(
        dashboard_id,
        Dashboard(
            display_name=existing.display_name,
            serialized_dashboard=json.dumps(config),
            warehouse_id=warehouse,
            etag=existing.etag,
        ),
    )
    w.lakeview.publish(
        dashboard_id,
        embed_credentials=True,
        warehouse_id=warehouse,
    )
    print(f"Dashboard updated: {dashboard_id}")


if __name__ == "__main__":
    layout = [
        text_widget("w_title", ["### My Dashboard\n"], {"x": 0, "y": 0, "width": 6, "height": 2}),
        bar_widget("w_chart", "Count by Category", "ds_main", "category", "cnt",
                   {"x": 0, "y": 2, "width": 6, "height": 6}),
    ]
    config = build_config(DATASETS, layout)
    create_dashboard(config)
