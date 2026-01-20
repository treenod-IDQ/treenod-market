# Changelog

## [0.10.0] - 2025-01-20

### Added

- Extract and render vegalite charts from `<marimo-mime-renderer>` elements
  - Added `_extract_vegalite_from_html()` to parse vegalite specs embedded in HTML outputs
  - Added `_remove_mime_renderers_from_html()` to clean HTML after extraction
  - Charts are rendered to PNG and uploaded as Confluence attachments
  - Fixes issue where marimo charts were not visible in Confluence pages

- Smart image width capping for Confluence container (760px)
  - Images larger than 760px are scaled down to fit container
  - Images smaller than 760px retain original size (no stretching)
  - Uses Pillow to detect image dimensions before upload
  - Updated `create_media_single_node()` to support `width_type` parameter

### Fixed

- Fixed marimo-table decimal precision
  - Added `_format_cell_value()` to round floats to 4 decimal places
  - Integers like `5.0` now display as `5`
  - Example: `0.8516127509168958` → `0.8516`

- Fixed list item inline content loss
  - `_process_list_item()` now preserves inline formatting (bold, italic, links) when nested lists present
  - Previously, text like `**타겟 변수**: d3` before nested list was lost

- Fixed `span.markdown` wrapper not being traversed
  - `_get_block_children()` now recursively processes `span.markdown` children
  - Fixes issue where markdown content wrapped in span was skipped

### Changed

- `marimo_converter.py`: Vega-Lite detection now supports v3, v4, v5+
  - Changed from exact match `application/vnd.vegalite.v5+json` to prefix match
  - Enables conversion of notebooks using older vega-lite versions

## [0.9.0] - 2025-01-14

### Added

- ADF spacing for better Confluence rendering
  - Added `add_spacing_before_blocks()` function to both converters
  - Inserts empty paragraph before horizontal rules (`---`) and h2-h4 headings
  - Improves visual separation in Confluence pages with cramped default line-height

### Changed

- `adf_converter.py`: `markdown_to_adf()` now applies spacing post-processing
- `html_to_adf.py`: `html_to_adf()` now applies spacing post-processing

### Documentation

- Added `docs/spec/adf-spacing.md` specification

## [0.8.0] - 2026-01-13

### Fixed

- Fixed marimo HTML conversion missing `<marimo-table>` components
  - Added `create_marimo_table_adf()` to parse marimo-table data-data attribute
  - Updated `_get_block_children()` to traverse marimo-ui-element wrappers
  - Added handler for marimo-ui-element in `convert_element_to_adf()`
  - Tables stored as escaped JSON in data-data are now properly converted to ADF tables

### Changed

- `html_to_adf.py` now handles marimo custom web components:
  - `<marimo-table>` - Extracts JSON from data-data attribute, converts to ADF table
  - `<marimo-ui-element>` - Traverses children to find convertible content

## [0.7.0] - 2025-01-13

### Changed

- `confluence_api.py update` now auto-detects `.html` files
  - Automatically delegates to `marimo_converter.py` for HTML files
  - Same command works for both markdown and marimo HTML exports
  - Fixes issue where HTML files were uploaded as raw text instead of converted

### Fixed

- Fixed circular import by using local import for `marimo_converter`

## [0.6.0] - 2025-01-13

### Added

#### Marimo Notebook Converter
- `marimo_converter.py` - Convert marimo HTML exports to Confluence pages
  - Extracts `__MARIMO_MOUNT_CONFIG__` from marimo HTML exports
  - Converts cell outputs to ADF nodes
  - Auto-extracts page title from first H1, removes duplicate
  - Uploads Vega-Lite charts as PNG attachments
  - CLI: `convert <html_file> --page-id <id>` or `--parent-id <id>`
  - CLI: `preview <html_file>` to inspect structure without uploading

#### HTML to ADF Conversion
- `html_to_adf.py` - lxml-based HTML to ADF conversion
  - Supports: headings, paragraphs, lists (nested), tables, code blocks
  - Inline formatting: bold, italic, code, links, underline, strike
  - Special handling for marimo's `span.paragraph` wrapper

#### Vega-Lite Renderer
- `vegalite_renderer.py` - Render Vega-Lite specs to PNG
  - Uses vl-convert-python for native rendering
  - 2x scale factor for high-resolution charts
  - CLI for standalone chart rendering

### Changed

#### Documentation Reorganization
- Reorganized `docs/` folder structure:
  - `docs/spec/` - Implementation specifications
  - `docs/research/` - API research documents
  - `docs/samples/` - Sample API responses
  - `docs/tests/` - Integration test scripts
- Added `docs/README.md` as index for all documentation
- Renamed files for clarity:
  - `SPEC.md` -> `spec/implementation.md`
  - `RESEARCH_DOCUMENT.md` -> `research/atlassian-api.md`

### Dependencies

- New: `lxml` for HTML parsing
- New: `vl-convert-python` for Vega-Lite rendering

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
