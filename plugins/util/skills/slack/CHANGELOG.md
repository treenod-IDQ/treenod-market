# Changelog

## [1.0.0] - 2026-02-03

Initial release of the Slack skill for Claude Code.

### Features

- Slack channel message reading via Web API
- Thread conversation retrieval
- Message link parsing and navigation

### Scripts

- `slack_api.py` - Main CLI for Slack operations
  - `read` command with auto-detection (channel ID, channel:thread_ts, message link)
  - `channel` command for explicit channel read
  - `thread` command for explicit thread read
  - `link` command for explicit message link read
  - JSON and text output formats
  - File output with `-o` flag
- `utils.py` - Authentication and utility functions
  - Bot token authentication (`SLACK_BOT_TOKEN`)
  - Message link parsing (URL to channel_id + timestamp)
  - Custom `SlackAPIError` exception

### Documentation

- `SKILL.md` - Usage guide for Claude Code
- `README.md` - Setup guide in Korean
- `SPEC.md` - API specification and implementation details

### API Endpoints Used

- `conversations.info` - Get channel metadata
- `conversations.history` - Read channel messages
- `conversations.replies` - Read thread messages

### Required Scopes

- `channels:history` - Read public channel messages
- `channels:read` - Get public channel info
- `groups:history` - Read private channel messages
- `groups:read` - Get private channel info
