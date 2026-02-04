---
title: Slack Skill README
---

# Slack Skill

Slack 채널 메시지 및 스레드 조회를 위한 Claude Code skill.

## Setup Guide

### 1. Environment Variables

필수 환경 변수 설정:

```bash
# ~/.bashrc or ~/.zshrc
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
```

Bot Token 발급 방법은 아래 Bot Setup 섹션 참조.

### 2. Bot Setup

#### 2.1 Slack App 생성 또는 선택

1. https://api.slack.com/apps 접속
2. 기존 앱 선택 또는 Create New App 클릭
3. From scratch 선택 후 앱 이름과 워크스페이스 선택

#### 2.2 Bot Token Scopes 설정

OAuth & Permissions 메뉴에서 Bot Token Scopes 추가:

| Scope | 설명 |
|-------|------|
| `channels:history` | 공개 채널 메시지 읽기 |
| `channels:read` | 공개 채널 정보 조회 |
| `groups:history` | 비공개 채널 메시지 읽기 |
| `groups:read` | 비공개 채널 정보 조회 |

#### 2.3 앱 설치 및 토큰 복사

1. OAuth & Permissions 상단의 Install to Workspace 클릭
2. 권한 승인
3. Bot User OAuth Token 복사 (`xoxb-`로 시작)
4. 환경 변수에 설정

#### 2.4 채널에 봇 초대

봇이 메시지를 읽으려면 해당 채널에 초대되어야 함:

```
/invite @YourBotName
```

비공개 채널도 동일하게 봇 초대 필요.

## Quick Start

```bash
# 채널 메시지 읽기
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7 --limit 50

# 스레드 읽기 (channel:thread_ts 형식)
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7:1770094319.078559

# 메시지 링크로 읽기
uv run --no-project --with requests python scripts/slack_api.py read "https://treenod.slack.com/archives/G4CDARPJ7/p1770094319078559"

# 텍스트 형식 출력
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7 --format text

# 파일로 저장
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7 -o messages.json
```

## 입력 형식 자동 감지

`read` 명령은 입력 형식을 자동으로 감지:

| 입력 | 예시 | 동작 |
|------|------|------|
| 채널 ID | `G4CDARPJ7` | 채널 메시지 조회 |
| 채널:스레드 | `G4CDARPJ7:1770094319.078559` | 스레드 조회 |
| 메시지 링크 | `https://...slack.com/archives/...` | 해당 메시지부터 조회 |

## 워크플로우 예시

채널에서 스레드 찾아 읽기:

```bash
# 1. 채널 메시지 조회
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7 --limit 10

# 출력에서 thread_ts 확인:
# "thread_ts": "1770094319.078559"
# "reply_count": 14

# 2. 해당 스레드 조회
uv run --no-project --with requests python scripts/slack_api.py read G4CDARPJ7:1770094319.078559
```

## 채널 ID 찾기

### Slack 앱에서 확인

1. 채널 상단의 채널 이름 클릭
2. 팝업 하단에서 Channel ID 확인 (예: `C04E5K9EWXX`)

### URL에서 추출

채널 URL 형식: `https://app.slack.com/client/T.../C04E5K9EWXX`

마지막 부분이 채널 ID.

### 메시지 링크에서 추출

메시지 링크 형식: `https://treenod.slack.com/archives/G4CDARPJ7/p1770094319078559`

`archives/` 다음 부분이 채널 ID.

## Documentation

- [SKILL.md](SKILL.md) - 상세 사용법
- [SPEC.md](SPEC.md) - API 스펙 및 구현 상세

## Troubleshooting

### missing_scope 에러

```
Error: Slack API error: missing_scope
```

원인: Bot Token에 필요한 scope가 없음.

해결:
1. https://api.slack.com/apps 에서 앱 선택
2. OAuth & Permissions > Bot Token Scopes에서 필요한 scope 추가
3. 앱 재설치 (Reinstall to Workspace)
4. 새 토큰 복사 후 환경 변수 업데이트

### channel_not_found 에러

```
Error: Slack API error: channel_not_found
```

원인: 채널 ID가 잘못되었거나 봇이 채널에 없음.

해결:
1. 채널 ID 확인 (C, G, D로 시작하는 영숫자)
2. 채널에 봇 초대: `/invite @YourBotName`

### not_in_channel 에러

원인: 봇이 해당 채널에 초대되지 않음.

해결: 채널에서 `/invite @YourBotName` 실행

### 환경 변수 확인

```bash
echo $SLACK_BOT_TOKEN
# xoxb-로 시작하는 토큰이 출력되어야 함
```

토큰이 비어있으면 shell 설정 파일 확인 후 `source ~/.zshrc` 실행.
