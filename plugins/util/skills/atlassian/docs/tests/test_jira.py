import os
import sys
import json
import base64

try:
    import requests
except ImportError:
    print("requests module not available in this context")
    sys.exit(1)

# Configuration from environment
JIRA_URL = os.environ.get('JIRA_URL', '').rstrip('/')
EMAIL = os.environ.get('ATLASSIAN_USER_EMAIL')
API_TOKEN = os.environ.get('ATLASSIAN_API_TOKEN')
ISSUE_KEY = "DATAANAL-8214"

if not all([JIRA_URL, EMAIL, API_TOKEN]):
    print("Missing required environment variables")
    sys.exit(1)

# Create authentication header
auth_string = f"{EMAIL}:{API_TOKEN}"
auth_bytes = auth_string.encode('ascii')
base64_auth = base64.b64encode(auth_bytes).decode('ascii')

headers = {
    "Authorization": f"Basic {base64_auth}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Test Jira API v3 - Get issue with all required fields
print(f"Fetching Jira issue {ISSUE_KEY}...")
print(f"URL: {JIRA_URL}/rest/api/3/issue/{ISSUE_KEY}")

url = f"{JIRA_URL}/rest/api/3/issue/{ISSUE_KEY}"
params = {
    "fields": "summary,status,description,assignee,reporter,comment,worklog,issuelinks,created,updated",
    "expand": "renderedFields"
}

response = requests.get(url, headers=headers, params=params)

print(f"\nResponse Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"\n=== Jira Issue Data ===")
    print(f"Issue Key: {data.get('key')}")
    print(f"Issue ID: {data.get('id')}")

    fields = data.get('fields', {})
    print(f"\nSummary: {fields.get('summary')}")
    print(f"Status: {fields.get('status', {}).get('name')}")
    print(f"Created: {fields.get('created')}")
    print(f"Updated: {fields.get('updated')}")

    # Assignee
    assignee = fields.get('assignee')
    if assignee:
        print(f"Assignee: {assignee.get('displayName')} ({assignee.get('emailAddress', 'N/A')})")
    else:
        print(f"Assignee: Unassigned")

    # Reporter
    reporter = fields.get('reporter')
    if reporter:
        print(f"Reporter: {reporter.get('displayName')}")

    # Description
    description = fields.get('description')
    if description:
        print(f"\nDescription type: {type(description)}")
        if isinstance(description, dict):
            print(f"Description format: ADF (version {description.get('version')})")

    # Comments
    comments = fields.get('comment', {})
    comment_count = comments.get('total', 0)
    print(f"\nComments: {comment_count}")
    if comment_count > 0:
        print(f"  Showing {len(comments.get('comments', []))} comments")

    # Worklogs
    worklogs = fields.get('worklog', {})
    worklog_count = worklogs.get('total', 0)
    print(f"Worklogs: {worklog_count}")
    if worklog_count > 0:
        print(f"  Showing {len(worklogs.get('worklogs', []))} worklogs")

    # Issue links
    issue_links = fields.get('issuelinks', [])
    print(f"Linked Issues: {len(issue_links)}")
    if issue_links:
        for link in issue_links[:3]:  # Show first 3
            link_type = link.get('type', {}).get('name')
            if 'outwardIssue' in link:
                linked = link['outwardIssue']
                print(f"  - {link_type}: {linked.get('key')} - {linked.get('fields', {}).get('summary')}")
            elif 'inwardIssue' in link:
                linked = link['inwardIssue']
                print(f"  - {link_type}: {linked.get('key')} - {linked.get('fields', {}).get('summary')}")

    # Save full response
    with open('jira_issue_response.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nFull response saved to: jira_issue_response.json")

else:
    print(f"\nError Response: {response.text}")
