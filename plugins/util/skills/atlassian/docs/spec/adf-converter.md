---
title: ADF Converter Improvement Spec
created: 2024-12-11
status: completed
version: 0.1.0
---

## Overview

Analysis of the current `adf_converter.py` implementation against real Confluence page data reveals several missing ADF node types that cause content loss during conversion.

## Source Page Analysis

- Page ID: 73287041106
- Node types found in source ADF:
  - bulletList, codeBlock, doc, expand, extension, hardBreak, heading
  - inlineCard, listItem, mark:alignment, mark:breakout, mark:link, mark:strong
  - paragraph, table, tableCell, tableHeader, tableRow, taskItem, taskList, text

## Current Implementation Coverage

### Supported Node Types

| Node Type | Status | Notes |
| --- | --- | --- |
| doc | supported | root node |
| paragraph | supported | basic conversion |
| heading | supported | levels 1-6 |
| bulletList | supported | with nesting |
| orderedList | supported | with nesting |
| listItem | supported | as child of lists |
| codeBlock | supported | language attr preserved |
| blockquote | supported | basic conversion |
| rule | supported | horizontal rule |
| table | supported | basic markdown table |
| tableRow | supported | |
| tableCell | supported | |
| tableHeader | supported | |
| text | supported | with marks |
| hardBreak | supported | as `  \n` |
| emoji | supported | text fallback |
| mention | supported | text fallback |

### Supported Marks

| Mark Type | Status | Notes |
| --- | --- | --- |
| strong | supported | `**text**` |
| em | supported | `*text*` |
| code | supported | `` `text` `` |
| strike | supported | `~~text~~` |
| underline | supported | `<u>text</u>` |
| link | supported | `[text](url)` |

## Missing Features

### 1. taskList / taskItem (Checkbox)

ADF structure:

```json
{
  "type": "taskList",
  "content": [
    {
      "type": "taskItem",
      "attrs": {
        "state": "DONE"  // or "TODO"
      },
      "content": [{"text": "Task text", "type": "text"}]
    }
  ]
}
```

Expected markdown output:

```markdown
- [x] Task text (when state: "DONE")
- [ ] Task text (when state: "TODO")
```

Current behavior: Falls through to default handler, outputs only text without checkbox.

Priority: HIGH - affects task tracking content

### 2. inlineCard (Confluence Page Links)

ADF structure:

```json
{
  "type": "inlineCard",
  "attrs": {
    "url": "https://treenod.atlassian.net/wiki/spaces/GT/pages/72101108461"
  }
}
```

Expected markdown output:

```markdown
[Page Title](https://treenod.atlassian.net/wiki/spaces/GT/pages/72101108461)
```

Note: Getting page title requires additional API call. Fallback can use URL or extract page ID.

Current behavior: Not handled, content is lost entirely.

Priority: HIGH - breaks all internal Confluence links

### 3. expand (Collapsible Section)

ADF structure:

```json
{
  "type": "expand",
  "attrs": {
    "title": "Section Title"
  },
  "content": [
    // child nodes (e.g., codeBlock, paragraph)
  ]
}
```

Expected markdown output:

```markdown
<details>
<summary>Section Title</summary>

(content converted recursively)

</details>
```

Alternative (simpler):

```markdown
### Section Title

(content)
```

Current behavior: Falls through to default, outputs only inner content without expand context.

Priority: MEDIUM - content preserved but structure lost

### 4. extension (External Macros like Mermaid)

ADF structure:

```json
{
  "type": "extension",
  "attrs": {
    "extensionType": "com.atlassian.ecosystem",
    "extensionKey": ".../mermaid-diagram",
    "text": "Mermaid diagram",
    "parameters": {
      "extensionTitle": "Mermaid diagram"
    }
  }
}
```

Note: Extension content (like mermaid code) is NOT stored in the ADF node itself. It is stored separately and rendered by the extension iframe.

For Mermaid specifically, the source code may be in an adjacent `expand > codeBlock` pattern (as seen in sample).

Expected markdown output:

```markdown
<!-- Extension: Mermaid diagram -->
<!-- Extension content not available via API -->
```

Current behavior: Not handled, content lost entirely.

Priority: LOW - extension content often unavailable via API

### 5. Missing Marks

