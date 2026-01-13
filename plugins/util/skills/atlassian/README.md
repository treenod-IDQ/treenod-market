---
title: Atlassian Skill README
---

# Atlassian Skill

Confluence pages and Jira issues 관리를 위한 Claude Code skill.

## Setup Guide

### 1. Environment Variables

필수 환경 변수 설정:

```bash
# ~/.bashrc or ~/.zshrc
export ATLASSIAN_USER_EMAIL="your_email@domain.com"
export ATLASSIAN_API_TOKEN="your_api_token"
export JIRA_URL="https://your-domain.atlassian.net"
```

API 토큰 생성: https://id.atlassian.com/manage/api-tokens

### 2. Korean Font Setup (for Chart Export)

Altair 차트를 PNG로 export할 때 한글 폰트 지원을 위한 설정.

#### 2.1 Install Noto Sans CJK Font

```bash
# Download font to local directory
mkdir -p ~/.local/share/fonts
cd ~/.local/share/fonts
curl -sL "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Korean/NotoSansCJKkr-Regular.otf" \
  -o NotoSansCJKkr-Regular.otf

# Update font cache
fc-cache -f

# Verify installation
fc-list | grep -i noto
```

#### 2.2 Set Environment Variable

vl-convert가 폰트를 찾을 수 있도록 환경 변수 설정:

```bash
# ~/.bashrc or ~/.zshrc
export VL_CONVERT_FONT_DIR="$HOME/.local/share/fonts"
```

#### 2.3 Configure Chart Font

Altair 차트에서 한글 폰트 사용:

```python
import altair as alt

chart = alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q'
).properties(
    title="차트 제목"
).configure(
    font="Noto Sans CJK KR"  # Global font setting
)

# Export to PNG
chart.save('chart.png', ppi=72)
```

### 3. Confluence Image Upload

차트 이미지를 Confluence 페이지에 업로드:

```bash
# Upload attachment
uv run --no-project --with requests python scripts/confluence_api.py attach <page_id> -f chart.png

# Output includes file_id for ADF embedding:
# ✓ Attachment 'chart.png' uploaded (id: att123456)
#   File ID (for ADF): 24e522f3-af3d-4979-925f-633c41caee8c
#   Collection: contentId-123456
```

ADF에서 이미지 참조:

```json
{
  "type": "mediaSingle",
  "attrs": {"layout": "center"},
  "content": [{
    "type": "media",
    "attrs": {
      "type": "file",
      "id": "<file_id>",
      "collection": "contentId-<page_id>"
    }
  }]
}
```

Note: `file_id` (UUID)를 사용해야 함. `att...` 형식의 attachment ID가 아님.

## Quick Start

```bash
# Read Confluence page
uv run --no-project --with requests python scripts/confluence_api.py read <page_id> -o page.md

# Update Confluence page
uv run --no-project --with requests python scripts/confluence_api.py update <page_id> -f page.md

# Create page in folder
uv run --no-project --with requests python scripts/confluence_api.py create <folder_id> -t "Title" -f content.md

# Upload attachment
uv run --no-project --with requests python scripts/confluence_api.py attach <page_id> -f image.png

# Read Jira issue
uv run --no-project --with requests python scripts/jira_api.py read <issue_key> -o issue.md

# Convert marimo notebook HTML to Confluence
uv run --no-project --with requests --with lxml python scripts/marimo_converter.py convert notebook.html --page-id <page_id>
```

## Documentation

- [SKILL.md](SKILL.md) - 상세 사용법
- [docs/SPEC.md](docs/SPEC.md) - API 스펙 및 구현 상세
- [docs/adf-converter-spec.md](docs/adf-converter-spec.md) - ADF 변환 스펙
- [references/api_reference.md](references/api_reference.md) - Atlassian API 레퍼런스

## Troubleshooting

### Chart Font Not Rendering

한글이 박스(tofu)로 표시되는 경우:

1. 폰트 설치 확인: `fc-list | grep -i noto`
2. 환경 변수 확인: `echo $VL_CONVERT_FONT_DIR`
3. 차트에 `.configure(font="Noto Sans CJK KR")` 추가

### Image Not Showing in Confluence

"Something went wrong" 에러 발생 시:

1. `file_id` (UUID) 사용 확인 - `att...` 형식 아님
2. `collection` 형식 확인: `contentId-<page_id>`
3. 첨부파일 업로드 후 반환된 `file_id` 사용

### Attachment Update

기존 첨부파일 업데이트 시 400 에러 발생:

```bash
# 기존 첨부파일 업데이트는 다른 endpoint 사용
POST /wiki/rest/api/content/{pageId}/child/attachment/{attachmentId}/data
```
