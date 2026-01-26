# Changelog

## [0.2.0] - 2025-01-26

### Added

#### Log Specification Research
- `scripts/log_spec.py` - Log specification lookup from Google Sheets
  - `--list-games` - List available games with spec sheets
  - `--game <name> --list-sheets` - List sheets in game spec
  - `--game <name> --event <name>` - Get event specification
  - `--game <name> --field <name>` - Search field across events
  - `--cache` flag for faster repeated lookups
  - Wraps sheet skill API for seamless access

- `references/log-specs.md` - Log specification reference
  - Game-to-Sheet URL mappings (litemeta, lovecruise, pokorinkle)
  - Common event types documentation (login, stageStart, stageClose, goods)
  - Properties and gameData field extraction patterns
  - Session calculation pattern (600s timeout)
  - Confluence reference link

### Changed

- `SKILL.md` workflow expanded from 5 to 6 steps
  - Added **Research** step between Understand and Search
  - Documents when to use log_spec.py (unfamiliar events, properties fields)
  - References `~/.claude/agents/log-data-researcher.md` for complex research

### Notes

- Merged functionality from `~/.claude/skills/research-orchestration/` (now deprecated)
- Log-data-researcher agent kept as reusable component at `~/.claude/agents/`

## [0.1.0] - 2025-01-15

### Added

- Initial sql-writer skill release
- Databricks SQL query writing and validation
- Table schema lookup via `schema.py`
- Query validation via `validate.py`
- Query execution via `sample.py` with partition filter requirement
- Reference catalogs for 6 games (litemeta, linkpang, pkpkg, matchflavor, matchwitch, traincf)
- SQL templates (retention, funnel, cohort)
