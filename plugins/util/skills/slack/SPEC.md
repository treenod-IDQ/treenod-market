---
title: Slack Skill Specification
---

## Overview

Slack API skill for Claude Code. Read channel messages, thread conversations, and messages from specific points using user token authentication.

## Requirements

### Functional Requirements

| ID | Feature | Input | Output |
|----|---------|-------|--------|
| FR-1 | Read channel messages | channel_id, count | List of messages with metadata |
| FR-2 | Read thread conversations | channel_id, thread_ts | All messages in thread |
| FR-3 | Read from message link | message_link | Messages from that point forward |

### Use Cases

#### UC-1: Read Channel Messages

```
Input:
  - channel_id: C04E5K9EWXX (from channel details or URL)
  - count: 50 (default: 100, max: 1000)

Output:
  - Channel metadata (name, topic)
  - Messages sorted by timestamp (newest first)
  - Each message: user, text, timestamp, reactions, thread info
```

#### UC-2: Read Thread Conversations

```
Input:
  - channel_id: C04E5K9EWXX
  - thread_ts: 1234567890.123456 (parent message timestamp)

Output:
  - Parent message content
  - All replies in order
  - User and timestamp for each
```

#### UC-3: Read from Message Link

```
Input:
  - message_link: https://treenod.slack.com/archives/C04E5K9EWXX/p1234567890123456

Output:
  - Extracted channel_id and timestamp
  - Target message
  - Subsequent messages (configurable count)
```

## Technical Design

### Authentication

**Token Type:** Bot Token (`xoxb-`)

Bot tokens are used because:
- Already configured and available
- Simpler setup (no user OAuth flow)
- Bot must be invited to channels to access them

**Environment Variable:**
```bash
SLACK_BOT_TOKEN=xoxb-...
```

### Bot Channel Access

Bot must be invited to each channel before it can read messages:
```
/invite @YourBotName
```

For private channels, bot must also be a member.

### Required Bot Token Scopes

| Scope | Purpose | Required |
|-------|---------|----------|
| `channels:history` | Read public channel messages | Yes |
| `channels:read` | List public channels, get channel info | Yes |
| `groups:history` | Read private channel messages | Yes |
| `groups:read` | List private channels, get channel info | Yes |
| `im:history` | Read direct messages | Optional |
| `mpim:history` | Read group DMs | Optional |
| `users:read` | Resolve user IDs to names | Optional |

**Minimum for core functionality:**
- `channels:history`, `channels:read`
- `groups:history`, `groups:read`

### API Endpoints

| Endpoint | Method | Use |
|----------|--------|-----|
| `conversations.history` | GET | Read channel messages |
| `conversations.replies` | GET | Read thread messages |
| `conversations.info` | GET | Get channel metadata |
| `users.info` | GET | Resolve user ID to name |

### Rate Limits

| Endpoint | Tier | Limit |
|----------|------|-------|
| `conversations.history` | 3 | 50+ req/min |
| `conversations.replies` | 3 | 50+ req/min |
| `conversations.info` | 4 | 100+ req/min |

Note: Rate limits for non-Marketplace apps may be more restrictive.

## File Structure

```
slack/
├── SKILL.md                    # Main skill documentation
├── SPEC.md                     # This file (development reference)
├── CHANGELOG.md                # Version history
├── research.md                 # API research (existing)
├── scripts/
│   ├── utils.py                # Auth helpers, API wrapper
│   ├── slack_api.py            # Main API implementation + CLI
│   └── message_formatter.py    # Output formatting (optional)
└── references/
    └── api_reference.md        # Detailed endpoint documentation
```

## Implementation Details

### scripts/utils.py

```python
"""Common utilities for Slack API operations."""

import os
import re
import requests

SLACK_BASE_URL = "https://slack.com/api"


def get_token() -> str:
    """Get Slack bot token from environment."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise EnvironmentError(
            "Missing required environment variable: SLACK_BOT_TOKEN"
        )
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
    pattern = r'archives/([A-Z0-9]+)/p(\d+)'
    match = re.search(pattern, link)
    if not match:
        raise ValueError(f"Invalid Slack message link: {link}")
    
    channel_id = match.group(1)
    # Convert p1234567890123456 to 1234567890.123456
    ts_raw = match.group(2)
    timestamp = f"{ts_raw[:10]}.{ts_raw[10:]}"
    
    return channel_id, timestamp


class SlackAPIError(Exception):
    """Slack API returned ok=false."""
    pass
```

### scripts/slack_api.py

Core functions:

```python
def read_channel(channel_id: str, limit: int = 100) -> dict:
    """
    Read messages from a channel.
    
    Args:
        channel_id: Channel ID (C..., G..., D...)
        limit: Number of messages (1-1000)
    
    Returns:
        dict: {channel_info, messages}
    """

def read_thread(channel_id: str, thread_ts: str) -> dict:
    """
    Read all messages in a thread.
    
    Args:
        channel_id: Channel containing the thread
        thread_ts: Parent message timestamp
    
    Returns:
        dict: {parent_message, replies}
    """

def read_from_link(message_link: str, limit: int = 50) -> dict:
    """
    Read messages starting from a message link.
    
    Args:
        message_link: Slack message permalink
        limit: Number of messages after the target
    
    Returns:
        dict: {target_message, following_messages}
    """
```

