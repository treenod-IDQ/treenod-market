---
title: Marimo HTML to ADF Conversion Specification
created: 2025-01-13
updated: 2026-01-13
status: implemented
---

## Overview

Specification for converting marimo notebook HTML exports to Atlassian Document Format (ADF) for Confluence pages.

## Problem Statement

Marimo notebooks export to HTML as React SPAs with embedded data. The HTML contains pre-rendered cell outputs that need to be extracted and converted to ADF for Confluence.

Target components for conversion (static content only):
- Markdown text (headings, paragraphs, lists, tables, code blocks)
- Plots/charts (exported as PNG images)
- Tables

Non-targets (dynamic/interactive components):
- Interactive widgets (sliders, dropdowns, etc.)
- Interactive plots (will be exported as static images)
- Code cells (optionally include as code blocks)

## Marimo HTML Export Structure

### Document Structure

```html
<!DOCTYPE html>
<html>
<head>
  <!-- CDN links to marimo frontend assets -->
</head>
<body>
  <div id="root"></div>
  <script data-marimo="true">
    window.__MARIMO_MOUNT_CONFIG__ = {
      "filename": "notebook.py",
      "notebook": { "cells": [...] },
      "session": { "cells": [...] }
    };
  </script>
  <marimo-code hidden="">...</marimo-code>
</body>
</html>
```

### Key Data: `window.__MARIMO_MOUNT_CONFIG__`

```json
{
  "filename": "notebook.py",
  "notebook": {
    "cells": [
      {
        "id": "cell_id",
        "code": "mo.md(\"# Title\")",
        "config": { "hide_code": false }
      }
    ]
  },
  "session": {
    "cells": [
      {
        "id": "cell_id",
        "outputs": [
          {
            "type": "data",
            "data": {
              "text/markdown": "<span class=\"markdown...\">...</span>",
              "text/plain": "..."
            }
          }
        ]
      }
    ]
  }
}
```

### Output Types

| MIME Type | Description | Conversion |
|-----------|-------------|------------|
| `text/markdown` | Rendered markdown as HTML | Parse HTML to ADF |
| `text/plain` | Plain text output | Convert to ADF paragraph |
| `application/vnd.vegalite.v5+json` | Vega-Lite chart spec | Render to PNG, upload as attachment |
| `text/html` | Raw HTML output | Parse HTML to ADF |

### Marimo Custom Components (text/html)

Marimo HTML outputs may contain custom web components instead of standard HTML elements:

| Component | Description | Conversion |
|-----------|-------------|------------|
| `<marimo-table>` | Data table with JSON in data-data attribute | Parse JSON, convert to ADF table |
| `<marimo-ui-element>` | Wrapper for interactive components | Traverse children |
| `<marimo-date>` | Date picker component | Extract value as text |
| flex div containers | Layout wrappers | Traverse children |

#### marimo-table Structure

```html
<marimo-ui-element object-id='RGSE-0' random-id='...'>
  <marimo-table
    data-initial-value='[]'
    data-data='&quot;[{&#92;&quot;col1&#92;&quot;:&#92;&quot;value1&#92;&quot;},...]&quot;'
    data-total-rows='3'
    data-total-columns='2'>
  </marimo-table>
</marimo-ui-element>
```

The `data-data` attribute contains:
1. HTML-escaped string (`&quot;` for quotes, `&#92;` for backslash)
2. Outer quotes wrapping the JSON string
3. Escaped inner quotes (`\"` for JSON string values)

Parsing steps:
1. `html.unescape()` to decode HTML entities
2. Strip outer quotes
3. Replace `\"` with `"` for JSON parsing
4. `json.loads()` to parse array of objects

### Markdown Output Format

Markdown outputs are already rendered to HTML:

```html
<span class="markdown prose dark:prose-invert contents">
  <h1 id="title">Title</h1>
  <span class="paragraph">Paragraph text.</span>
  <ul>
    <li>Item 1</li>
    <li>Item 2</li>
  </ul>
  <table>
    <thead><tr><th>Header</th></tr></thead>
    <tbody><tr><td>Cell</td></tr></tbody>
  </table>
</span>
```

### Chart Output Format

