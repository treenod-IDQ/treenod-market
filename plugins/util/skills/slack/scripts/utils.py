"""Common utilities for Slack API operations."""

import os
import re
import requests

SLACK_BASE_URL = "https://slack.com/api"


class SlackAPIError(Exception):
    """Slack API returned ok=false."""

    pass


def get_token() -> str:
    """
    Get Slack bot token from environment.

    Returns:
        str: Bot token

    Raises:
        EnvironmentError: If SLACK_BOT_TOKEN not set
    """
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise EnvironmentError("Missing required environment variable: SLACK_BOT_TOKEN")
    return token


def slack_request(method: str, params: dict = None) -> dict:
    """
    Make authenticated request to Slack API.

    Args:
        method: API method name (e.g., 'conversations.history')
        params: Query parameters

    Returns:
        dict: API response

    Raises:
        EnvironmentError: If token not configured
        requests.HTTPError: If HTTP request fails
        SlackAPIError: If Slack returns ok=false
    """
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{SLACK_BASE_URL}/{method}"

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()

    data = response.json()
    if not data.get("ok"):
        error = data.get("error", "unknown_error")
        raise SlackAPIError(f"Slack API error: {error}")

    return data


def parse_message_link(link: str) -> tuple:
    """
    Extract channel_id and timestamp from Slack message link.

    Args:
        link: Slack message permalink
              Format: https://{workspace}.slack.com/archives/{channel}/p{ts}

    Returns:
        tuple: (channel_id, timestamp)

    Raises:
        ValueError: If link format invalid
    """
    pattern = r"archives/([A-Z0-9]+)/p(\d+)"
    match = re.search(pattern, link)
    if not match:
        raise ValueError(f"Invalid Slack message link: {link}")

    channel_id = match.group(1)
    # Convert p1234567890123456 to 1234567890.123456
    ts_raw = match.group(2)
    timestamp = f"{ts_raw[:10]}.{ts_raw[10:]}"

    return channel_id, timestamp
