# /// script
# requires-python = ">=3.11"
# dependencies = ["google-auth", "google-api-python-client"]
# ///
"""
Log Specification Lookup Tool

Wrapper for reading log event specifications from Google Sheets.
Uses the sheet skill API to access log spec documents.

Usage:
    uv run scripts/log_spec.py --game litemeta --list-sheets
    uv run scripts/log_spec.py --game litemeta --event stageClose
    uv run scripts/log_spec.py --game litemeta --field playId
    uv run scripts/log_spec.py --game litemeta --event stageClose --cache
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Game to Spreadsheet ID mapping
GAME_SHEETS = {
    "litemeta": {
        "id": "1rnrv-64ODKkjOMxF6hETyAai4juNQYEFUyAcgPZqj04",
        "name": "글로벌 포코포코",
        "url": "https://docs.google.com/spreadsheets/d/1rnrv-64ODKkjOMxF6hETyAai4juNQYEFUyAcgPZqj04/edit",
    },
    "lovecruise": {
        "id": "1JB90AveO5RHlWZNLoj3rhJZh9bIppluhL6yZq8_Rnc4",
        "name": "글로벌 러브크루즈",
        "url": "https://docs.google.com/spreadsheets/d/1JB90AveO5RHlWZNLoj3rhJZh9bIppluhL6yZq8_Rnc4/edit",
    },
    "pokorinkle": {
        "id": "16Hn6GQYxQhcckEEHzz193kGbOyVkQnF85kCEsARDZns",
        "name": "글로벌 포코링클",
        "url": "https://docs.google.com/spreadsheets/d/16Hn6GQYxQhcckEEHzz193kGbOyVkQnF85kCEsARDZns/edit",
    },
}

# Cache directory
CACHE_DIR = Path.home() / ".cache" / "sql-writer" / "log-specs"


def get_sheets_service():
    """Get authenticated Google Sheets service."""
    from google.auth import default
    from googleapiclient.discovery import build

    creds, _ = default(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    return build("sheets", "v4", credentials=creds)


def get_cache_path(game: str, key: str) -> Path:
    """Get cache file path for a specific query."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{game}_{key}.json"


def read_cache(game: str, key: str) -> Optional[dict]:
    """Read from cache if exists and fresh (< 24h)."""
    cache_path = get_cache_path(game, key)
    if not cache_path.exists():
        return None

    import time
    if time.time() - cache_path.stat().st_mtime > 86400:  # 24 hours
        return None

    with open(cache_path) as f:
        return json.load(f)