### CLI Interface

```bash
# Read channel messages
uv run --no-project --with requests python scripts/slack_api.py \
    channel C04E5K9EWXX --limit 50

# Read thread
uv run --no-project --with requests python scripts/slack_api.py \
    thread C04E5K9EWXX 1234567890.123456

# Read from message link
uv run --no-project --with requests python scripts/slack_api.py \
    link "https://treenod.slack.com/archives/C04E5K9EWXX/p1234567890123456"

# Output formats
--format json    # Raw JSON (default)
--format text    # Human-readable text
-o output.json   # Save to file
```

## Output Formats

### Channel Messages (JSON)

```json
{
  "channel": {
    "id": "C04E5K9EWXX",
    "name": "general",
    "topic": "General discussion"
  },
  "messages": [
    {
      "ts": "1234567890.123456",
      "user": "U04ABCDEF",
      "user_name": "minwoo",
      "text": "Hello world",
      "reactions": [{"name": "thumbsup", "count": 2}],
      "thread_ts": null,
      "reply_count": 0
    }
  ],
  "has_more": true,
  "next_cursor": "..."
}
```

### Channel Messages (Text)

```
Channel: #general (C04E5K9EWXX)
Topic: General discussion
Messages: 50 (has more)
---

[2025-01-15 10:30:15] minwoo
Hello world
  - thumbsup (2)

[2025-01-15 10:31:22] drew
Reply here
  [Thread: 3 replies]
```

### Thread Messages (JSON)

```json
{
  "channel_id": "C04E5K9EWXX",
  "thread_ts": "1234567890.123456",
  "parent": {
    "ts": "1234567890.123456",
    "user": "U04ABCDEF",
    "text": "Parent message"
  },
  "replies": [
    {
      "ts": "1234567890.234567",
      "user": "U04GHIJKL",
      "text": "Reply 1"
    }
  ],
  "reply_count": 5
}
```

## Error Handling

### Slack API Errors

| Error Code | Cause | Action |
|------------|-------|--------|
| `missing_scope` | Token lacks required scope | Document scope requirements |
| `channel_not_found` | Invalid channel ID or no access | Verify ID, check membership |
| `invalid_auth` | Token expired or invalid | Re-authenticate |
| `rate_limited` | Too many requests | Implement backoff, show Retry-After |
| `thread_not_found` | Invalid thread_ts | Verify timestamp format |

### Error Response Format

```json
{
  "ok": false,
  "error": "missing_scope",
  "needed": "channels:history",
  "provided": "channels:read"
}
```

## Slack App Setup

### Required Steps (Admin)

1. Go to https://api.slack.com/apps
2. Select existing app
3. Navigate to OAuth & Permissions
4. Verify Bot Token Scopes include:
   - `channels:history`
   - `channels:read`
   - `groups:history`
   - `groups:read`
5. Copy Bot User OAuth Token (`xoxb-...`)
6. Set environment variable: `SLACK_BOT_TOKEN`
7. Invite bot to channels: `/invite @YourBotName`

### Bot Access Notes

- Bot can only read channels it's been invited to
- For private channels, bot must be a member
- No token rotation needed (bot tokens don't expire)

## Pagination

### conversations.history

```python
def read_all_messages(channel_id: str, limit: int = 1000):
    """Paginate through all messages up to limit."""
    messages = []
    cursor = None
    
    while len(messages) < limit:
        params = {
            "channel": channel_id,
            "limit": min(200, limit - len(messages))
        }
        if cursor:
            params["cursor"] = cursor
        
        result = slack_request("conversations.history", params)
        messages.extend(result["messages"])
        
        cursor = result.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    
    return messages[:limit]
```

### conversations.replies

No pagination needed for most threads. Slack returns all replies.
For very long threads (1000+ replies), use cursor parameter.

## Security Considerations

1. **Token Storage**: Environment variable only, never in code
2. **Token Display**: Never echo token in output
3. **Access Control**: Bot can only access channels it's invited to
4. **No Expiration**: Bot tokens don't expire (unlike user tokens)

## Testing

### Test Script (existing)

```bash
# Test authentication
uv run --no-project --with requests python scripts/test_slack_api.py

# Test with specific channel
uv run --no-project --with requests python scripts/test_slack_api.py C04E5K9EWXX
```

### Verification Checklist

- [ ] Token authentication works (`auth.test`)
- [ ] Can list channels (`conversations.list`)
- [ ] Can read public channel (`conversations.history`)
- [ ] Can read private channel (if bot is member)
- [ ] Can read thread replies (`conversations.replies`)
- [ ] Message link parsing works
- [ ] Pagination works for large channels
- [ ] Error messages are clear for missing scopes

## Version Plan

| Version | Features |
|---------|----------|
| 1.0.0 | Core: channel read, thread read, message link |
| 1.1.0 | User name resolution, reactions display |
| 1.2.0 | Search integration (if scope available) |

## References

- Slack API: https://api.slack.com/web
- conversations.history: https://api.slack.com/methods/conversations.history
- conversations.replies: https://api.slack.com/methods/conversations.replies
- OAuth Scopes: https://api.slack.com/scopes
- Rate Limits: https://api.slack.com/docs/rate-limits
