---
title: Dashboard Maker Skill README
---

# Dashboard Maker Skill

Databricks Lakeview 대시보드 생성/수정을 위한 Claude Code skill.

## Setup Guide

### 1. Databricks PAT 생성

1. Databricks workspace 접속
2. 우측 상단 사용자명 클릭 > Settings
3. Developer 탭 클릭
4. Access tokens 옆 Manage 클릭
5. Generate new token 클릭
6. 토큰 용도 설명 입력 (예: claude-code-dashboard)
7. 유효 기간 설정 (일 단위)
8. Generate 클릭
9. 토큰 복사 후 안전하게 저장

주의: 토큰은 생성 시에만 확인 가능.

### 2. 환경 변수 설정

shell 설정 파일 (`.bashrc`, `.zshrc` 등)에 추가:

```bash
export DATABRICKS_HOST="https://your-workspace.databricks.com"
export DATABRICKS_TOKEN="your-personal-access-token"
```

설정 적용:

```bash
source ~/.zshrc  # 또는 ~/.bashrc
```

또는 `~/.databrickscfg` 파일 생성:

```ini
[DEFAULT]
host = https://your-workspace.databricks.com
token = your-personal-access-token
```

### 3. Warehouse ID 확인

대시보드 생성/게시에 warehouse_id 필요:

1. Databricks workspace > SQL Warehouses 메뉴
2. 사용할 warehouse 클릭
3. Connection details 탭에서 HTTP Path 확인
4. HTTP Path의 마지막 segment가 warehouse ID

예: `/sql/1.0/warehouses/abc123def456` -> warehouse ID: `abc123def456`

## Quick Start

```bash
# 대시보드 생성 스크립트 실행
uv run --with databricks-sdk python3 create_dashboard.py
```

## Documentation

- [SKILL.md](SKILL.md) - 상세 사용법 및 위젯 빌더 레퍼런스
- [references/lakeview-guide.md](references/lakeview-guide.md) - Lakeview JSON 구조 가이드

## Troubleshooting

### 대시보드가 비어있는 경우

- `warehouse_id` 값 확인
- `publish()` 호출 여부 확인

### API 400 에러

- queryLines에 `\r\n` 대신 `\n` 사용
- dataset name과 widget name 중복 확인
- update 시 etag 포함 확인

### 환경 변수 확인

```bash
echo $DATABRICKS_HOST
echo $DATABRICKS_TOKEN
```
