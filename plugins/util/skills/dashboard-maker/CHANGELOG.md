# Changelog

## [0.2.0] - 2026-02-11

### Added

- New widget builders: line_widget, pie_widget, combo_widget, single_select_filter
- Validation in build_config():
  - Detects `\r\n` in queryLines
  - Detects name collisions between datasets and widgets
  - Detects widget references to non-existent datasets

### Fixed

- Fixed lakeview-guide.md: replaced `\r\n` with `\n` in all query examples
- Fixed lakeview-guide.md: API usage section now shows correct Dashboard object wrapper, warehouse_id, etag, and publish() calls

### Changed

- Restructured SKILL.md to standard pattern (prerequisites, widget builders table, validation, troubleshooting)

### Documentation

- Added README.md with Korean setup guide
- Added CHANGELOG.md

## [0.1.0] - 2026-02-10

### Added

- Initial dashboard-maker skill
- Widget builders: text_widget, counter_widget, bar_widget, table_widget, date_range_filter, multi_select_filter
- create_dashboard and update_dashboard functions with SDK Dashboard object wrapper
- Lakeview JSON structure reference guide