Charts are stored as Vega-Lite JSON specifications:

```json
{
  "application/vnd.vegalite.v5+json": {
    "$schema": "https://vega.github.io/schema/vega-lite/v6.1.0.json",
    "datasets": { ... },
    "encoding": { ... },
    "mark": { ... }
  }
}
```

## Architecture

### Module Structure

```
atlassian/scripts/
├── marimo_converter.py    # Main converter module (new)
├── html_to_adf.py         # HTML to ADF conversion (new)
├── vegalite_renderer.py   # Vega-Lite to PNG (new)
├── confluence_api.py      # Existing API module
└── adf_converter.py       # Existing ADF converter
```

### Conversion Pipeline

```
marimo HTML file
    ↓
[1] Extract __MARIMO_MOUNT_CONFIG__ JSON
    ↓
[2] Iterate session.cells outputs
    ↓
[3] For each output:
    ├── text/markdown → Parse HTML → Convert to ADF nodes
    ├── text/plain → ADF paragraph node
    └── vegalite+json → Render PNG → Upload attachment → ADF media node
    ↓
[4] Assemble ADF document
    ↓
[5] Create/Update Confluence page
```

## Module Specifications

### 1. marimo_converter.py - Main Converter

```python
def convert_marimo_html(
    html_file: str,
    page_id: str = None,
    parent_id: str = None,
    title: str = None,
    include_code: bool = False
) -> dict:
    """
    Convert marimo HTML export to Confluence page.

    Args:
        html_file: Path to marimo HTML export file
        page_id: Existing page ID to update (optional)
        parent_id: Parent page ID for new page (required if no page_id)
        title: Page title (extracted from notebook if not provided)
        include_code: Include code cells in output (default: False)

    Returns:
        dict: Page metadata (id, title, version, url)

    Process:
        1. Parse HTML file to extract notebook config
        2. Extract cell outputs from session data
        3. Convert outputs to ADF nodes
        4. Upload chart images as attachments
        5. Create/update Confluence page with ADF content

    Raises:
        FileNotFoundError: If HTML file doesn't exist
        ValueError: If HTML doesn't contain marimo config
        requests.HTTPError: If API request fails
    """
```

### 2. html_to_adf.py - HTML to ADF Conversion

```python
def html_to_adf(html_content: str) -> list:
    """
    Convert HTML content to ADF nodes.

    Supports:
        - h1-h6: ADF heading nodes
        - p, span.paragraph: ADF paragraph nodes
        - ul, ol: ADF bulletList/orderedList nodes
        - table: ADF table node
        - pre, code: ADF codeBlock node
        - strong, em, code (inline): ADF marks
        - a: ADF link mark

    Args:
        html_content: HTML string to convert

    Returns:
        list: List of ADF content nodes
    """


def convert_element_to_adf(element) -> dict | None:
    """
    Convert single lxml HTML element to ADF node.

    Args:
        element: lxml HtmlElement

    Returns:
        dict: ADF node or None if element should be skipped
    """
```

#### Implementation with lxml

