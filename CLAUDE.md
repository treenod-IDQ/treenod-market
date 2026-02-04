## Treenod Plugin Marketplace Repository

This is the source of truth for Treenod Claude Code plugins.

### Structure

```
plugins/util/
├── .claude-plugin/plugin.json    # Plugin manifest
└── skills/
    ├── atlassian/                # Confluence and Jira API integration
    ├── document-hoarder/         # Confluence documentation fetcher
    ├── sheet/                    # Google Sheets API integration
    ├── skill-creator/            # Guide for creating Claude Code skills
    ├── slack/                    # Slack message and thread reader
    └── sql-writer/               # Databricks SQL query generator
```

### Development Workflow (Maintainer)

1. Edit plugin files directly in this repo
2. Test: skills are loaded when Claude Code runs here
3. Update version in both files (semantic versioning):
   - `plugins/util/.claude-plugin/plugin.json`
   - `.claude-plugin/marketplace.json`
4. Commit and push to distribute to team

### Distribution (Team Members)

```bash
/plugin marketplace add treenod/treenod-claude-plugins
/plugin install util@treenod-plugins
/plugin update util@treenod-plugins
```

### Available Skills

| Skill | Description |
|-------|-------------|
| atlassian | Confluence and Jira API integration |
| document-hoarder | Confluence documentation fetcher |
| sheet | Google Sheets API integration |
| skill-creator | Guide for creating Claude Code skills |
| slack | Slack message and thread reader |
| sql-writer | Databricks SQL query generator |

### Prerequisites

- atlassian/document-hoarder: `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_API_TOKEN`, `JIRA_URL`
- sheet: Google Cloud project with Sheets API, `gcloud` CLI
- slack: `SLACK_BOT_TOKEN`
- sql-writer: Databricks workspace access

### Adding a New Skill Checklist

When adding a new skill, update these files:

1. **Skill files** (in `plugins/util/skills/<skill-name>/`):
   - `SKILL.md` - Claude Code skill documentation
   - `README.md` - Setup guide (Korean)
   - `CHANGELOG.md` - Version history
   - `scripts/` - Implementation

2. **Documentation updates**:
   - `CLAUDE.md` - Structure, Available Skills, Prerequisites sections
   - `README.md` - 스킬 목록 table
   - `plugins/util/docs/setup-guide.md` - 스킬별 필요 설정 table, 선택 설정 section
   - Confluence page (page_id in setup-guide.md frontmatter) - run `confluence_api.py update`
