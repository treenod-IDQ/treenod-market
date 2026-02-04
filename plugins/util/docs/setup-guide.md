---
title: Treenod Plugin 설정 가이드
page_id: 73484927057
---

## 스킬별 필요 설정

| Skill | 패키지 설치 | 환경 변수 |
|-------|-----------|----------|
| atlassian, document-hoarder | uv | ATLASSIAN_USER_EMAIL, ATLASSIAN_API_TOKEN, JIRA_URL |
| sheet | uv, gcloud | gcloud 로그인으로 대체 | 
| slack | uv | SLACK_BOT_TOKEN |
| sql-writer | uv | DATABRICKS_TOKEN, DATABRICKS_HOST |
| skill-creator | 없음 | 없음 |

## 필수 설정

모든 사용자가 완료해야 하는 설정.

### 터미널 접근 (macOS)

두 가지 방법 중 하나를 선택:

- Launchpad에서 Terminal 검색 후 클릭
- Finder > Applications > Utilities > Terminal 더블클릭

### 터미널 접근 (Windows WSL)

Windows 사용자는 WSL (Windows Subsystem for Linux) 사용을 권장. Linux 환경에서 모든 도구를 동일하게 사용 가능.

#### WSL 설치

사전 요구사항: Windows 10 버전 2004 이상 (Build 19041+) 또는 Windows 11

1. PowerShell을 관리자 권한으로 실행 (시작 메뉴에서 PowerShell 검색 > 우클릭 > 관리자 권한으로 실행)
2. WSL 설치 명령 실행:

```powershell
wsl --install
```

이 명령으로 WSL 2와 Ubuntu가 함께 설치됨.

3. 컴퓨터 재시작
4. 재시작 후 Ubuntu 창이 자동으로 열리면 사용자 이름과 비밀번호 설정

#### WSL 설치 확인

```powershell
wsl --list --verbose
```

출력 예시:

```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

VERSION이 2인지 확인. 1인 경우 WSL 2로 업그레이드:

```powershell
wsl --set-version Ubuntu 2
```

#### Ubuntu 실행

- Windows Terminal 실행 후 Ubuntu 탭 선택
- 또는 시작 메뉴에서 Ubuntu 검색 후 실행

WSL 설치 후 이 가이드의 macOS/Linux 명령어를 Ubuntu에서 그대로 사용.

공식 문서: https://learn.microsoft.com/en-us/windows/wsl/install

#### Windows Terminal 설치 (선택)

WSL과 함께 사용하면 편리:

- Microsoft Store에서 Windows Terminal 설치: https://aka.ms/terminal
- 또는 PowerShell에서: `winget install Microsoft.WindowsTerminal`

### Claude Code CLI

사전 요구사항: Claude 구독 (Pro, Max, Teams, Enterprise) 또는 Claude Console 계정

macOS/Linux/WSL:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

대체 방법:
- macOS Homebrew: `brew install --cask claude-code`

설치 후 프로젝트 디렉토리에서 `claude` 명령 실행.

공식 문서: https://code.claude.com/docs/en/overview

### 플러그인 설치

Claude Code 실행 후:

```bash
# 마켓플레이스 추가
/plugin marketplace add treenod-IDQ/treenod-market

