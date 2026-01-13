---
title: Marimo Notebook to Confluence Research
created: 2024-12-23
status: completed
---

## Overview

Research on converting marimo notebook exports to Confluence pages, including chart image handling and attachment upload.

## Problem Statement

Marimo notebooks export to:
- HTML: Complex React SPA with embedded JS/data, not suitable for direct parsing
- Markdown: Contains code blocks but no rendered outputs (charts, dynamic content)

For Confluence, need to:
1. Convert markdown content to ADF
2. Render Altair charts to static images
3. Upload images as page attachments
4. Reference images in ADF content

## Marimo Export Analysis

### HTML Export

```bash
marimo export html notebook.py -o output.html
```

Output structure:
- React-based single page application
- External CDN dependencies (fonts, JS bundles)
- Data embedded in JavaScript
- Not suitable for HTML-to-ADF parsing

### Markdown Export

```bash
marimo export md notebook.py -o output.md
```

Output structure:
- Standard markdown with YAML frontmatter
- Python code blocks tagged with `{.marimo}`
- Static markdown content (headers, tables, lists)
- No rendered outputs (charts as code only, `mo.md()` as code only)

Limitations:
- Dynamic content (`mo.md(f"...")`) shown as code, not rendered text
- Charts shown as Altair code, not images

## Solution Architecture

### Approach 1: Static Report Generation (Recommended)

Create a separate report script that:
1. Runs queries and computes values
2. Generates static markdown with computed values
3. Exports Altair charts as PNG images
4. Uses existing atlassian skill to sync markdown to Confluence
5. Adds image attachment support

Components needed:
- Altair chart to PNG export
- Confluence attachment upload API
- ADF mediaGroup/mediaSingle support for images

### Approach 2: HTML Parsing (Complex, Not Recommended)

Would require:
- Rendering marimo HTML (needs browser/headless Chrome)
- Extracting rendered content from DOM
- Converting HTML to ADF
- Not practical due to React SPA complexity

## Technical Research

### Altair Chart to Image

Dependencies:
```bash
pip install vl-convert-python
```

Usage:
```python
import altair as alt

chart = alt.Chart(df).mark_bar().encode(x='x', y='y')

# Save as PNG
chart.save('chart.png', ppi=200)

# Save as SVG
chart.save('chart.svg')

# Options
chart.save('chart.png', scale_factor=2)  # 2x resolution
```

Note: `vl-convert` uses native Vega rendering, no browser needed.

### Confluence Attachment API

Endpoint (v1 API):
```
POST /wiki/rest/api/content/{pageId}/child/attachment
```

Headers:
```
X-Atlassian-Token: no-check
Content-Type: multipart/form-data
Authorization: Basic {base64_auth}
```

Multipart form data:
- `file`: Binary file content
- `comment`: Optional description

Example Python implementation:
```python
import requests
import base64
import os

def upload_attachment(page_id: str, file_path: str, comment: str = "") -> dict:
    """Upload file attachment to Confluence page."""
    confluence_url, _ = get_base_urls()

    email = os.environ.get('ATLASSIAN_USER_EMAIL')
    api_token = os.environ.get('ATLASSIAN_API_TOKEN')
    auth_string = f"{email}:{api_token}"
    base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')

    headers = {
        "Authorization": f"Basic {base64_auth}",
        "X-Atlassian-Token": "no-check"
    }

    url = f"{confluence_url}/wiki/rest/api/content/{page_id}/child/attachment"

    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        files = {
            'file': (filename, f, 'image/png'),
        }
        data = {'comment': comment} if comment else {}

        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()

    return response.json()
```

### ADF Image Support

ADF media node structure for attached images:
```json
{
  "type": "mediaSingle",
  "attrs": {
    "layout": "center"
  },
  "content": [
    {
      "type": "media",
      "attrs": {
        "type": "file",
        "id": "{attachment-id}",
        "collection": "contentId-{page-id}"
      }
    }
  ]
}
```

Alternative using external URL (if image hosted elsewhere):
```json
{
  "type": "mediaSingle",
  "attrs": {
    "layout": "center"
  },
  "content": [
    {
      "type": "media",
      "attrs": {
        "type": "external",
        "url": "https://example.com/image.png"
      }
    }
  ]
}
```

## Implementation Plan

### Phase 1: Attachment Upload (Completed)

1. [x] Add `upload_attachment()` function to `confluence_api.py`
2. [x] Add CLI command for attachment upload
3. [x] Test with image files
4. [x] Return `file_id` for ADF embedding

### Phase 2: ADF Image Support (Partial)

1. [ ] Add `convert_image_to_adf()` function to `adf_converter.py`
2. [ ] Support markdown image syntax: `![alt](path)`
3. [x] Documented ADF media node format in `adf-converter-spec.md`

### Phase 3: Marimo Integration (Manual Workflow)

Current workflow (manual):
1. [x] Export Altair charts with `.configure(font="Noto Sans CJK KR")`
2. [x] Upload chart PNG via `confluence_api.py attach`
3. [x] Create/update page with ADF media node referencing `file_id`

Future automation:
1. [ ] Create `marimo_report.py` helper module
2. [ ] Auto-extract charts from notebook
3. [ ] Generate static markdown with image references
4. [ ] Sync to Confluence with attachment upload

## Markdown to ADF Image Conversion

Current markdown_to_adf() does not handle images. Need to add:

```python
# In markdown_to_adf parsing
elif re.match(r'!\[.*?\]\(.*?\)', line):
    # Image: ![alt](src)
    match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
    alt_text = match.group(1)
    src = match.group(2)

    if src.startswith('http'):
        # External URL
        content.append({
            "type": "mediaSingle",
            "attrs": {"layout": "center"},
            "content": [{
                "type": "media",
                "attrs": {
                    "type": "external",
                    "url": src,
                    "alt": alt_text
                }
            }]
        })
    else:
        # Local file - needs attachment upload first
        # Store path for later processing
        content.append({
            "type": "mediaSingle",
            "attrs": {"layout": "center"},
            "content": [{
                "type": "media",
                "attrs": {
                    "type": "file",
                    "id": f"placeholder:{src}",
                    "collection": ""
                }
            }]
        })
```

## Workflow for Analysis Reports

1. Run analysis notebook to compute results
2. Export charts as PNG:
   ```python
   chart.save('report/chart.png', ppi=200)
   ```
3. Generate static markdown report:
   ```markdown
   ## Results

   | Metric | Value |
   |--------|-------|
   | Avg Stage | 9.2 |

   ![Stage Distribution](chart.png)
   ```
4. Sync to Confluence:
   ```bash
   python confluence_api.py sync ./report {parent_id}
   ```

## Dependencies Summary

Required packages:
- `requests` - HTTP client (existing)
- `vl-convert-python` - Altair to PNG export (new)
- `beautifulsoup4` - HTML parsing (optional, for future)

## Next Steps

1. Implement attachment upload in confluence_api.py
2. Add image support to markdown_to_adf()
3. Update sync command to handle images
4. Create helper for marimo report generation
5. Document workflow in skill SKILL.md