```python
from lxml import html

def html_to_adf_nodes(html_string: str) -> list:
    """Convert marimo markdown HTML output to ADF nodes using lxml."""
    tree = html.fromstring(html_string)
    nodes = []

    for elem in tree.iter():
        if elem.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(elem.tag[1])
            nodes.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": [{"type": "text", "text": elem.text_content()}]
            })
        elif elem.tag == 'p' or (elem.tag == 'span' and 'paragraph' in elem.get('class', '')):
            nodes.append(create_paragraph_adf(elem))
        elif elem.tag == 'ul':
            nodes.append(create_bullet_list_adf(elem))
        elif elem.tag == 'ol':
            nodes.append(create_ordered_list_adf(elem))
        elif elem.tag == 'table':
            nodes.append(create_table_adf(elem))

    return nodes

def create_paragraph_adf(elem) -> dict:
    """Convert paragraph element with inline formatting."""
    content = extract_inline_content(elem)
    return {
        "type": "paragraph",
        "content": content or [{"type": "text", "text": ""}]
    }

def extract_inline_content(elem) -> list:
    """Extract inline content with marks (bold, italic, code, links)."""
    content = []

    for child in elem.iter():
        if child.tag in ('strong', 'b'):
            content.append({
                "type": "text",
                "text": child.text_content(),
                "marks": [{"type": "strong"}]
            })
        elif child.tag in ('em', 'i'):
            content.append({
                "type": "text",
                "text": child.text_content(),
                "marks": [{"type": "em"}]
            })
        elif child.tag == 'code':
            content.append({
                "type": "text",
                "text": child.text_content(),
                "marks": [{"type": "code"}]
            })
        elif child.tag == 'a':
            content.append({
                "type": "text",
                "text": child.text_content(),
                "marks": [{
                    "type": "link",
                    "attrs": {"href": child.get('href', '#')}
                }]
            })
        elif child.text and child.tag not in ('strong', 'em', 'code', 'a', 'b', 'i'):
            content.append({"type": "text", "text": child.text})

    return content

def create_bullet_list_adf(elem) -> dict:
    """Convert ul element with nested list support using XPath."""
    items = []

    # Select only direct li children
    for li in elem.xpath('./li'):
        item_nodes = []

        # Check for nested lists
        for child in li:
            if child.tag == 'ul':
                item_nodes.append(create_bullet_list_adf(child))
            elif child.tag == 'ol':
                item_nodes.append(create_ordered_list_adf(child))

        if not item_nodes:
            item_nodes.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": li.text_content().strip()}]
            })

        items.append({"type": "listItem", "content": item_nodes})

    return {"type": "bulletList", "content": items}

def create_table_adf(elem) -> dict:
    """Convert table element using XPath queries."""
    rows = []

    for tr in elem.xpath('.//tr'):
        cells = []

        for cell in tr.xpath('.//td | .//th'):
            cell_type = "tableHeader" if cell.tag == 'th' else "tableCell"
            cells.append({
                "type": cell_type,
                "content": [{
                    "type": "paragraph",
                    "content": extract_inline_content(cell) or [{"type": "text", "text": cell.text_content()}]
                }]
            })

        if cells:
            rows.append({"type": "tableRow", "content": cells})

    return {"type": "table", "content": rows}
```

#### HTML to ADF Mapping

| HTML Element | ADF Node Type | Notes |
|--------------|---------------|-------|
| `h1`-`h6` | `heading` | `attrs.level` = 1-6 |
| `p`, `span.paragraph` | `paragraph` | |
| `ul` | `bulletList` | |
| `ol` | `orderedList` | |
| `li` | `listItem` | |
| `table` | `table` | |
| `thead > tr` | `tableRow` with `tableHeader` | |
| `tbody > tr` | `tableRow` with `tableCell` | |
| `pre > code` | `codeBlock` | Extract language from class |
| `code` (inline) | text with `code` mark | |
| `strong`, `b` | text with `strong` mark | |
| `em`, `i` | text with `em` mark | |
| `a` | text with `link` mark | |
| `hr` | `rule` | |
| `blockquote` | `blockquote` | |
| `marimo-table` | `table` | Parse data-data JSON attribute |
| `marimo-ui-element` | (traverse children) | Wrapper element |

### 3. vegalite_renderer.py - Chart Rendering

```python
def render_vegalite_to_png(
    spec: dict,
    output_path: str,
    scale: float = 2.0
) -> str:
    """
    Render Vega-Lite specification to PNG image.

    Args:
        spec: Vega-Lite JSON specification
        output_path: Output PNG file path
        scale: Scale factor for higher resolution (default: 2x)

    Returns:
        str: Path to generated PNG file

    Dependencies:
        - vl-convert-python: Native Vega rendering

    Example:
        >>> spec = {"mark": "bar", "encoding": {...}}
        >>> render_vegalite_to_png(spec, "chart.png")
        "chart.png"
    """
```

## CLI Interface