# 플러그인 설치
/plugin install util@treenod-plugins
```

플러그인 업데이트:

```bash
/plugin marketplace update treenod-plugins
/plugin update util@treenod-plugins
```

## 선택 설정

사용할 스킬에 따라 필요한 설정만 완료.

### uv (Python 패키지 관리자)

필요 스킬: sheet, sql-writer

macOS/Linux/WSL:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

대체 방법:
- macOS Homebrew: `brew install uv`

공식 문서: https://docs.astral.sh/uv/getting-started/installation/

### Atlassian API Token

필요 스킬: atlassian, document-hoarder

#### 토큰 생성

1. https://id.atlassian.com/manage-profile/security/api-tokens 접속
2. Create API token 클릭
3. 토큰 이름 입력 (예: claude-code-plugin)
4. 만료 기간 설정 (1-365일, 기본값 1년)
5. Create 클릭
6. 토큰 복사 후 안전하게 저장

주의: 토큰은 생성 시에만 확인 가능. 분실 시 재생성 필요.

#### 환경 변수 설정

shell 설정 파일 (`.bashrc`, `.zshrc` 등)에 추가:

```bash
export ATLASSIAN_USER_EMAIL="your-email@example.com"
export ATLASSIAN_API_TOKEN="your-api-token"
export JIRA_URL="https://your-domain.atlassian.net"
```

설정 적용:

```bash
source ~/.zshrc  # 또는 ~/.bashrc
```

공식 문서: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/

### Google Sheets API (gcloud)

필요 스킬: sheet

#### gcloud 설치

macOS:

1. Python 3.9-3.14 설치 확인: `python3 -V`
2. 아키텍처에 맞는 패키지 다운로드:
   - Intel: https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-x86_64.tar.gz
   - Apple Silicon: https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz
3. 압축 해제 후 설치:

```bash
tar -xf google-cloud-cli-darwin-*.tar.gz
./google-cloud-sdk/install.sh
```

Linux/WSL (Ubuntu):

```bash
sudo apt-get update && sudo apt-get install apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
```

공식 문서: https://cloud.google.com/sdk/docs/install

#### Google Sheets API 설정

1. Google Cloud Console에서 프로젝트 생성 또는 선택: https://console.cloud.google.com
2. Google Sheets API 활성화: APIs & Services > Library > Google Sheets API > Enable
3. gcloud CLI 인증:

```bash
gcloud init
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets
```

브라우저에서 Google 계정 인증 후 사용 가능.

### Slack Bot Token

필요 스킬: slack

#### Slack App 설정

1. https://api.slack.com/apps 접속
2. 기존 앱 선택 또는 Create New App > From scratch
3. OAuth & Permissions 메뉴로 이동
4. Bot Token Scopes에 다음 scope 추가:
   - `channels:history` - 공개 채널 메시지 읽기
   - `channels:read` - 공개 채널 정보 조회
   - `groups:history` - 비공개 채널 메시지 읽기
   - `groups:read` - 비공개 채널 정보 조회
5. Install to Workspace 클릭 후 권한 승인
6. Bot User OAuth Token 복사 (`xoxb-`로 시작)

#### 환경 변수 설정

shell 설정 파일에 추가:

```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
```

#### 채널에 봇 초대

봇이 메시지를 읽으려면 채널에 초대 필요:

```
/invite @YourBotName
```

공식 문서: https://api.slack.com/authentication/token-types

### Databricks Token

필요 스킬: sql-writer

#### 토큰 생성

1. Databricks workspace 접속
2. 우측 상단 사용자명 클릭 > Settings
3. Developer 탭 클릭
4. Access tokens 옆 Manage 클릭
5. Generate new token 클릭
6. 토큰 용도 설명 입력 (예: claude-code-sql-writer)
7. 유효 기간 설정 (일 단위)
8. Generate 클릭
9. 토큰 복사 후 안전하게 저장

주의: 토큰은 생성 시에만 확인 가능.

#### 환경 변수 설정

shell 설정 파일에 추가:

```bash
export DATABRICKS_HOST="https://your-workspace.databricks.com"
export DATABRICKS_TOKEN="your-personal-access-token"
```

또는 `~/.databrickscfg` 파일 생성:

```ini
[DEFAULT]
host = https://your-workspace.databricks.com
token = your-personal-access-token
```

공식 문서: https://docs.databricks.com/en/dev-tools/auth/pat.html

## 문제 해결

### 환경 변수 확인

```bash
# Atlassian
echo $ATLASSIAN_USER_EMAIL
echo $ATLASSIAN_API_TOKEN
echo $JIRA_URL

# Slack
echo $SLACK_BOT_TOKEN

# Databricks
echo $DATABRICKS_HOST
echo $DATABRICKS_TOKEN
```

### gcloud 인증 확인

```bash
gcloud auth list
gcloud config list
```

### Claude Code 재시작

환경 변수 변경 후 Claude Code 세션 재시작 필요.