def write_cache(game: str, key: str, data: dict):
    """Write data to cache."""
    cache_path = get_cache_path(game, key)
    with open(cache_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_sheets(game: str, use_cache: bool = False) -> list[dict]:
    """List available sheets in the game's log spec spreadsheet."""
    if use_cache:
        cached = read_cache(game, "sheets")
        if cached:
            return cached["sheets"]

    if game not in GAME_SHEETS:
        print(f"[ERROR] Unknown game: {game}", file=sys.stderr)
        print(f"Available games: {', '.join(GAME_SHEETS.keys())}", file=sys.stderr)
        sys.exit(1)

    spreadsheet_id = GAME_SHEETS[game]["id"]
    service = get_sheets_service()

    result = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = [
        {"title": s["properties"]["title"], "index": s["properties"]["index"]}
        for s in result.get("sheets", [])
    ]

    if use_cache:
        write_cache(game, "sheets", {"sheets": sheets})

    return sheets


def get_event_spec(game: str, event: str, use_cache: bool = False) -> dict:
    """Get specification for a specific event type."""
    cache_key = f"event_{event}"
    if use_cache:
        cached = read_cache(game, cache_key)
        if cached:
            return cached

    if game not in GAME_SHEETS:
        print(f"[ERROR] Unknown game: {game}", file=sys.stderr)
        sys.exit(1)

    spreadsheet_id = GAME_SHEETS[game]["id"]
    service = get_sheets_service()

    # First, get list of sheets to find matching event
    sheets = list_sheets(game, use_cache)
    matching_sheets = [s for s in sheets if event.lower() in s["title"].lower()]

    if not matching_sheets:
        # Try reading from index/overview sheet
        return search_event_in_overview(service, spreadsheet_id, event, sheets)

    # Read the first matching sheet
    sheet_name = matching_sheets[0]["title"]
    range_name = f"'{sheet_name}'!A:Z"

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    values = result.get("values", [])
    spec = parse_event_sheet(sheet_name, values)

    if use_cache:
        write_cache(game, cache_key, spec)

    return spec


def search_event_in_overview(service, spreadsheet_id: str, event: str, sheets: list) -> dict:
    """Search for event in overview/index sheet."""
    # Common overview sheet names
    overview_names = ["overview", "index", "목록", "이벤트목록", "action"]
    overview_sheet = None

    for sheet in sheets:
        if any(name in sheet["title"].lower() for name in overview_names):
            overview_sheet = sheet["title"]
            break

    if not overview_sheet:
        overview_sheet = sheets[0]["title"] if sheets else None

    if not overview_sheet:
        return {"error": f"Event '{event}' not found and no overview sheet available"}

    range_name = f"'{overview_sheet}'!A:Z"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    values = result.get("values", [])

    # Search for event in values
    matches = []
    headers = values[0] if values else []

    for i, row in enumerate(values[1:], start=2):
        for j, cell in enumerate(row):
            if event.lower() in str(cell).lower():
                matches.append({
                    "row": i,
                    "column": headers[j] if j < len(headers) else f"Col{j}",
                    "value": cell,
                    "row_data": dict(zip(headers, row)) if headers else row
                })

    return {
        "event": event,
        "source_sheet": overview_sheet,
        "matches": matches[:10],  # Limit to 10 matches
        "total_matches": len(matches)
    }


def parse_event_sheet(sheet_name: str, values: list) -> dict:
    """Parse event sheet data into structured format."""
    if not values:
        return {"sheet": sheet_name, "fields": [], "error": "Empty sheet"}

    headers = values[0]
    rows = values[1:]

    fields = []
    for row in rows:
        if not row or not row[0]:  # Skip empty rows
            continue
        field = dict(zip(headers, row + [""] * (len(headers) - len(row))))
        fields.append(field)

    return {
        "sheet": sheet_name,
        "headers": headers,
        "fields": fields,
        "field_count": len(fields)
    }


def search_field(game: str, field: str, use_cache: bool = False) -> dict:
    """Search for a field across all event sheets."""
    cache_key = f"field_{field}"
    if use_cache:
        cached = read_cache(game, cache_key)
        if cached:
            return cached

    if game not in GAME_SHEETS:
        print(f"[ERROR] Unknown game: {game}", file=sys.stderr)
        sys.exit(1)

    spreadsheet_id = GAME_SHEETS[game]["id"]
    service = get_sheets_service()

    sheets = list_sheets(game, use_cache)
    results = []

    for sheet in sheets[:20]:  # Limit to first 20 sheets
        try:
            range_name = f"'{sheet['title']}'!A:Z"
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get("values", [])
            for i, row in enumerate(values):
                for j, cell in enumerate(row):
                    if field.lower() in str(cell).lower():
                        headers = values[0] if values else []
                        results.append({
                            "sheet": sheet["title"],
                            "row": i + 1,
                            "column": headers[j] if j < len(headers) else f"Col{j}",
                            "value": cell,
                            "context": row
                        })
        except Exception as e:
            continue  # Skip sheets that fail to read

    output = {
        "field": field,
        "game": game,
        "matches": results[:20],  # Limit results
        "total_matches": len(results)
    }

    if use_cache:
        write_cache(game, cache_key, output)

    return output


def clear_cache(game: Optional[str] = None):
    """Clear cached data."""
    if not CACHE_DIR.exists():
        print("No cache to clear")
        return

    if game:
        # Clear specific game cache
        for f in CACHE_DIR.glob(f"{game}_*.json"):
            f.unlink()
        print(f"Cleared cache for {game}")
    else:
        # Clear all cache
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()
        print("Cleared all cache")


def format_output(data: dict, format_type: str = "json") -> str:
    """Format output data."""
    if format_type == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif format_type == "table":
        # Simple table format for lists
        if "fields" in data:
            lines = [f"Sheet: {data.get('sheet', 'Unknown')}"]
            lines.append("-" * 60)
            for field in data.get("fields", [])[:20]:
                lines.append(" | ".join(str(v)[:30] for v in field.values()))
            return "\n".join(lines)
        elif "matches" in data:
            lines = [f"Found {data.get('total_matches', 0)} matches"]
            lines.append("-" * 60)
            for match in data.get("matches", []):
                lines.append(f"{match.get('sheet', '')}:{match.get('row', '')} - {match.get('value', '')}")
            return "\n".join(lines)
        return json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


def main():
    parser = argparse.ArgumentParser(
        description="Log Specification Lookup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List available sheets for a game:
    uv run scripts/log_spec.py --game litemeta --list-sheets

  Get event specification:
    uv run scripts/log_spec.py --game litemeta --event stageClose

  Search for a field:
    uv run scripts/log_spec.py --game litemeta --field playId

  Use cache for faster lookups:
    uv run scripts/log_spec.py --game litemeta --event stageClose --cache

  Clear cache:
    uv run scripts/log_spec.py --clear-cache
    uv run scripts/log_spec.py --game litemeta --clear-cache
        """
    )

    parser.add_argument("--game", "-g", help="Target game (litemeta, lovecruise, pokorinkle)")
    parser.add_argument("--list-sheets", "-l", action="store_true", help="List available sheets")
    parser.add_argument("--list-games", action="store_true", help="List available games")
    parser.add_argument("--event", "-e", help="Get specification for event type")
    parser.add_argument("--field", "-f", help="Search for field across sheets")
    parser.add_argument("--cache", "-c", action="store_true", help="Use cache for faster lookups")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cached data")
    parser.add_argument("--format", choices=["json", "table"], default="json", help="Output format")

    args = parser.parse_args()

    # Handle list-games
    if args.list_games:
        print("Available games:")
        for game, info in GAME_SHEETS.items():
            print(f"  {game}: {info['name']}")
            print(f"    URL: {info['url']}")
        return

    # Handle clear-cache
    if args.clear_cache:
        clear_cache(args.game)
        return

    # Require game for other operations
    if not args.game:
        parser.print_help()
        print("\n[ERROR] --game is required for this operation", file=sys.stderr)
        sys.exit(1)

    if args.game not in GAME_SHEETS:
        print(f"[ERROR] Unknown game: {args.game}", file=sys.stderr)
        print(f"Available games: {', '.join(GAME_SHEETS.keys())}", file=sys.stderr)
        sys.exit(1)

    # Execute requested operation
    try:
        if args.list_sheets:
            sheets = list_sheets(args.game, args.cache)
            print(f"Sheets in {GAME_SHEETS[args.game]['name']}:")
            for sheet in sheets:
                print(f"  [{sheet['index']}] {sheet['title']}")

        elif args.event:
            result = get_event_spec(args.game, args.event, args.cache)
            print(format_output(result, args.format))

        elif args.field:
            result = search_field(args.game, args.field, args.cache)
            print(format_output(result, args.format))

        else:
            # Default: show game info
            info = GAME_SHEETS[args.game]
            print(f"Game: {info['name']}")
            print(f"Spreadsheet: {info['url']}")
            print(f"\nUse --list-sheets to see available sheets")
            print(f"Use --event <name> to get event specification")
            print(f"Use --field <name> to search for a field")

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