```bash
# Convert marimo HTML and create new page
uv run --no-project --with requests,lxml,vl-convert-python \
    python marimo_converter.py convert notebook.html \
    --parent-id 123456 \
    --title "Analysis Report"

# Update existing page
uv run --no-project --with requests,lxml,vl-convert-python \
    python marimo_converter.py convert notebook.html \
    --page-id 789012

# Include code cells
uv run --no-project --with requests,lxml,vl-convert-python \
    python marimo_converter.py convert notebook.html \
    --parent-id 123456 \
    --include-code
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client (existing) |
| `lxml` | HTML parsing with XPath support (new) |
| `vl-convert-python` | Vega-Lite to PNG rendering (new) |

### Why lxml over BeautifulSoup

| Feature | html.parser | BeautifulSoup | lxml |
|---------|-------------|---------------|------|
| Dependency | None (stdlib) | External | External |
| CSS Selectors | No | Yes | Yes |
| XPath | No | No | Yes |
| Malformed HTML | Poor | Good | Excellent |
| Speed | Medium | Slow | Fast (C-based) |
| Nested Structures | Difficult | Good | Excellent |
| Code Verbosity | High | Medium | Low |

lxml is preferred because:
- Faster (C-based implementation)
- XPath support for clean element selection (`./li`, `.//tr`)
- Excellent handling of nested structures (lists, tables)
- Lighter than BeautifulSoup for this specific use case
- Marimo generates predictable HTML, so BeautifulSoup's lenient parsing is overkill

## ADF Output Structure

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {
      "type": "heading",
      "attrs": { "level": 1 },
      "content": [{ "type": "text", "text": "Analysis Report" }]
    },
    {
      "type": "paragraph",
      "content": [{ "type": "text", "text": "Introduction text..." }]
    },
    {
      "type": "table",
      "content": [...]
    },
    {
      "type": "mediaSingle",
      "attrs": { "layout": "center" },
      "content": [{
        "type": "media",
        "attrs": {
          "type": "file",
          "id": "attachment-uuid",
          "collection": "contentId-pageid"
        }
      }]
    }
  ]
}
```

## Implementation Plan

### Phase 1: HTML Parsing

- [x] Extract `__MARIMO_MOUNT_CONFIG__` from HTML
- [x] Parse session cells and outputs
- [x] Identify output types

### Phase 2: HTML to ADF Conversion

- [x] Implement `html_to_adf.py` module
- [x] Support headings, paragraphs, lists
- [x] Support tables
- [x] Support code blocks
- [x] Support inline formatting (bold, italic, code, links)
- [x] Support marimo-table custom component (v0.8.0)
- [x] Support marimo-ui-element wrapper traversal (v0.8.0)

### Phase 3: Chart Rendering

- [x] Implement `vegalite_renderer.py` module
- [x] Render Vega-Lite specs to PNG
- [x] Handle chart dimensions and scale

### Phase 4: Integration

- [x] Implement `marimo_converter.py` main module
- [x] Integrate with existing `confluence_api.py`
- [x] Upload chart attachments
- [x] Create/update pages with ADF content

### Phase 5: CLI and Testing

- [x] Add CLI interface
- [x] Test with real marimo exports
- [x] Document usage in SKILL.md

## Edge Cases

### Nested Lists

Marimo markdown may contain nested lists. The HTML structure:

```html
<ul>
  <li>Item 1
    <ul>
      <li>Nested item</li>
    </ul>
  </li>
</ul>
```

Must convert to nested ADF listItem nodes.

### Code Blocks with Language

```html
<pre><code class="language-python">def foo(): pass</code></pre>
```

Extract language from class attribute for ADF codeBlock.

### Tables with Complex Cells

Tables may contain formatted text, links, or code within cells. Parser must handle inline content.

### Large Charts

Vega-Lite charts may be large. Consider:
- Maximum image dimensions
- File size limits for Confluence attachments
- Scale factor configuration

## Example Workflow

```python
# Usage example
from marimo_converter import convert_marimo_html

result = convert_marimo_html(
    html_file="DATAANAL-8571_analysis.html",
    parent_id="73294938154",
    title="DATAANAL-8571: 10분 플레이 시점 평균 도달 레벨 분석"
)

print(f"Page created: {result['url']}")
```

## References

- [Marimo Documentation](https://docs.marimo.io/)
- [Atlassian ADF Schema](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
- [Vega-Lite Specification](https://vega.github.io/vega-lite/docs/)
- [vl-convert Documentation](https://github.com/vega/vl-convert)
