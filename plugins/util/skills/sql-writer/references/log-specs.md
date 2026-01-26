# Log Specification Reference

Client-side log event specifications stored in Google Sheets.

## External References

- Confluence: [로그 데이터 가이드](https://treenod.atlassian.net/wiki/spaces/DataAnalysis/pages/72460666618)
- Agent: `~/.claude/agents/log-data-researcher.md`

## Game Log Specs

| Game | Project | Spreadsheet |
|------|---------|-------------|
| 글로벌 포코포코 | litemeta | [Sheet](https://docs.google.com/spreadsheets/d/1rnrv-64ODKkjOMxF6hETyAai4juNQYEFUyAcgPZqj04/edit) |
| 글로벌 러브크루즈 | lovecruise | [Sheet](https://docs.google.com/spreadsheets/d/1JB90AveO5RHlWZNLoj3rhJZh9bIppluhL6yZq8_Rnc4/edit) |
| 글로벌 포코링클 | pokorinkle | [Sheet](https://docs.google.com/spreadsheets/d/16Hn6GQYxQhcckEEHzz193kGbOyVkQnF85kCEsARDZns/edit) |

## Using log_spec.py

```bash
# List available games
uv run scripts/log_spec.py --list-games

# List sheets in game spec
uv run scripts/log_spec.py --game litemeta --list-sheets

# Get event specification
uv run scripts/log_spec.py --game litemeta --event stageClose

# Search for field
uv run scripts/log_spec.py --game litemeta --field playId

# Use cache for faster repeated lookups
uv run scripts/log_spec.py --game litemeta --event stageClose --cache
```

## Common Event Types

### Analytics Events

| Action | Table | Description | Key Fields |
|--------|-------|-------------|------------|
| login | `{db}.login` | User login | gameData.userInfo |
| stageStart | `{db}.stagestart` | Stage begin | playId, stage, properties |
| stageClose | `{db}.stageclose` | Stage end | playId, result, playTime |
| activation | `{db}.activation` | App foreground | - |
| deactivation | `{db}.deactivation` | App background | - |
| goods | `{db}.goods` | Currency change | get, use arrays |
| funnel | `{db}.funnel` | Funnel event | action, properties |

### Common Fields

| Field | Location | Description |
|-------|----------|-------------|
| uid | root | User identifier |
| dt | root | Event date (partition) |
| timestamp | root | Event time (ms) |
| properties | root | Event-specific JSON data |
| gameData | root | Game state JSON |
| playId | properties | Stage play session ID |
| stage | properties | Stage number/identifier |
| result | properties | Stage result (success, fail, etc.) |

### Properties Field Extraction

```sql
-- Extract from properties (variant type)
SELECT
    properties:playId::string as play_id,
    properties:stage::int as stage,
    properties:result::string as result,
    properties:playTime::int as play_time_ms
FROM litemeta_production.stageclose
WHERE dt = '2024-01-01'
```

### gameData Field Extraction

```sql
-- Extract user info from gameData
SELECT
    gameData:userInfo:level::int as user_level,
    gameData:userInfo:coin::bigint as coin,
    gameData:userInfo:heart::int as heart
FROM litemeta_production.login
WHERE dt = '2024-01-01'
```

## Session Calculation

Standard session timeout: 600 seconds (10 minutes)

```sql
-- Session boundary detection
WITH events AS (
    SELECT
        uid,
        timestamp,
        LEAD(timestamp) OVER (PARTITION BY uid ORDER BY timestamp) as next_timestamp
    FROM litemeta_production.activation
    WHERE dt BETWEEN '2024-01-01' AND '2024-01-07'
)
SELECT
    uid,
    timestamp as session_start,
    CASE
        WHEN next_timestamp IS NULL
            OR (next_timestamp - timestamp) / 1000 > 600
        THEN 1 ELSE 0
    END as is_session_end
FROM events
```

## Data Quality Notes

- `properties` field may be null or empty for some events
- `gameData` structure varies by game and event type
- Always validate field existence before extraction
- Check for null values in aggregations

## When to Research Log Specs

Use log_spec.py when:
- Querying unfamiliar event types
- Need field definitions not in table schema
- Understanding when/why events fire
- Checking available properties fields
- Cross-referencing spec vs actual data
