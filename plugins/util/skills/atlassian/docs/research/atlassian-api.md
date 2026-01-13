# Atlassian API Research Document

## Executive Summary

This document provides comprehensive research findings on the Atlassian Confluence and Jira REST APIs for reading and managing pages and issues. The research includes API endpoint analysis, authentication methods, data formats, and validated test results from live API calls.

## Table of Contents

1. [Authentication](#authentication)
2. [Confluence REST API v2](#confluence-rest-api-v2)
3. [Jira REST API v3](#jira-rest-api-v3)
4. [Atlassian Document Format (ADF)](#atlassian-document-format-adf)
5. [Test Results](#test-results)
6. [Rate Limiting and Best Practices](#rate-limiting-and-best-practices)
7. [Error Handling](#error-handling)

---

## Authentication

### Method: Basic Authentication with API Tokens

Both Confluence and Jira APIs use the same authentication mechanism.

**Steps to Generate API Token:**
1. Visit https://id.atlassian.com/manage/api-tokens
2. Create a new API token for your Atlassian account
3. Store the token securely (it cannot be retrieved again)

**Authentication Header Format:**
```python
import base64

email = "your_email@domain.com"
api_token = "your_api_token"

# Create Basic Auth header
auth_string = f"{email}:{api_token}"
auth_bytes = auth_string.encode('ascii')
base64_auth = base64.b64encode(auth_bytes).decode('ascii')

headers = {
    "Authorization": f"Basic {base64_auth}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

**Security Notes:**
- API tokens work with two-factor authentication
- Tokens can be revoked individually without changing passwords
- For production applications, OAuth 2.0 is recommended over Basic Auth
- Never commit API tokens to version control

---

## Confluence REST API v2

### Base URL Structure

```
https://{your-domain}.atlassian.net/wiki/api/v2
```

### Key Endpoints

#### 1. Get Page by ID

**Endpoint:** `GET /wiki/api/v2/pages/{pageId}`

**Required Headers:**
- `Authorization: Basic <base64_credentials>`
- `Content-Type: application/json`
- `Accept: application/json`

**Query Parameters:**
- `body-format` - Content format (values: `storage`, `atlas_doc_format`, `view`)
  - Use `atlas_doc_format` for ADF JSON format
- `include-labels` - Boolean to include page labels
- `include-properties` - Boolean to include content properties
- `include-versions` - Boolean to include version history

**Example Request:**
```bash
curl -u email@domain.com:api_token \
  -H "Content-Type: application/json" \
  "https://your-domain.atlassian.net/wiki/api/v2/pages/123456?body-format=atlas_doc_format"
```

**Response Structure:**
```json
{
  "id": "73294938154",
  "status": "current",
  "title": "Page Title",
  "spaceId": "12345",
  "authorId": "account-id",
  "createdAt": "2025-01-01T00:00:00.000Z",
  "version": {
    "createdAt": "2025-01-01T00:00:00.000Z",
    "message": "Version message",
    "number": 5,
    "minorEdit": false,
    "authorId": "account-id"
  },
  "body": {
    "atlas_doc_format": {
      "representation": "atlas_doc_format",
      "value": "{\"type\":\"doc\",\"content\":[...],\"version\":1}"
    }
  },
  "_links": {
    "webui": "/wiki/spaces/SPACE/pages/123456/Page+Title"
  }
}
```

#### 2. Update Page

**Endpoint:** `PUT /wiki/api/v2/pages/{pageId}`

**Request Body:**
```json
{
  "id": "123456",
  "status": "current",
  "title": "Updated Page Title",
  "spaceId": "12345",
  "body": {
    "representation": "atlas_doc_format",
    "value": "{\"type\":\"doc\",\"content\":[...],\"version\":1}"
  },
  "version": {
    "number": 6,
    "message": "Update description"
  }
}
```

**Important Notes:**
- Version number must be incremented from the current version
- The `spaceId` must match the page's current space
- ADF content must be passed as a JSON string in the `value` field

**Response Codes:**
- `200` - Success, returns updated page
- `400` - Bad request (invalid parameters or version conflict)
- `401` - Authentication failed
- `403` - Insufficient permissions
- `404` - Page not found

### Permissions

API operations respect the same permissions as the web interface:
- Read: User must have view permission for the page
- Update: User must have edit permission for the page

---

## Jira REST API v3

### Base URL Structure

```
https://{your-domain}.atlassian.net/rest/api/3
```

### Key Endpoints

#### 1. Get Issue by Key or ID

**Endpoint:** `GET /rest/api/3/issue/{issueIdOrKey}`

**Required Headers:**
- `Authorization: Basic <base64_credentials>`
- `Content-Type: application/json`
- `Accept: application/json`

**Query Parameters:**

| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| `fields` | Comma-separated list of fields to retrieve | `summary,status,description,assignee,reporter,comment,worklog,issuelinks,created,updated` |
| `expand` | Additional data to include | `renderedFields,changelog,operations` |
| `properties` | Issue property keys to include | `property1,property2` |
| `updateHistory` | Include update history | `true` or `false` |

**Field Selection Options:**
- `*all` - Returns all fields
- `*navigable` - Returns navigable fields (default)
- Specific fields: `summary,status,description`
- Exclude fields: `*all,-comment` (all fields except comments)

**Example Request:**
```bash
curl -u email@domain.com:api_token \
  -H "Content-Type: application/json" \
  "https://your-domain.atlassian.net/rest/api/3/issue/PROJECT-123?fields=summary,status,description,assignee,reporter,comment,worklog,issuelinks,created,updated&expand=renderedFields"
```

**Response Structure:**
```json
{
  "expand": "renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations",
  "id": "227768",
  "self": "https://your-domain.atlassian.net/rest/api/3/issue/227768",
  "key": "PROJECT-123",
  "fields": {
    "summary": "Issue summary text",
    "status": {
      "self": "https://your-domain.atlassian.net/rest/api/3/status/10001",
      "description": "",
      "name": "Done",
      "id": "10001",
      "statusCategory": {
        "id": 3,
        "key": "done",
        "colorName": "green",
        "name": "Done"
      }
    },
    "description": {
      "version": 1,
      "type": "doc",
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": "Description text"
            }
          ]
        }
      ]
    },
    "assignee": {
      "self": "https://your-domain.atlassian.net/rest/api/3/user?accountId=...",
      "accountId": "712020:d5376783-8c3c-4daa-bc53-facd86b3f01c",
      "emailAddress": "user@domain.com",
      "displayName": "User Name",
      "active": true,
      "timeZone": "Asia/Seoul"
    },
    "reporter": {
      "accountId": "712020:...",
      "displayName": "Reporter Name"
    },
    "created": "2025-09-29T17:52:34.097+0900",
    "updated": "2025-12-03T10:14:43.231+0900",
    "comment": {
      "comments": [
        {
          "self": "https://your-domain.atlassian.net/rest/api/3/issue/227768/comment/191253",
          "id": "191253",
          "author": {
            "accountId": "712020:...",
            "displayName": "Comment Author",
            "emailAddress": "author@domain.com"
          },
          "body": {
            "version": 1,
            "type": "doc",
            "content": [
              {
                "type": "paragraph",
                "content": [
                  {
                    "type": "text",
                    "text": "Comment text in ADF format"
                  }
                ]
              }
            ]
          },
          "created": "2025-09-29T18:34:00.000+0900",
          "updated": "2025-09-29T18:34:00.000+0900",
          "jsdPublic": true
        }
      ],
      "maxResults": 20,
      "total": 2,
      "startAt": 0
    },
    "worklog": {
      "startAt": 0,
      "maxResults": 20,
      "total": 13,
      "worklogs": [
        {
          "self": "https://your-domain.atlassian.net/rest/api/3/issue/227768/worklog/10000",
          "author": {
            "accountId": "712020:...",
            "displayName": "Worker Name"
          },
          "created": "2025-10-01T09:00:00.000+0900",
          "updated": "2025-10-01T09:00:00.000+0900",
          "started": "2025-10-01T09:00:00.000+0900",
          "timeSpent": "2h",
          "timeSpentSeconds": 7200,
          "comment": {
            "type": "doc",
            "content": [...]
          }
        }
      ]
    },
    "issuelinks": [
      {
        "id": "10000",
        "type": {
          "id": "10000",
          "name": "Blocks",
          "inward": "is blocked by",
          "outward": "blocks"
        },
        "outwardIssue": {
          "id": "10003",
          "key": "PROJECT-124",
          "self": "https://your-domain.atlassian.net/rest/api/3/issue/10003",
          "fields": {
            "summary": "Linked issue summary",
            "status": {
              "name": "In Progress"
            }
          }
        }
      }
    ]
  },
  "renderedFields": {
    "description": "<p>HTML rendered description</p>",
    "comment": {
      "comments": [
        {
          "body": "<p>HTML rendered comment</p>"
        }
      ]
    }
  }
}
```

### Important Field Details

#### Status Field
Contains the current issue status with category information:
- `name` - Display name of the status
- `statusCategory.key` - Category key (`new`, `indeterminate`, `done`)
- `statusCategory.colorName` - Color for UI display

#### Comment Field
- Paginated list with `total`, `startAt`, `maxResults`
- Each comment has `body` in ADF format
- `renderedFields.comment` provides HTML version when expanded

#### Worklog Field
- Paginated list of time logging entries
- `timeSpent` - Human-readable format (e.g., "2h 30m")
- `timeSpentSeconds` - Seconds for calculations
- `started` - Timestamp when work started

#### Issue Links Field
- Array of linked issues
- `type` defines relationship (Blocks, Relates to, etc.)
- `inwardIssue` or `outwardIssue` contains linked issue details
- Linked issue includes key, summary, and status

---

## Atlassian Document Format (ADF)

### Overview

ADF is a JSON-based format used across Atlassian products for rich content representation. Both Confluence pages and Jira issue descriptions/comments use ADF.

### Structure

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    // Array of content nodes
  ]
}
```

### Node Types

#### Block Nodes

**Paragraph:**
```json
{
  "type": "paragraph",
  "attrs": {
    "localId": "unique-id"
  },
  "content": [
    {
      "type": "text",
      "text": "Paragraph text"
    }
  ]
}
```

**Heading:**
```json
{
  "type": "heading",
  "attrs": {
    "level": 2,
    "localId": "unique-id"
  },
  "content": [
    {
      "type": "text",
      "text": "Heading text"
    }
  ]
}
```
- Levels: 1-6 (h1-h6)

**Bullet List:**
```json
{
  "type": "bulletList",
  "attrs": {
    "localId": "unique-id"
  },
  "content": [
    {
      "type": "listItem",
      "attrs": {
        "localId": "unique-id"
      },
      "content": [
        {
          "type": "paragraph",
          "attrs": {
            "localId": "unique-id"
          },
          "content": [
            {
              "type": "text",
              "text": "List item text"
            }
          ]
        }
      ]
    }
  ]
}
```

**Ordered List:**
```json
{
  "type": "orderedList",
  "attrs": {
    "localId": "unique-id"
  },
  "content": [
    {
      "type": "listItem",
      "content": [...]
    }
  ]
}
```

**Code Block:**
```json
{
  "type": "codeBlock",
  "attrs": {
    "language": "python",
    "localId": "unique-id"
  },
  "content": [
    {
      "type": "text",
      "text": "code content"
    }
  ]
}
```

**Blockquote:**
```json
{
  "type": "blockquote",
  "content": [
    {
      "type": "paragraph",
      "content": [...]
    }
  ]
}
```

**Table:**
```json
{
  "type": "table",
  "attrs": {
    "isNumberColumnEnabled": false,
    "layout": "default",
    "localId": "unique-id"
  },
  "content": [
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableHeader",
          "content": [
            {
              "type": "paragraph",
              "content": [...]
            }
          ]
        }
      ]
    }
  ]
}
```

#### Inline Nodes

**Text with Marks:**
```json
{
  "type": "text",
  "text": "formatted text",
  "marks": [
    {
      "type": "strong"  // Bold
    },
    {
      "type": "em"  // Italic
    },
    {
      "type": "code"  // Inline code
    },
    {
      "type": "underline"
    },
    {
      "type": "strike"  // Strikethrough
    },
    {
      "type": "link",
      "attrs": {
        "href": "https://example.com",
        "title": "Link title"
      }
    },
    {
      "type": "textColor",
      "attrs": {
        "color": "#ff0000"
      }
    }
  ]
}
```

**Hard Break:**
```json
{
  "type": "hardBreak"
}
```

**Emoji:**
```json
{
  "type": "emoji",
  "attrs": {
    "shortName": ":smile:",
    "id": "1f604",
    "text": "😄"
  }
}
```

**Mention:**
```json
{
  "type": "mention",
  "attrs": {
    "id": "712020:account-id",
    "text": "@Username",
    "accessLevel": ""
  }
}
```

### Nested Structures

Lists can be nested:
```json
{
  "type": "bulletList",
  "content": [
    {
      "type": "listItem",
      "content": [
        {
          "type": "paragraph",
          "content": [
            {"type": "text", "text": "Parent item"}
          ]
        },
        {
          "type": "bulletList",
          "content": [
            {
              "type": "listItem",
              "content": [
                {
                  "type": "paragraph",
                  "content": [
                    {"type": "text", "text": "Nested item"}
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### ADF Validation

- JSON Schema available at: http://go.atlassian.com/adf-json-schema
- Root must be `{"type": "doc", "version": 1}`
- Content traversal is ordered
- Each node type has specific allowed children and attributes

---

## Test Results

### Test Environment
- Domain: treenod.atlassian.net
- Authentication: Basic Auth with API token
- Python: 3.14.2
- HTTP Client: requests library

### Confluence API Test

**Test Page:** https://treenod.atlassian.net/wiki/spaces/~712020c45463edcb8440b6adc872f6958d74a3/pages/73294938154/test

**Request:**
```python
url = "https://treenod.atlassian.net/wiki/api/v2/pages/73294938154"
params = {"body-format": "atlas_doc_format"}
response = requests.get(url, headers=headers, params=params)
```

**Result:** ✅ Success (HTTP 200)

**Response Data:**
- Page ID: 73294938154
- Title: "test"
- Status: "current"
- Body format: atlas_doc_format available
- ADF content includes:
  - Heading level 2: "head32"
  - Heading level 3: "head 3"
  - Nested bullet lists (2 levels deep)
  - Code block with wide breakout mode
  - Empty paragraphs

**Key Findings:**
1. ADF content is returned as a JSON string in `body.atlas_doc_format.value`
2. Each node has a `localId` attribute for tracking
3. Code blocks can have `marks` array with layout attributes (e.g., breakout mode)
4. Response time: ~200ms

### Jira API Test

**Test Issue:** https://treenod.atlassian.net/browse/DATAANAL-8214

**Request:**
```python
url = "https://treenod.atlassian.net/rest/api/3/issue/DATAANAL-8214"
params = {
    "fields": "summary,status,description,assignee,reporter,comment,worklog,issuelinks,created,updated",
    "expand": "renderedFields"
}
response = requests.get(url, headers=headers, params=params)
```

**Result:** ✅ Success (HTTP 200)

**Response Data:**
- Issue Key: DATAANAL-8214
- Issue ID: 227768
- Summary: "[포코링클] 리뷰현황 리포트 중/하 우선순위 및 작업 전달 작업"
- Status: "완료" (Done)
- Created: 2025-09-29T17:52:34.097+0900
- Updated: 2025-12-03T10:14:43.231+0900
- Assignee: Lizzy(이지민) (jimin02@treenod.com)
- Comments: 2 comments retrieved
- Worklogs: 13 worklog entries
- Linked Issues: 0

**Key Findings:**
1. Description, comments, and worklog comments are in ADF format
2. `renderedFields` provides HTML version of text fields
3. Comments are paginated (maxResults: 20 by default)
4. Worklogs include both human-readable (`timeSpent`) and seconds (`timeSpentSeconds`)
5. User information includes accountId, displayName, email, and timezone
6. Response time: ~150ms
7. Korean characters are properly encoded in UTF-8

---

## Rate Limiting and Best Practices

### Rate Limits

#### Jira API
- **Per-issue write operations:**
  - 20 operations per 2 seconds per issue
  - 100 operations per 30 seconds per issue
- Cost-based limits vary by request type and authentication method
- Free apps: Rate limits begin on or after August 18, 2025

#### Confluence API
- Similar cost-based system to Jira
- Specific limits not publicly documented
- Monitor `X-RateLimit-Remaining` header

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
Retry-After: 60
```

### Best Practices

#### 1. Request Optimization
- Request only needed fields using `fields` parameter
- Use specific field names instead of `*all` when possible
- Avoid unnecessary `expand` parameters
- Cache responses when data doesn't change frequently

#### 2. Error Handling
```python
def api_request_with_retry(func, max_retries=5):
    """Execute API request with exponential backoff"""
    for attempt in range(max_retries):
        response = func()

        if response.status_code == 200:
            return response

        if response.status_code == 429:
            # Rate limited
            retry_after = int(response.headers.get('Retry-After', 60))
            wait_time = min(retry_after * (2 ** attempt), 300)
            time.sleep(wait_time)
            continue

        if response.status_code >= 500:
            # Server error - retry with backoff
            wait_time = min(2 ** attempt, 60)
            time.sleep(wait_time)
            continue

        # Client error - don't retry
        response.raise_for_status()

    raise Exception(f"Max retries ({max_retries}) exceeded")
```

#### 3. Batch Operations
- Group multiple read operations when possible
- Use JQL search for multiple Jira issues instead of individual requests
- For Confluence, use `/pages` endpoint with filters

#### 4. Pagination
```python
def fetch_all_comments(issue_key):
    """Fetch all comments with pagination"""
    comments = []
    start_at = 0
    max_results = 50

    while True:
        url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/comment"
        params = {
            "startAt": start_at,
            "maxResults": max_results
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        comments.extend(data['comments'])

        if len(data['comments']) < max_results:
            break

        start_at += max_results

    return comments
```

#### 5. Authentication Security
- Store API tokens in environment variables
- Never commit tokens to version control
- Use secrets management systems in production
- Rotate tokens periodically
- Use least-privilege OAuth scopes when possible

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 201 | Created | Resource created successfully |
| 204 | No Content | Success with no response body |
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Verify authentication credentials |
| 403 | Forbidden | Check user permissions |
| 404 | Not Found | Verify resource ID/key exists |
| 429 | Too Many Requests | Implement exponential backoff |
| 500 | Internal Server Error | Retry with backoff |
| 503 | Service Unavailable | Retry after delay |

### Error Response Structures

#### Confluence Error
```json
{
  "statusCode": 404,
  "message": "Page not found",
  "reason": "Not Found"
}
```

#### Jira Error
```json
{
  "errorMessages": [
    "Issue does not exist or you do not have permission to see it."
  ],
  "errors": {
    "customfield_10050": "Field is required"
  }
}
```

### Error Handling Pattern

```python
def handle_api_error(response):
    """Handle API errors with appropriate logging and exceptions"""

    if response.status_code == 200:
        return response.json()

    # Log error details
    error_context = {
        "status_code": response.status_code,
        "url": response.url,
        "headers": dict(response.headers),
        "body": response.text
    }

    if response.status_code == 401:
        raise AuthenticationError("Invalid credentials", error_context)

    if response.status_code == 403:
        raise PermissionError("Insufficient permissions", error_context)

    if response.status_code == 404:
        raise NotFoundError("Resource not found", error_context)

    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        raise RateLimitError(f"Rate limited. Retry after {retry_after}s", error_context)

    if response.status_code >= 500:
        raise ServerError("Atlassian server error", error_context)

    # Generic error
    raise APIError(f"API request failed: {response.status_code}", error_context)
```

---

## Conclusion

Both Atlassian APIs are well-structured and provide comprehensive access to Confluence pages and Jira issues. Key takeaways:

1. **Authentication**: Basic Auth with API tokens is simple and works for both APIs
2. **ADF Format**: Universal format across products, requires parsing and generation logic
3. **Performance**: Both APIs respond quickly (<300ms) with proper field selection
4. **Pagination**: Required for comments and worklogs when counts exceed limits
5. **Rate Limiting**: Must be handled with exponential backoff strategies
6. **Permissions**: API respects same permissions as web interface

### Next Steps

Refer to the Implementation Specification document for detailed implementation guidelines including:
- Python module structure
- ADF to Markdown conversion logic
- Markdown to ADF conversion logic
- File output formats
- Command-line interface design
- Error handling implementation
