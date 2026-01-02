# Changelog

## [0.5.1] - 2025-01-02

### Fixed

- `jira_api.py` CLI now matches documented interface
  - Added subcommand support (`read`, `update`) as documented in SKILL.md
  - Previously only accepted `<issue_key>` as first argument without subcommand
  - Implemented `update_jira_issue` function (was documented but missing)

### Known Issues

- `confluence_api.py` `sync` command documented but not implemented (TODO added)

## [0.5.0] - 2024-12-23

### Added

#### Confluence Attachment Upload
- `upload_attachment` function to upload files to Confluence pages
  - Supports image files (PNG, JPG, GIF, SVG) and documents (PDF)
  - Returns `file_id` and `collection` for ADF media node embedding
  - Auto-detects MIME type from file extension
- New CLI command: `attach <page_id> -f <file> [-c <comment>]`
- ADF media node support for embedded images:
  ```json
  {"type": "mediaSingle", "content": [{"type": "media", "attrs": {"type": "file", "id": "<file_id>", "collection": "<collection>"}}]}
  ```

#### Folder Support for Page Creation
- `create_confluence_page` now supports folder IDs as parent
  - Tries folder API first, falls back to page API
  - Enables creating pages directly in Confluence folders

### Documentation

- Added `README.md` with setup guide
  - Korean font setup for chart export (Noto Sans CJK)
  - `VL_CONVERT_FONT_DIR` environment variable configuration
  - Troubleshooting guide for image embedding
- Added attachment upload API endpoint to `api_reference.md`
- Added ADF media node specification to `adf-converter-spec.md`
- Updated `SPEC.md` with `upload_attachment` function specification

### Notes

- When embedding images in ADF, use `file_id` (UUID format), not attachment ID (`att...`)
- Updating existing attachments requires different endpoint: `POST .../attachment/{id}/data`

## [0.4.1] - 2024-12-22

### Added

- Parent issue support in `jira_api.py`
  - Fetches `parent` field from Jira API
  - Displays parent in metadata: `- **Parent:** [PARENT-KEY] Parent Summary`
  - Useful for tracking subtask relationships

## [0.4.0] - 2024-12-22

### Added

#### Jira Issue Updates
- `update_jira_issue` function to modify issue fields
  - Update summary (`-s/--summary`)
  - Update description from markdown file (`-d/--description`)
  - Set labels directly (`-l/--labels`)
  - Add/remove individual labels (`--add-label`, `--remove-label`)
  - Create issue links (`--link-type`, `--link-issue`, `--link-direction`)
- `read_jira_issue_metadata` helper function
- New CLI subcommands: `read`, `update` (breaking change from previous single-command format)

#### Confluence Page Creation
- `create_confluence_page` function to create new pages under a parent
  - Accepts markdown file (`-f`) or inline content (`-c`)
  - Auto-derives space ID from parent page
  - Returns page URL in result
- New CLI command: `create <parent_id> -t "Title" [-f file.md] [-c "content"]`

#### Confluence Folder Sync
- `sync_folder_to_confluence` function for batch page sync
  - Syncs all .md files in a folder to Confluence
  - Files with `page_id` in frontmatter: Updates existing page
  - Files without `page_id`: Creates new page, writes `page_id` back to file
  - Nested folder structure creates corresponding page hierarchy
  - `--dry-run` flag to preview changes without executing
- Helper functions: `parse_frontmatter`, `update_frontmatter`, `get_or_create_child_page`
- New CLI command: `sync <folder> <parent_id> [--dry-run]`
- Requires `pyyaml` dependency for frontmatter parsing

### Documentation

- Added Jira update API endpoints (PUT issue, POST issueLink) to api_reference.md
- Added Confluence create page API endpoint (POST pages) to api_reference.md
- Updated SKILL.md with all new command examples
- Updated SPEC.md with full function specifications

## [0.3.0] - 2024-12-15

### Added

- `get_page_tree` function to retrieve page descendants (page tree)
  - Supports both all descendants and direct children only via `depth` parameter
  - Handles pagination automatically for large page trees
- New CLI command `tree` for `confluence_api.py`
  - `tree <page_id>` - get all descendants
  - `tree <page_id> -d root` - get direct children only
  - `tree <page_id> -o tree.json` - save to JSON file

### Documentation

- Added descendants/children API endpoints to api_reference.md
- Updated SKILL.md with tree command usage examples

## [0.2.0] - 2024-12-12

### Fixed

- Nested bullet lists now properly convert to ADF structure (max depth 3)
  - Previously flattened all list items to single level
  - Now creates proper nested `bulletList` inside parent `listItem`
- Fixed infinite loop when indented bullet follows numbered list
  - `parse_bullet_list` now starts with correct base indent
- Improved `parse_inline_markdown` performance
  - Pre-compiled regex patterns
  - Find earliest match instead of iterating all patterns per match
- Added markdown table to ADF conversion
- Fixed indented code blocks not being detected

### Changed

- `-o` flag is now optional for read commands
  - `confluence_api.py read` defaults to `confluence_<page_id>.md`
  - `jira_api.py` defaults to `<issue_key>.md`

### Documentation

- Added nested list ADF structure example to API reference

## [0.1.0] - 2024-12-11

Initial release of the Atlassian skill for Claude Code.

### Features

- Confluence page read/update via REST API v2
- Jira issue export with comments and worklogs
- Automatic ADF (Atlassian Document Format) to Markdown conversion

### ADF Converter

Supported node types:
- doc, paragraph, heading (h1-h6)
- bulletList, orderedList, listItem (with nesting)
- taskList, taskItem (checkboxes with DONE/TODO state)
- codeBlock (with language syntax)
- blockquote, rule (horizontal line)
- table, tableRow, tableCell, tableHeader
- expand (collapsible sections as `<details>` HTML)
- inlineCard (Confluence/Jira smart links)
- extension (macros as HTML comments)
- text with marks (strong, em, code, strike, underline, link)
- hardBreak, emoji, mention

### Scripts

- `confluence_api.py` - Read and update Confluence pages
- `jira_api.py` - Export Jira issues to markdown
- `adf_converter.py` - ADF to Markdown bidirectional conversion
- `utils.py` - Authentication and file utilities
- `debug_adf.py` - Debug tool for analyzing raw ADF structure

### Documentation

- `SKILL.md` - Usage guide and API reference
- `docs/adf-converter-spec.md` - ADF converter implementation spec
- `docs/SPEC.md` - Original skill specification
- `references/api_reference.md` - Atlassian API reference
