#!/usr/bin/env python3
"""Slack API operations."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import slack_request, parse_message_link, SlackAPIError
import re


def detect_input_type(input_str: str) -> tuple[str, dict]:
    """Returns (type, parsed_data) where type is 'channel', 'thread', 'link', or 'unknown'"""
    if "slack.com/archives/" in input_str:
        return "link", {"link": input_str}

    # Check for channel:thread_ts format (e.g., G4CDARPJ7:1770094319.078559)
    thread_match = re.match(r"^([CGD][A-Z0-9]{8,}):(\d{10}\.\d+)$", input_str)
    if thread_match:
        return "thread", {
            "channel_id": thread_match.group(1),
            "thread_ts": thread_match.group(2),
        }

    if re.match(r"^[CGD][A-Z0-9]{8,}$", input_str):
        return "channel", {"channel_id": input_str}

    return "unknown", {}


def read_channel(channel_id: str, limit: int = 100) -> dict:
    info_result = slack_request("conversations.info", {"channel": channel_id})
    channel_info = info_result.get("channel", {})

    history_result = slack_request(
        "conversations.history", {"channel": channel_id, "limit": limit}
    )

    return {
        "channel": {
            "id": channel_info.get("id"),
            "name": channel_info.get("name"),
            "topic": channel_info.get("topic", {}).get("value", ""),
            "purpose": channel_info.get("purpose", {}).get("value", ""),
        },
        "messages": history_result.get("messages", []),
        "has_more": history_result.get("has_more", False),
    }


def read_thread(channel_id: str, thread_ts: str) -> dict:
    result = slack_request(
        "conversations.replies", {"channel": channel_id, "ts": thread_ts}
    )

    return {
        "channel_id": channel_id,
        "thread_ts": thread_ts,
        "messages": result.get("messages", []),
        "reply_count": len(result.get("messages", [])) - 1,
    }


def read_from_link(message_link: str, limit: int = 50) -> dict:
    channel_id, timestamp = parse_message_link(message_link)

    result = slack_request(
        "conversations.history",
        {
            "channel": channel_id,
            "oldest": timestamp,
            "limit": limit + 1,
            "inclusive": "true",
        },
    )

    return {
        "channel_id": channel_id,
        "target_ts": timestamp,
        "messages": result.get("messages", []),
        "has_more": result.get("has_more", False),
    }


def format_timestamp(ts: str) -> str:
    from datetime import datetime

    try:
        dt = datetime.fromtimestamp(float(ts))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return ts


def format_text(data: dict, command: str) -> str:
    lines = []

    if command == "channel":
        ch = data.get("channel", {})
        lines.append(f"Channel: #{ch.get('name', 'unknown')} ({ch.get('id', '')})")
        if ch.get("topic"):
            lines.append(f"Topic: {ch.get('topic')}")
        lines.append(
            f"Messages: {len(data.get('messages', []))} (has_more: {data.get('has_more', False)})"
        )
        lines.append("---")

    elif command == "thread":
        lines.append(f"Thread in {data.get('channel_id', '')}")
        lines.append(f"Thread TS: {data.get('thread_ts', '')}")
        lines.append(f"Replies: {data.get('reply_count', 0)}")
        lines.append("---")

    elif command == "link":
        lines.append(f"Channel: {data.get('channel_id', '')}")
        lines.append(f"Starting from: {data.get('target_ts', '')}")
        lines.append(f"Messages: {len(data.get('messages', []))}")
        lines.append("---")

    for msg in data.get("messages", []):
        ts = format_timestamp(msg.get("ts", ""))
        user = msg.get("user", "unknown")
        text = msg.get("text", "")

        lines.append(f"[{ts}] {user}")
        lines.append(text)

        if msg.get("reactions"):
            reactions = ", ".join(
                [f":{r['name']}: ({r['count']})" for r in msg["reactions"]]
            )
            lines.append(f"  Reactions: {reactions}")

        if msg.get("reply_count"):
            lines.append(f"  [Thread: {msg['reply_count']} replies]")

        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Slack API operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser(
        "read", help="Read messages (auto-detects input type)"
    )
    read_parser.add_argument("input", help="Channel ID or message link")
    read_parser.add_argument(
        "--limit", type=int, default=100, help="Message limit (default: 100)"
    )
    read_parser.add_argument(
        "--format", choices=["json", "text"], default="json", help="Output format"
    )
    read_parser.add_argument("-o", "--output", help="Output file")

    channel_parser = subparsers.add_parser("channel", help="Read channel messages")
    channel_parser.add_argument("channel_id", help="Channel ID (e.g., C04E5K9EWXX)")
    channel_parser.add_argument(
        "--limit", type=int, default=100, help="Message limit (default: 100)"
    )
    channel_parser.add_argument(
        "--format", choices=["json", "text"], default="json", help="Output format"
    )
    channel_parser.add_argument("-o", "--output", help="Output file")

    thread_parser = subparsers.add_parser("thread", help="Read thread messages")
    thread_parser.add_argument("channel_id", help="Channel ID")
    thread_parser.add_argument(
        "thread_ts", help="Thread timestamp (e.g., 1234567890.123456)"
    )
    thread_parser.add_argument(
        "--format", choices=["json", "text"], default="json", help="Output format"
    )
    thread_parser.add_argument("-o", "--output", help="Output file")

    link_parser = subparsers.add_parser("link", help="Read from message link")
    link_parser.add_argument("message_link", help="Slack message URL")
    link_parser.add_argument(
        "--limit", type=int, default=50, help="Messages to fetch (default: 50)"
    )
    link_parser.add_argument(
        "--format", choices=["json", "text"], default="json", help="Output format"
    )
    link_parser.add_argument("-o", "--output", help="Output file")

    args = parser.parse_args()
    data = {}
    detected_type = None

    try:
        if args.command == "read":
            detected_type, parsed = detect_input_type(args.input)
            if detected_type == "channel":
                data = read_channel(parsed["channel_id"], args.limit)
            elif detected_type == "thread":
                data = read_thread(parsed["channel_id"], parsed["thread_ts"])
            elif detected_type == "link":
                data = read_from_link(parsed["link"], args.limit)
            else:
                print(
                    f"Error: Could not detect input type for '{args.input}'",
                    file=sys.stderr,
                )
                print(
                    "Expected: Channel ID (G4CDARPJ7), channel:thread_ts (G4CDARPJ7:1234567890.123456), or message link",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif args.command == "channel":
            detected_type = "channel"
            data = read_channel(args.channel_id, args.limit)
        elif args.command == "thread":
            detected_type = "thread"
            data = read_thread(args.channel_id, args.thread_ts)
        elif args.command == "link":
            detected_type = "link"
            data = read_from_link(args.message_link, args.limit)

        if args.format == "json":
            output = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            format_type = detected_type if detected_type else args.command
            output = format_text(data, format_type)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Saved to {args.output}")
        else:
            print(output)

    except SlackAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