| Mark Type | ADF Example | Expected Output |
| --- | --- | --- |
| alignment | `{"type": "alignment", "attrs": {"align": "center"}}` | No direct markdown equivalent; could use HTML or ignore |
| breakout | `{"type": "breakout", "attrs": {"mode": "wide"}}` | Layout hint; ignore in markdown |

Priority: LOW - layout hints, no semantic content

## Nested taskList Handling

The sample shows nested taskList within taskItem:

```json
{
  "type": "taskItem",
  "content": [
    {"text": "Parent task", "type": "text"},
    {
      "type": "taskList",
      "content": [
        {"type": "taskItem", ...}
      ]
    }
  ]
}
```

Expected output:

```markdown
- [ ] Parent task
  - [ ] Child task
```

## Implementation Plan

### Phase 1: Core Missing Types

1. Add `taskList` handler
2. Add `taskItem` handler with state attribute
3. Add `inlineCard` handler (URL-only fallback)

### Phase 2: Rich Content

4. Add `expand` handler with `<details>` output
5. Handle nested taskList within taskItem

### Phase 3: Extensions

6. Add `extension` handler with metadata comment
7. Special case for Mermaid: look for adjacent codeBlock source

## Code Changes Required

Location: `/home/drew/.claude/skills/atlassian/scripts/adf_converter.py`

### convert_node_to_markdown function

Add handlers for:

```python
elif node_type == 'taskList':
    return convert_task_list(node, list_depth)

elif node_type == 'taskItem':
    return convert_task_item(node, list_depth)

elif node_type == 'inlineCard':
    return convert_inline_card(node)

elif node_type == 'expand':
    return convert_expand(node)

elif node_type == 'extension':
    return convert_extension(node)
```

### New Functions

```python
def convert_task_list(node: dict, depth: int) -> str:
    """Convert task list (checkbox list) to markdown."""
    pass

def convert_task_item(node: dict, depth: int) -> str:
    """Convert task item with DONE/TODO state."""
    pass

def convert_inline_card(node: dict) -> str:
    """Convert Confluence page link to markdown link."""
    pass

def convert_expand(node: dict) -> str:
    """Convert collapsible section to HTML details tag."""
    pass

def convert_extension(node: dict) -> str:
    """Convert extension macro to comment with metadata."""
    pass
```

## Testing

Test page: 73287041106 (contains all missing node types)

Validation checklist:

- [x] Checkboxes render with correct state
- [x] Nested checkboxes indent properly
- [x] Confluence page links are clickable
- [x] Expand sections show title and content
- [x] Extension macros show informative placeholder

## Missing Features (Phase 4)

### Image/Media Support

Markdown image syntax: `![alt text](url or path)`

For external URLs:
```json
{
  "type": "mediaSingle",
  "attrs": {"layout": "center"},
  "content": [{
    "type": "media",
    "attrs": {
      "type": "external",
      "url": "https://example.com/image.png",
      "alt": "alt text"
    }
  }]
}
```

For attached files (requires prior upload):
```json
{
  "type": "mediaSingle",
  "attrs": {"layout": "center"},
  "content": [{
    "type": "media",
    "attrs": {
      "type": "file",
      "id": "{file-id}",
      "collection": "contentId-{page-id}"
    }
  }]
}
```

Note: Use `file_id` (UUID format like `24e522f3-af3d-4979-925f-633c41caee8c`) from
attachment upload response, NOT the attachment ID (`att123456`). The `upload_attachment()`
function returns both `id` (attachment ID) and `file_id` (for ADF embedding).

Priority: HIGH - needed for analysis reports with charts

### Implementation Notes

When syncing markdown with images to Confluence:
1. Parse markdown for image references
2. Upload local image files as attachments
3. Replace image paths with attachment IDs in ADF
4. Create page with media nodes

## Implementation Status

All Phase 1-3 items completed on 2024-12-11:

- [x] `convert_task_list()` - checkbox lists
- [x] `convert_task_item()` - individual checkboxes with DONE/TODO state
- [x] `convert_inline_card()` - Confluence/Jira smart links
- [x] `convert_expand()` - collapsible sections with `<details>` HTML
- [x] `convert_extension()` - extension macros as HTML comments
- [x] Fixed nested list indentation in `convert_bullet_list()` and `convert_ordered_list()`
