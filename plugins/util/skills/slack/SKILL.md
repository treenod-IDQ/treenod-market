---
name: slack
description: Read Slack channel messages, thread conversations, and messages from links using bot token authentication. Use when users need to (1) Read recent messages from a channel, (2) Read all messages in a thread, (3) Read messages starting from a specific message link.
---

# Slack API Skill

Read Slack messages using Python scripts and the uv package manager.

## Prerequisites

**Required:**
- uv package manager installed
- Environment variable set:
  - `SLACK_BOT_TOKEN` - Bot User OAuth Token (starts with `xoxb-`)

**Bot Setup:**
- Bot must be invited to channels before it can read messages: `/invite @BotName`

**Execution pattern:**
```bash
uv run --no-project --with requests python scripts/slack_api.py [command] [args]
```

## Available Operations

### Read Messages (Auto-Detect)

```bash
uv run --no-project --with requests python scripts/slack_api.py read <input> --limit 100
```

Automatically detects input type:
- Channel ID (e.g., `G4CDARPJ7`) → reads channel messages
- Channel:Thread (e.g., `G4CDARPJ7:1770094319.078559`) → reads thread
- Message link (e.g., `https://...slack.com/archives/...`) → reads from that message

**Arguments:**
- `input` - Channel ID, channel:thread_ts, or message link
- `--limit` - Number of messages (default: 100)
- `--format` - Output format: `json` (default) or `text`
- `-o` - Output file path

**Examples:**
```bash
# Read channel
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7 --limit 50

# Read thread (channel:thread_ts format)
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7:1770094319.078559

# Read from message link
uv run --no-project --with requests python scripts/slack_api.py read "https://treenod.slack.com/archives/G4CDARPJ7/p1770094319078559"
```

**Workflow example:**
```bash
# 1. Read channel, find thread_ts in output
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7 --limit 10
# Output shows: "thread_ts": "1770094319.078559", "reply_count": 14

# 2. Read that thread using channel:thread_ts format
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7:1770094319.078559
```

### Read Channel Messages

```bash
uv run --no-project --with requests python scripts/slack_api.py channel <channel_id> --limit 100
```

**Arguments:**
- `channel_id` - Channel ID (e.g., `C04E5K9EWXX` or `G4CDARPJ7`)
- `--limit` - Number of messages (default: 100, max: 1000)
- `--format` - Output format: `json` (default) or `text`
- `-o` - Output file path

**Example:**
```bash
uv run --no-project --with requests python scripts/slack_api.py channel G4CDARPJ7 --limit 50 --format text
```

### Read Thread Conversations

```bash
uv run --no-project --with requests python scripts/slack_api.py thread <channel_id> <thread_ts>
```

**Arguments:**
- `channel_id` - Channel containing the thread
- `thread_ts` - Parent message timestamp (e.g., `1234567890.123456`)
- `--format` - Output format: `json` (default) or `text`
- `-o` - Output file path

**Example:**
```bash
uv run --no-project --with requests python scripts/slack_api.py thread G4CDARPJ7 1770094319.078559
```

### Read from Message Link

```bash
uv run --no-project --with requests python scripts/slack_api.py link "<message_url>" --limit 50
```

**Arguments:**
- `message_url` - Slack message permalink
- `--limit` - Messages to fetch after target (default: 50)
- `--format` - Output format: `json` (default) or `text`
- `-o` - Output file path

**Example:**
```bash
uv run --no-project --with requests python scripts/slack_api.py link "https://treenod.slack.com/archives/G4CDARPJ7/p1770094319078559"
```

## Output Formats

### JSON (default)

```json
{
  "channel": {
    "id": "G4CDARPJ7",
    "name": "데이터분석팀",
    "topic": "",
    "purpose": ""
  },
  "messages": [
    {
      "user": "U07J8HJ18MC",
      "type": "message",
      "ts": "1770094319.078559",
      "text": "Message content..."
    }
  ],
  "has_more": true
}
```

### Text

```
Channel: #데이터분석팀 (G4CDARPJ7)
Messages: 50 (has_more: True)
---
[2025-02-03 12:00:00] U07J8HJ18MC
Message content...
```

## Finding Channel and Thread IDs

**Channel ID:**
- Open channel in Slack
- Click channel name at top
- Channel ID is at bottom of popup (e.g., `C04E5K9EWXX`)
- Or extract from URL: `https://app.slack.com/client/T.../C04E5K9EWXX`

**Thread Timestamp:**
- From message link: `https://...slack.com/archives/C.../p1234567890123456`
- Convert `p1234567890123456` to `1234567890.123456`
- Or use JSON output from channel read - look for `thread_ts` field

## Bot Setup Instructions

1. Go to https://api.slack.com/apps
2. Select existing app or create new
3. Navigate to OAuth & Permissions
4. Add Bot Token Scopes:
   - `channels:history` - Read public channel messages
   - `channels:read` - Get public channel info
   - `groups:history` - Read private channel messages
   - `groups:read` - Get private channel info
5. Install/Reinstall app to workspace
6. Copy Bot User OAuth Token (`xoxb-...`)
7. Set environment variable:
   ```bash
   export SLACK_BOT_TOKEN="xoxb-your-token"
   ```
8. Invite bot to channels:
   ```
   /invite @YourBotName
   ```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `missing_scope` | Token lacks required scope | Add scope in app settings, reinstall |
| `channel_not_found` | Invalid channel ID or no access | Check ID, invite bot to channel |
| `invalid_auth` | Token invalid or expired | Check `SLACK_BOT_TOKEN` value |
| `not_in_channel` | Bot not invited | `/invite @BotName` in channel |

## Troubleshooting

**Bot token not set:**
```bash
export SLACK_BOT_TOKEN="xoxb-..."
```

**Permission errors:**
Ensure bot has required scopes and is invited to the channel.

**Private channel access:**
Bot must be explicitly invited to private channels.
