"""Jira issue operations via REST API v3."""

import requests
from utils import get_auth_headers, get_base_urls, save_to_file, load_from_file
from adf_converter import adf_to_markdown, markdown_to_adf


def read_jira_issue(issue_key: str, output_file: str) -> dict:
    """
    Read Jira issue and save to markdown file.

    Args:
        issue_key: Jira issue key (e.g., "PROJECT-123")
        output_file: Path to save markdown output

    Returns:
        dict: Issue metadata

    Process:
        1. Fetch issue with all required fields
        2. Convert fields to markdown format
        3. Save to file

    Raises:
        requests.HTTPError: If API request fails
    """
    _, jira_url = get_base_urls()
    headers = get_auth_headers()

    url = f"{jira_url}/rest/api/3/issue/{issue_key}"
    params = {
        "fields": "summary,status,description,assignee,reporter,"
                  "comment,worklog,issuelinks,created,updated,priority,parent",
        "expand": "renderedFields"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    fields = data['fields']

    # Build markdown content
    markdown = format_jira_issue_markdown(data)

    # Save to file
    save_to_file(markdown, output_file)

    return {
        "key": data['key'],
        "summary": fields['summary'],
        "status": fields['status']['name']
    }


def format_jira_issue_markdown(issue_data: dict) -> str:
    """
    Format Jira issue data as markdown.

    Args:
        issue_data: Full issue response from API

    Returns:
        str: Formatted markdown content
    """
    fields = issue_data['fields']
    key = issue_data['key']

    sections = []

    # Header
    sections.append(f"# {key}: {fields['summary']}\n")

    # Metadata
    sections.append("## Metadata\n")
    sections.append(f"- **Status:** {fields['status']['name']}")
    sections.append(f"- **Created:** {fields['created']}")
    sections.append(f"- **Updated:** {fields['updated']}")

    if fields.get('priority'):
        sections.append(f"- **Priority:** {fields['priority']['name']}")

    if fields.get('assignee'):
        assignee = fields['assignee']
        sections.append(f"- **Assignee:** {assignee['displayName']} ({assignee['emailAddress']})")
    else:
        sections.append("- **Assignee:** Unassigned")

    if fields.get('reporter'):
        reporter = fields['reporter']
        sections.append(f"- **Reporter:** {reporter['displayName']}")

    if fields.get('parent'):
        parent = fields['parent']
        parent_key = parent['key']
        parent_summary = parent['fields']['summary']
        sections.append(f"- **Parent:** [{parent_key}] {parent_summary}")

    sections.append("")

    # Description
    sections.append("## Description\n")
    if fields.get('description'):
        desc_markdown = adf_to_markdown(fields['description'])
        sections.append(desc_markdown)
    else:
        sections.append("*No description*")

    sections.append("")

    # Linked Issues
    if fields.get('issuelinks'):
        sections.append("## Linked Issues\n")
        for link in fields['issuelinks']:
            link_type = link['type']['name']

            if 'outwardIssue' in link:
                linked = link['outwardIssue']
                relation = link['type']['outward']
                sections.append(
                    f"- **{relation}:** [{linked['key']}] {linked['fields']['summary']} "
                    f"({linked['fields']['status']['name']})"
                )
            elif 'inwardIssue' in link:
                linked = link['inwardIssue']
                relation = link['type']['inward']
                sections.append(
                    f"- **{relation}:** [{linked['key']}] {linked['fields']['summary']} "
                    f"({linked['fields']['status']['name']})"
                )

        sections.append("")

    # Comments
    if fields.get('comment') and fields['comment']['total'] > 0:
        sections.append("## Comments\n")
        for comment in fields['comment']['comments']:
            author = comment['author']['displayName']
            created = comment['created']

            sections.append(f"### {author} - {created}\n")

            if isinstance(comment.get('body'), dict):
                comment_markdown = adf_to_markdown(comment['body'])
            else:
                comment_markdown = comment.get('body', '*No content*')

            sections.append(comment_markdown)
            sections.append("")

    # Work Logs
    if fields.get('worklog') and fields['worklog']['total'] > 0:
        sections.append("## Work Logs\n")

        total_seconds = 0
        for worklog in fields['worklog']['worklogs']:
            author = worklog['author']['displayName']
            time_spent = worklog['timeSpent']
            started = worklog['started']
            total_seconds += worklog['timeSpentSeconds']

            sections.append(f"- **{author}** - {time_spent} - {started}")

        # Summary
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        sections.append(f"\n**Total Time Logged:** {hours}h {minutes}m")
        sections.append("")

    return "\n".join(sections)


def update_jira_issue(
    issue_key: str,
    summary: str = None,
    description_file: str = None,
    labels: list = None,
    add_labels: list = None,
    remove_labels: list = None,
    link_type: str = None,
    link_issue: str = None
) -> dict:
    """
    Update Jira issue fields.

    Args:
        issue_key: Jira issue key (e.g., "PROJECT-123")
        summary: New issue summary
        description_file: Path to markdown file for description
        labels: List of labels to set (replaces existing)
        add_labels: List of labels to add
        remove_labels: List of labels to remove
        link_type: Issue link type name (e.g., "Blocks", "Relates")
        link_issue: Issue key to link to

    Returns:
        dict: Updated issue metadata

    Raises:
        requests.HTTPError: If API request fails
    """
    _, jira_url = get_base_urls()
    headers = get_auth_headers()

    fields = {}
    update = {}

    # Summary update
    if summary:
        fields["summary"] = summary

    # Description update from markdown file
    if description_file:
        markdown_content = load_from_file(description_file)
        adf_content = markdown_to_adf(markdown_content)
        fields["description"] = adf_content

    # Labels - set (replace all)
    if labels is not None:
        fields["labels"] = labels

    # Labels - add/remove operations
    if add_labels:
        update["labels"] = update.get("labels", [])
        for label in add_labels:
            update["labels"].append({"add": label})

    if remove_labels:
        update["labels"] = update.get("labels", [])
        for label in remove_labels:
            update["labels"].append({"remove": label})

    # Update issue fields
    if fields or update:
        url = f"{jira_url}/rest/api/3/issue/{issue_key}"
        payload = {}
        if fields:
            payload["fields"] = fields
        if update:
            payload["update"] = update

        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()

    # Create issue link
    if link_type and link_issue:
        link_url = f"{jira_url}/rest/api/3/issueLink"
        link_payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": link_issue},
            "outwardIssue": {"key": issue_key}
        }
        response = requests.post(link_url, headers=headers, json=link_payload)
        response.raise_for_status()

    # Fetch updated issue info
    url = f"{jira_url}/rest/api/3/issue/{issue_key}"
    params = {"fields": "summary,status,labels"}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    return {
        "key": data['key'],
        "summary": data['fields']['summary'],
        "status": data['fields']['status']['name'],
        "labels": data['fields'].get('labels', [])
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Jira issue operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Read command
    read_parser = subparsers.add_parser("read", help="Export issue to markdown")
    read_parser.add_argument("issue_key", help="Jira issue key (e.g., PROJECT-123)")
    read_parser.add_argument("-o", "--output", help="Output markdown file (default: <issue_key>.md)")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update issue fields")
    update_parser.add_argument("issue_key", help="Jira issue key (e.g., PROJECT-123)")
    update_parser.add_argument("-s", "--summary", help="New issue summary")
    update_parser.add_argument("-d", "--description", help="Markdown file for description")
    update_parser.add_argument("-l", "--labels", nargs="+", help="Labels to set (replaces existing)")
    update_parser.add_argument("--add-label", dest="add_labels", action="append", help="Label to add")
    update_parser.add_argument("--remove-label", dest="remove_labels", action="append", help="Label to remove")
    update_parser.add_argument("--link-type", help="Issue link type (e.g., Blocks, Relates)")
    update_parser.add_argument("--link-issue", help="Issue key to link to")

    args = parser.parse_args()

    if args.command == "read":
        output_file = args.output or f"{args.issue_key}.md"
        result = read_jira_issue(args.issue_key, output_file)
        print(f"✓ Issue '{result['key']}: {result['summary']}' saved to {output_file}")

    elif args.command == "update":
        result = update_jira_issue(
            args.issue_key,
            summary=args.summary,
            description_file=args.description,
            labels=args.labels,
            add_labels=args.add_labels,
            remove_labels=args.remove_labels,
            link_type=args.link_type,
            link_issue=args.link_issue
        )
        print(f"✓ Issue '{result['key']}: {result['summary']}' updated")
        if result['labels']:
            print(f"  Labels: {', '.join(result['labels'])}")
