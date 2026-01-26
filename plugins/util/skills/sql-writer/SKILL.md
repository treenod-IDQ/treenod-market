---
name: sql-writer
description: Write and validate Databricks SQL queries for game analytics. Use when user needs to (1) query game event data from Databricks, (2) analyze user behavior metrics (retention, funnel, DAU), (3) explore table schemas, (4) validate SQL syntax, (5) get sample data from production tables, or (6) research log event specifications. Covers litemeta, linkpang, pkpkg, matchflavor, matchwitch, traincf games.
---

## Prerequisites

Environment variables: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`

For log spec lookup: Google Cloud auth via `gcloud auth application-default login`

## Scripts

Run from skill directory.

### log_spec.py - Log Specification Lookup

```bash
uv run scripts/log_spec.py --list-games                           # List available games
uv run scripts/log_spec.py --game litemeta --list-sheets          # List spec sheets
uv run scripts/log_spec.py --game litemeta --event stageClose     # Get event spec
uv run scripts/log_spec.py --game litemeta --field playId         # Search field
uv run scripts/log_spec.py --game litemeta --event login --cache  # Use cache
```

### schema.py - Table Metadata

```bash
uv run scripts/schema.py <table>                          # Get schema
uv run scripts/schema.py --list-databases                 # List databases
uv run scripts/schema.py --list-tables <database>         # List tables
```

### validate.py - Query Validation

```bash
uv run scripts/validate.py -q "<sql>"                     # Validate query
uv run scripts/validate.py -f query.sql --check-tables    # Check tables exist
```

### sample.py - Execute Query

Requires partition filter (`dt`, `log_date`) to prevent full table scans.

```bash
uv run scripts/sample.py -q "SELECT * FROM table WHERE dt = '2024-01-01' LIMIT 10"
uv run scripts/sample.py -f query.sql --limit 100 --output results.csv
uv run scripts/sample.py -q "..." --no-filter-check       # Skip filter check (caution)
```

## References

- `references/index.md` - Database overview and common schema
- `references/log-specs.md` - Log specification sources and event documentation
- `references/{game}_production.md` - Table catalogs per game

Database catalogs:
- `litemeta_production.md` - 46 tables
- `linkpang_production.md` - 39 tables
- `pkpkg_production.md` - 36 tables
- `matchflavor_production.md` - 10 tables
- `matchwitch_production.md` - 4 tables
- `traincf_production.md` - 4 tables

## Workflow

### Standard Query Writing

1. **Understand** - Parse request: project, metrics, date range
2. **Research** - Look up log specs for unfamiliar events (see below)
3. **Search** - Check catalog for relevant tables
4. **Validate** - Run `schema.py` to confirm columns
5. **Sample** - Test query with `sample.py` (use partition filter)
6. **Deliver** - Provide query + tables used + assumptions

### When to Research Log Specs

Use `log_spec.py` when:
- Event type is unfamiliar or undocumented
- Need to understand `properties` field contents
- Need to know when/why an event fires
- Cross-referencing spec vs actual data
- Building queries involving `gameData` extraction

Example research flow:
```bash
# 1. Check what sheets exist
uv run scripts/log_spec.py --game litemeta --list-sheets

# 2. Get event specification
uv run scripts/log_spec.py --game litemeta --event stageClose

# 3. Search for specific field
uv run scripts/log_spec.py --game litemeta --field playId
```

### Complex Research Tasks

For multi-topic investigation (log specs + codebase + existing queries), use the log-data-researcher agent:

```
Agent: ~/.claude/agents/log-data-researcher.md

Capabilities:
- Read log specs from Google Sheets
- Cross-reference with codebase implementations
- Document field definitions and data types
- Check production table schemas
```

Launch via Task tool with `subagent_type=general-purpose`:
```
Prompt: Research log specifications for {game}.
Include agent instructions from ~/.claude/agents/log-data-researcher.md
Focus on: {specific events or fields}
```

## Safety

- Read-only: SELECT, EXPLAIN, DESCRIBE, SHOW only
- Partition filter required by default
- 60s timeout, 10000 row limit

## Common Patterns

### Properties Field Extraction

```sql
SELECT
    properties:playId::string as play_id,
    properties:stage::int as stage,
    properties:result::string as result
FROM litemeta_production.stageclose
WHERE dt = '2024-01-01'
```

### Session Calculation

```sql
-- 10-minute session timeout
CASE
    WHEN next_timestamp IS NULL
        OR (next_timestamp - timestamp) / 1000 > 600
    THEN 1 ELSE 0
END as is_session_end
```

### Retention Query Pattern

See `templates/retention.sql` for D1/D3/D7 retention template.

### Funnel Analysis Pattern

See `templates/funnel.sql` for conversion funnel template.
