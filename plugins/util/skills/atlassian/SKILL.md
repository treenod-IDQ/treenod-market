---
name: atlassian
description: Read, create, and update Confluence pages and Jira issues via REST APIs with automatic ADF (Atlassian Document Format) to Markdown conversion. Use when users need to (1) Read/Create/Update Confluence pages from markdown or marimo HTML exports, (2) Sync local markdown folders to Confluence, (3) Export and update Jira issues (summary, description, labels, links), (4) Convert between ADF and Markdown formats, or (5) Interact with Atlassian Cloud APIs programmatically
---

# Atlassian API Skill

Work with Confluence pages and Jira issues using Python scripts and the uv package manager.

## Prerequisites

**Required:**
- uv package manager installed
- Environment variables set:
  - `ATLASSIAN_USER_EMAIL` - Your Atlassian account email
  - `ATLASSIAN_API_TOKEN` - API token from https://id.atlassian.com/manage/api-tokens
  - `JIRA_URL` - Your Atlassian instance URL (e.g., https://your-domain.atlassian.net)

**Execution pattern:**
```bash
uv run --no-project --with requests python scripts/script_name.py [args]
```

## Available Scripts

### Confluence Operations

**Read page to markdown:**
```bash
uv run --no-project --with requests python scripts/confluence_api.py read <page_id> -o output.md
```

**Update page from file (requires `-f`):**
```bash
# From markdown file
uv run --no-project --with requests python scripts/confluence_api.py update <page_id> -f input.md

# From marimo HTML export (auto-detected, requires lxml)
uv run --no-project --with requests --with lxml python scripts/confluence_api.py update <page_id> -f notebook.html
```

Note: `.html` files are auto-detected and delegated to `marimo_converter.py` for conversion.

**Update with new title:**
```bash
uv run --no-project --with requests python scripts/confluence_api.py update <page_id> -f input.md -t "New Title"
```

**Get page tree (descendants):**
```bash
# All descendants
uv run --no-project --with requests python scripts/confluence_api.py tree <page_id>

# Direct children only
uv run --no-project --with requests python scripts/confluence_api.py tree <page_id> -d root

# Save to JSON file
uv run --no-project --with requests python scripts/confluence_api.py tree <page_id> -o tree.json
```

**Create new page:**
```bash
# Create empty page under parent page or folder
uv run --no-project --with requests python scripts/confluence_api.py create <parent_id> -t "Page Title"

# Create page with content from markdown file
uv run --no-project --with requests python scripts/confluence_api.py create <parent_id> -t "Page Title" -f content.md

# Create page with inline content
uv run --no-project --with requests python scripts/confluence_api.py create <parent_id> -t "Quick Note" -c "## Content"
```

Note: `<parent_id>` can be a page ID or folder ID. The script auto-detects the parent type.

**Sync folder to Confluence:**
```bash
# Preview what would be synced (dry run)
uv run --no-project --with requests,pyyaml python scripts/confluence_api.py sync ./docs <parent_id> --dry-run

# Sync all markdown files in folder
uv run --no-project --with requests,pyyaml python scripts/confluence_api.py sync ./docs <parent_id>
```

Sync behavior:
- Files with `page_id` in frontmatter: Updates existing page
- Files without `page_id`: Creates new page, adds `page_id` to file
- Nested folders create corresponding page hierarchy
- Title from frontmatter `title` field or filename

**Upload attachment:**
```bash
# Upload file to page
uv run --no-project --with requests python scripts/confluence_api.py attach <page_id> -f image.png

# Upload with comment
uv run --no-project --with requests python scripts/confluence_api.py attach <page_id> -f chart.png -c "Analysis chart"
```

Output includes `file_id` for ADF embedding:
```
✓ Attachment 'chart.png' uploaded (id: att123456)
  Download: https://...
  File ID (for ADF): 24e522f3-af3d-4979-925f-633c41caee8c
  Collection: contentId-123456
```

Note: Use `file_id` (UUID) in ADF media nodes, not the attachment ID (`att...`).

### Marimo Notebook Conversion

Convert marimo HTML exports to Confluence pages.

**Preview marimo HTML structure:**
```bash
uv run --no-project --with requests --with lxml python scripts/marimo_converter.py preview notebook.html
```

Output shows cell count, output types (markdown, html, vegalite):
```
Notebook: CI-107_ab_test.py
Marimo version: 0.19.2
Cells: 35
Outputs: 23
Output types:
  - markdown: 11
  - html: 12
```

**Convert and update existing page:**
```bash
uv run --no-project --with requests --with lxml --with vl-convert-python --with pillow \
    python scripts/marimo_converter.py convert notebook.html --page-id 123456
```

**Convert and create new page:**
```bash
uv run --no-project --with requests --with lxml --with vl-convert-python --with pillow \
    python scripts/marimo_converter.py convert notebook.html --parent-id 123456 --title "Analysis Report"
```

Supported marimo output types:
- `text/markdown` - Rendered markdown (headings, lists, tables, code blocks)
- `text/html` - HTML outputs including marimo-table components and embedded charts
- `application/vnd.vegalite.v{3,4,5}+json` - Vega-Lite charts (rendered as PNG, uploaded as attachment)
- `text/plain` - Plain text output

Note: Requires `lxml` for HTML parsing. Add `vl-convert-python` and `pillow` for Vega-Lite chart rendering with smart width sizing.

### Jira Operations

**Export issue to markdown:**
```bash
uv run --no-project --with requests python scripts/jira_api.py read <issue_key> -o output.md
```

**Update issue fields:**
```bash
# Update summary
uv run --no-project --with requests python scripts/jira_api.py update <issue_key> -s "New Summary"

# Update description from markdown file
uv run --no-project --with requests python scripts/jira_api.py update <issue_key> -d description.md

# Set labels (replaces existing)
uv run --no-project --with requests python scripts/jira_api.py update <issue_key> -l label1 label2

# Add/remove labels
uv run --no-project --with requests python scripts/jira_api.py update <issue_key> --add-label new-label
uv run --no-project --with requests python scripts/jira_api.py update <issue_key> --remove-label old-label

# Create issue link
uv run --no-project --with requests python scripts/jira_api.py update <issue_key> --link-type "Blocks" --link-issue OTHER-123
```

Example: `uv run --no-project --with requests python scripts/jira_api.py read PROJECT-123 -o issue.md`

## Output Formats

### Confluence Pages

Saved as markdown with YAML frontmatter:

```markdown
---
title: Page Title
page_id: 123456
version: 5
status: current
---

# Page content starts here
Regular text with **bold** and *italic*.

## Code blocks
\`\`\`python
def example():
    return "hello"
\`\`\`
```

### Jira Issues

Saved as markdown with structured sections:

```markdown
# PROJECT-123: Issue Summary

## Metadata
- **Status:** Done
- **Created:** 2025-09-29T17:52:34.097+0900
- **Assignee:** John Doe (john@example.com)

## Description
Issue description content...

## Linked Issues
- **blocks:** [PROJECT-124] Related issue (In Progress)

## Comments
### Author Name - 2025-09-30T10:00:00.000+0900
Comment content...

## Work Logs
- **Worker** - 2h 30m - 2025-09-30T09:00:00.000+0900
**Total Time Logged:** 3h 30m
```

## Working with Scripts

### Typical Workflow

1. **Read Confluence page:**
   ```bash
   uv run --no-project --with requests python scripts/confluence_api.py read 123456 -o page.md
   ```

2. **Edit the markdown file** (user edits page.md)

3. **Update Confluence page:**
   ```bash
   uv run --no-project --with requests python scripts/confluence_api.py update 123456 -f page.md
   ```

### Script Modules

- `scripts/utils.py` - Authentication, environment config, file I/O
- `scripts/adf_converter.py` - ADF to Markdown conversion
- `scripts/confluence_api.py` - Confluence page operations
- `scripts/jira_api.py` - Jira issue operations
- `scripts/debug_adf.py` - Debug tool for analyzing raw ADF structure

All scripts can be imported as Python modules for programmatic use.

### Debug Tool

Analyze raw ADF structure from Confluence pages:

```bash
# List all node types in a page
uv run --no-project --with requests python scripts/debug_adf.py <page_id>

# Save raw ADF JSON
uv run --no-project --with requests python scripts/debug_adf.py <page_id> -o raw.json

# Find specific node types
uv run --no-project --with requests python scripts/debug_adf.py <page_id> --find taskList
```

## ADF Conversion

The skill handles conversion between Atlassian Document Format (ADF) and Markdown automatically.

**Supported elements:**
- Headings (h1-h6)
- Paragraphs with inline formatting (bold, italic, code, strikethrough, underline, links)
- Bullet and ordered lists (including nested)
- Task lists with checkboxes (`- [x]` / `- [ ]`)
- Code blocks with language syntax
- Blockquotes
- Tables
- Horizontal rules
- Collapsible sections (expand) as `<details>` HTML
- Smart links (inlineCard) for Confluence/Jira URLs
- Extension macros as HTML comments

**Limitations:**
- Complex tables may lose some formatting
- Extension content (e.g., Mermaid diagrams) stored externally is not available via API
- Color and font attributes are not preserved
- Alignment marks are ignored (no markdown equivalent)

## Error Handling

Scripts will raise exceptions for:
- Missing environment variables
- Authentication failures (401)
- Permission errors (403)
- Resource not found (404)
- Rate limiting (429)
- Server errors (500+)

For rate limiting, implement exponential backoff or wait for the duration specified in the `Retry-After` header.

## API Reference

For detailed API information including endpoints, ADF structure, error codes, and rate limiting details, see [references/api_reference.md](references/api_reference.md).

## Troubleshooting

**Environment variables not set:**
```bash
# Windows Command Prompt
set ATLASSIAN_USER_EMAIL=your_email@domain.com
set ATLASSIAN_API_TOKEN=your_token
set JIRA_URL=https://your-domain.atlassian.net

# Windows PowerShell
$env:ATLASSIAN_USER_EMAIL="your_email@domain.com"
$env:ATLASSIAN_API_TOKEN="your_token"
$env:JIRA_URL="https://your-domain.atlassian.net"
```

**Permission errors:**
Verify API token has appropriate permissions for the space/project.

**Version conflicts:**
When updating Confluence pages, ensure you're working with the latest version. The script automatically increments the version number.
