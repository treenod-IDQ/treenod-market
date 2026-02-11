---
title: Treenod Claude Code Plugins
---

# Treenod Claude Code Plugins

Treenod 내부용 Claude Code 플러그인 마켓플레이스

## 빠른 시작

```bash
# 1. Claude Code에서 마켓플레이스 추가
/plugin marketplace add treenod-IDQ/treenod-market

# 2. 플러그인 설치
/plugin install util@treenod-plugins
```

상세 설정 가이드: [plugins/util/docs/setup-guide.md](plugins/util/docs/setup-guide.md)

## 스킬 목록

| Skill | Description |
|-------|-------------|
| atlassian | Confluence, Jira API 연동 |
| dashboard-maker | Databricks Lakeview 대시보드 생성/수정 |
| document-hoarder | Confluence 문서 로컬 동기화 |
| sheet | Google Sheets API 연동 |
| slack | Slack 채널 메시지, 스레드 조회 |
| skill-creator | Claude Code skill 생성 가이드 |
| sql-writer | Databricks SQL 쿼리 생성기 |

## 문서

| 문서 | 대상 | 내용 |
|------|------|------|
| [설정 가이드](plugins/util/docs/setup-guide.md) | 사용자 | 터미널 접근, 도구 설치, 토큰 발급, 플러그인 설치 |
| [개발자 가이드](plugins/util/docs/developer-guide.md) | 관리자 | 스킬 추가/수정, 버전 관리, 배포 |

## 플러그인 업데이트

```bash
/plugin marketplace update treenod-plugins
/plugin update util@treenod-plugins
```
