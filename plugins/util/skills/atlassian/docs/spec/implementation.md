# Atlassian API Implementation Specification

## Overview

This document provides detailed specifications for implementing Python scripts to interact with Atlassian Confluence and Jira APIs. The implementation uses `uv` for package management and runs without workspace or virtual environment setup (using `--no-project` and `--with` flags).

## Requirements

### System Requirements
- Python 3.10+ (installed via uv automatically)
- uv package manager (https://docs.astral.sh/uv/)
- Internet connection for API calls

### Environment Variables
```bash
ATLASSIAN_USER_EMAIL=your_email@domain.com
ATLASSIAN_API_TOKEN=your_api_token
JIRA_URL=https://your-domain.atlassian.net
```

### Python Dependencies
- `requests` - HTTP client library
- No additional dependencies required (standard library for everything else)

---

## Architecture

### Module Structure

```
project/
├── confluence_api.py       # Confluence page operations
├── jira_api.py             # Jira issue operations
├── adf_converter.py        # ADF <-> Markdown conversion
└── utils.py                # Common utilities (auth, file I/O)
```

### Execution Pattern

All scripts should be executed using uv without workspace:
```bash
uv run --no-project --with requests python script_name.py [args]
```

---

## Module Specifications

### 1. utils.py - Common Utilities

#### Purpose
Shared utilities for authentication, environment configuration, and file operations.

#### Functions

**get_auth_headers() -> dict**
```python
def get_auth_headers() -> dict:
    """
    Create authentication headers from environment variables.

    Returns:
        dict: Headers with Basic Auth and content type

    Raises:
        EnvironmentError: If required env vars are missing
    """
    email = os.environ.get('ATLASSIAN_USER_EMAIL')
    api_token = os.environ.get('ATLASSIAN_API_TOKEN')

    if not email or not api_token:
        raise EnvironmentError(
            "Missing required environment variables: "
            "ATLASSIAN_USER_EMAIL, ATLASSIAN_API_TOKEN"
        )

    auth_string = f"{email}:{api_token}"
    auth_bytes = auth_string.encode('ascii')
    base64_auth = base64.b64encode(auth_bytes).decode('ascii')

    return {
        "Authorization": f"Basic {base64_auth}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
```

**get_base_urls() -> tuple**
```python
def get_base_urls() -> tuple:
    """
    Get Confluence and Jira base URLs from environment.

    Returns:
        tuple: (confluence_url, jira_url)

    Raises:
        EnvironmentError: If JIRA_URL is not set
    """
    jira_url = os.environ.get('JIRA_URL', '').rstrip('/')

    if not jira_url:
        raise EnvironmentError("Missing required environment variable: JIRA_URL")

    # Confluence is on the same domain
    confluence_url = jira_url.replace('/jira', '').rstrip('/')

    return confluence_url, jira_url
```

**save_to_file(content: str, filepath: str) -> None**
```python
def save_to_file(content: str, filepath: str) -> None:
    """
    Save content to file with UTF-8 encoding.

    Args:
        content: Content to save
        filepath: Output file path

    Raises:
        IOError: If file cannot be written
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
```

**load_from_file(filepath: str) -> str**
```python
def load_from_file(filepath: str) -> str:
    """
    Load content from file with UTF-8 encoding.

    Args:
        filepath: Input file path

    Returns:
        str: File content

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()
```

---

### 2. confluence_api.py - Confluence Operations

#### Purpose
Handle Confluence page reading and updating operations.

#### Functions

**read_confluence_page(page_id: str, output_file: str) -> dict**
```python
def read_confluence_page(page_id: str, output_file: str) -> dict:
    """
    Read Confluence page and save to markdown file.

    Args:
        page_id: Confluence page ID
        output_file: Path to save markdown output

    Returns:
        dict: Page metadata (id, title, version, etc.)

    Process:
        1. Fetch page with ADF format
        2. Convert ADF to Markdown
        3. Save markdown to file
        4. Return page metadata

    Raises:
        requests.HTTPError: If API request fails
    """
    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

    url = f"{confluence_url}/wiki/api/v2/pages/{page_id}"
    params = {"body-format": "atlas_doc_format"}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()

    # Extract ADF content
    adf_string = data['body']['atlas_doc_format']['value']
    adf_content = json.loads(adf_string)

    # Convert to markdown
    markdown = adf_to_markdown(adf_content)

    # Add metadata header
    metadata = f"""---
title: {data['title']}
page_id: {data['id']}
version: {data['version']['number']}
status: {data['status']}
---

"""
    full_content = metadata + markdown

    # Save to file
    save_to_file(full_content, output_file)

    return {
        "id": data['id'],
        "title": data['title'],
        "version": data['version']['number'],
        "status": data['status']
    }
```

**update_confluence_page(page_id: str, markdown_file: str, title: str = None) -> dict**
```python
def update_confluence_page(
    page_id: str,
    markdown_file: str,
    title: str = None
) -> dict:
    """
    Update Confluence page from markdown file.

    Args:
        page_id: Confluence page ID
        markdown_file: Path to markdown file
        title: Optional new title (uses existing if None)

    Returns:
        dict: Updated page metadata

    Process:
        1. Read current page to get version
        2. Load markdown from file
        3. Convert markdown to ADF
        4. Update page with new content

    Raises:
        requests.HTTPError: If API request fails
        FileNotFoundError: If markdown file doesn't exist
    """
    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

    # Get current page info
    url = f"{confluence_url}/wiki/api/v2/pages/{page_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    current_page = response.json()

    # Load markdown
    markdown_content = load_from_file(markdown_file)

    # Extract metadata if present
    if markdown_content.startswith('---'):
        parts = markdown_content.split('---', 2)
        if len(parts) >= 3:
            markdown_content = parts[2].strip()

    # Convert markdown to ADF
    adf_content = markdown_to_adf(markdown_content)

    # Prepare update payload
    payload = {
        "id": page_id,
        "status": "current",
        "title": title or current_page['title'],
        "spaceId": current_page['spaceId'],
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(adf_content)
        },
        "version": {
            "number": current_page['version']['number'] + 1,
            "message": "Updated via API"
        }
    }

    # Update page
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()

    updated_page = response.json()

    return {
        "id": updated_page['id'],
        "title": updated_page['title'],
        "version": updated_page['version']['number'],
        "status": updated_page['status']
    }
```

**get_page_tree(page_id: str, depth: str = "all") -> list**
```python
def get_page_tree(page_id: str, depth: str = "all") -> list:
    """
    Get descendants (page tree) of a Confluence page.

    Args:
        page_id: Confluence page ID
        depth: "all" for all descendants, "root" for direct children only

    Returns:
        list: List of page info dicts with keys:
            - id: Page ID
            - title: Page title
            - status: Page status
            - parent_id: Parent page ID (None for direct children of root)

    Process:
        1. Fetch descendants/children from API with pagination
        2. Collect all pages across paginated results
        3. Return flattened list of page info

    Raises:
        requests.HTTPError: If API request fails
    """
    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

    # Use children endpoint for direct children, descendants for all
    if depth == "root":
        endpoint = f"{confluence_url}/wiki/api/v2/pages/{page_id}/children"
    else:
        endpoint = f"{confluence_url}/wiki/api/v2/pages/{page_id}/descendants"

    pages = []
    cursor = None

    while True:
        params = {"limit": 250}
        if cursor:
            params["cursor"] = cursor

        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        for page in data.get("results", []):
            pages.append({
                "id": page["id"],
                "title": page["title"],
                "status": page.get("status", "current"),
                "parent_id": page.get("parentId")
            })

        # Check for next page
        links = data.get("_links", {})
        if "next" not in links:
            break

        # Extract cursor from next link
        next_link = links["next"]
        if "cursor=" in next_link:
            cursor = next_link.split("cursor=")[1].split("&")[0]
        else:
            break

    return pages
```

**create_confluence_page(parent_id: str, title: str, markdown_file: str = None, markdown_content: str = None, space_id: str = None) -> dict**
```python
def create_confluence_page(
    parent_id: str,
    title: str,
    markdown_file: str = None,
    markdown_content: str = None,
    space_id: str = None
) -> dict:
    """
    Create a new Confluence page under a parent page.

    Args:
        parent_id: Parent page ID (required)
        title: Page title
        markdown_file: Path to markdown file for content (optional)
        markdown_content: Markdown string for content (optional)
        space_id: Space ID (optional, derived from parent if not provided)

    Returns:
        dict: Created page metadata (id, title, version, status, url)

    Process:
        1. Get parent page info to retrieve space ID
        2. Load markdown from file or use provided content
        3. Convert markdown to ADF
        4. Create page via POST request

    Raises:
        requests.HTTPError: If API request fails
        ValueError: If neither markdown_file nor markdown_content provided
    """
    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

    # Get space ID from parent if not provided
    if not space_id:
        parent_url = f"{confluence_url}/wiki/api/v2/pages/{parent_id}"
        response = requests.get(parent_url, headers=headers)
        response.raise_for_status()
        space_id = response.json()['spaceId']

    # Get content
    if markdown_file:
        content = load_from_file(markdown_file)
    elif markdown_content:
        content = markdown_content
    else:
        content = ""  # Empty page

    # Remove metadata header if present
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    # Convert to ADF
    adf_content = markdown_to_adf(content)

    # Create page payload
    payload = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "parentId": parent_id,
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(adf_content)
        }
    }

    # Create page
    url = f"{confluence_url}/wiki/api/v2/pages"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    created = response.json()

    return {
        "id": created['id'],
        "title": created['title'],
        "version": created['version']['number'],
        "status": created['status'],
        "url": f"{confluence_url}/wiki/spaces/{created['spaceId']}/pages/{created['id']}"
    }
```

**sync_folder_to_confluence(folder_path: str, parent_id: str, dry_run: bool = False) -> dict**
```python
def sync_folder_to_confluence(
    folder_path: str,
    parent_id: str,
    dry_run: bool = False
) -> dict:
    """
    Sync local markdown files to Confluence pages under a parent.

    Syncs all .md files in folder to Confluence:
    - Files with page_id in frontmatter: Update existing page
    - Files without page_id: Create new page (title from frontmatter or filename)

    After sync, updates local files with page_id in frontmatter.

    Args:
        folder_path: Path to folder containing markdown files
        parent_id: Parent Confluence page ID
        dry_run: If True, only report what would be done without making changes

    Returns:
        dict: Sync results with keys:
            - created: list of created page info
            - updated: list of updated page info
            - skipped: list of skipped files with reasons
            - errors: list of error messages

    Process:
        1. Scan folder for .md files
        2. Parse frontmatter to determine if create or update
        3. Create/update pages as needed
        4. Update local files with page metadata

    File naming convention for titles:
        - Uses 'title' from frontmatter if present
        - Otherwise uses filename without .md extension
        - Converts dashes/underscores to spaces and title-cases

    Folder structure mapping:
        - Flat: All files become direct children of parent_id
        - Nested: Subfolders create child pages (folder name as title),
          files in subfolder become children of that page

    Raises:
        FileNotFoundError: If folder doesn't exist
        requests.HTTPError: If API request fails
    """
    import os
    import re

    results = {
        "created": [],
        "updated": [],
        "skipped": [],
        "errors": []
    }

    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    # Scan for markdown files
    md_files = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root, f))

    for file_path in md_files:
        try:
            content = load_from_file(file_path)
            metadata = parse_frontmatter(content)

            # Determine title
            title = metadata.get('title')
            if not title:
                filename = os.path.basename(file_path)
                title = filename[:-3]  # Remove .md
                title = re.sub(r'[-_]', ' ', title).title()

            # Determine parent for nested structure
            rel_path = os.path.relpath(file_path, folder_path)
            current_parent = parent_id

            # Handle nested folders
            parts = rel_path.split(os.sep)
            if len(parts) > 1:
                # Create or find parent pages for nested structure
                for folder_name in parts[:-1]:
                    folder_title = re.sub(r'[-_]', ' ', folder_name).title()
                    current_parent = get_or_create_child_page(
                        current_parent, folder_title, dry_run
                    )

            page_id = metadata.get('page_id')

            if dry_run:
                action = "UPDATE" if page_id else "CREATE"
                results['skipped'].append({
                    "file": file_path,
                    "action": action,
                    "title": title,
                    "reason": "dry run"
                })
                continue

            if page_id:
                # Update existing page
                result = update_confluence_page(page_id, file_path, title)
                results['updated'].append({
                    "file": file_path,
                    "page_id": result['id'],
                    "title": result['title'],
                    "version": result['version']
                })
            else:
                # Create new page
                result = create_confluence_page(
                    parent_id=current_parent,
                    title=title,
                    markdown_file=file_path
                )
                results['created'].append({
                    "file": file_path,
                    "page_id": result['id'],
                    "title": result['title']
                })

                # Update local file with page_id
                update_frontmatter(file_path, {'page_id': result['id']})

        except Exception as e:
            results['errors'].append({
                "file": file_path,
                "error": str(e)
            })

    return results


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}

    import yaml
    try:
        return yaml.safe_load(parts[1]) or {}
    except:
        return {}


def update_frontmatter(file_path: str, updates: dict) -> None:
    """Update frontmatter in markdown file with new values."""
    content = load_from_file(file_path)
    metadata = parse_frontmatter(content)

    # Merge updates
    metadata.update(updates)

    # Remove old frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            body = parts[2]
        else:
            body = content
    else:
        body = content

    # Build new frontmatter
    import yaml
    new_frontmatter = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)

    new_content = f"---\n{new_frontmatter}---\n{body}"
    save_to_file(new_content, file_path)


def get_or_create_child_page(parent_id: str, title: str, dry_run: bool = False) -> str:
    """Get existing child page by title or create new one. Returns page ID."""
    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

    # Search for existing child with this title
    children = get_page_tree(parent_id, depth="root")
    for child in children:
        if child['title'].lower() == title.lower():
            return child['id']

    # Create new page if not found (and not dry run)
    if dry_run:
        return f"NEW-{title}"  # Placeholder for dry run

    result = create_confluence_page(parent_id, title, markdown_content="")
    return result['id']
```

#### CLI Interface

```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Confluence page operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Read command
    read_parser = subparsers.add_parser("read", help="Read page to markdown")
    read_parser.add_argument("page_id", help="Confluence page ID")
    read_parser.add_argument("-o", "--output", help="Output markdown file (default: confluence_<page_id>.md)")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update page from markdown")
    update_parser.add_argument("page_id", help="Confluence page ID")
    update_parser.add_argument("-f", "--file", required=True, help="Markdown file")
    update_parser.add_argument("-t", "--title", help="New page title (optional)")

    # Tree command
    tree_parser = subparsers.add_parser("tree", help="Get page tree (descendants)")
    tree_parser.add_argument("page_id", help="Confluence page ID")
    tree_parser.add_argument("-d", "--depth", choices=["all", "root"], default="all",
                            help="Depth: 'all' for all descendants, 'root' for direct children only")
    tree_parser.add_argument("-o", "--output", help="Output JSON file (optional)")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new page under parent")
    create_parser.add_argument("parent_id", help="Parent page ID")
    create_parser.add_argument("-t", "--title", required=True, help="Page title")
    create_parser.add_argument("-f", "--file", help="Markdown file for content (optional)")
    create_parser.add_argument("-c", "--content", help="Markdown content string (optional)")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync folder of markdown files to Confluence")
    sync_parser.add_argument("folder", help="Path to folder containing markdown files")
    sync_parser.add_argument("parent_id", help="Parent Confluence page ID")
    sync_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    args = parser.parse_args()

    if args.command == "read":
        output_file = args.output or f"confluence_{args.page_id}.md"
        result = read_confluence_page(args.page_id, output_file)
        print(f"Page '{result['title']}' saved to {output_file}")

    elif args.command == "update":
        result = update_confluence_page(args.page_id, args.file, args.title)
        print(f"Page '{result['title']}' updated (version {result['version']})")

    elif args.command == "tree":
        pages = get_page_tree(args.page_id, args.depth)
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump(pages, f, indent=2)
            print(f"Found {len(pages)} pages, saved to {args.output}")
        else:
            for page in pages:
                print(f"[{page['id']}] {page['title']}")
            print(f"\nFound {len(pages)} pages")

    elif args.command == "create":
        result = create_confluence_page(
            parent_id=args.parent_id,
            title=args.title,
            markdown_file=args.file,
            markdown_content=args.content
        )
        print(f"Page '{result['title']}' created")
        print(f"  ID: {result['id']}")
        print(f"  URL: {result['url']}")

    elif args.command == "sync":
        results = sync_folder_to_confluence(args.folder, args.parent_id, args.dry_run)
        print(f"\nSync {'(dry run) ' if args.dry_run else ''}complete:")
        print(f"  Created: {len(results['created'])} pages")
        print(f"  Updated: {len(results['updated'])} pages")
        print(f"  Skipped: {len(results['skipped'])} files")
        print(f"  Errors: {len(results['errors'])}")

        if results['created']:
            print("\nCreated pages:")
            for p in results['created']:
                print(f"  - {p['title']} (ID: {p['page_id']})")

        if results['updated']:
            print("\nUpdated pages:")
            for p in results['updated']:
                print(f"  - {p['title']} (v{p['version']})")

        if results['errors']:
            print("\nErrors:")
            for e in results['errors']:
                print(f"  - {e['file']}: {e['error']}")
```

**Usage Examples:**
```bash
# Read page
uv run --no-project --with requests python confluence_api.py read 123456 -o page.md

# Update page
uv run --no-project --with requests python confluence_api.py update 123456 -f page.md

# Update page with new title
uv run --no-project --with requests python confluence_api.py update 123456 -f page.md -t "New Title"

# Get all descendants (page tree)
uv run --no-project --with requests python confluence_api.py tree 123456

# Get direct children only
uv run --no-project --with requests python confluence_api.py tree 123456 -d root

# Save page tree to JSON file
uv run --no-project --with requests python confluence_api.py tree 123456 -o tree.json

# Create new page under parent
uv run --no-project --with requests python confluence_api.py create 123456 -t "New Page Title"

# Create page with content from markdown file
uv run --no-project --with requests python confluence_api.py create 123456 -t "New Page" -f content.md

# Create page with inline content
uv run --no-project --with requests python confluence_api.py create 123456 -t "Quick Note" -c "## Hello\n\nThis is a quick note."

# Sync folder to Confluence (dry run first)
uv run --no-project --with requests,pyyaml python confluence_api.py sync ./docs 123456 --dry-run

# Sync folder to Confluence
uv run --no-project --with requests,pyyaml python confluence_api.py sync ./docs 123456

# Upload attachment to page
uv run --no-project --with requests python confluence_api.py attach 123456 -f chart.png -c "Analysis chart"
```

**upload_attachment(page_id: str, file_path: str, comment: str = "") -> dict**
```python
def upload_attachment(page_id: str, file_path: str, comment: str = "") -> dict:
    """
    Upload file attachment to Confluence page.

    Args:
        page_id: Confluence page ID
        file_path: Path to file to upload
        comment: Optional comment for the attachment

    Returns:
        dict: Attachment metadata (id, title, download_link)

    Process:
        1. Read file as binary
        2. POST to attachment endpoint with multipart form
        3. Return attachment info

    Raises:
        requests.HTTPError: If API request fails
        FileNotFoundError: If file doesn't exist

    Note: Uses v1 REST API endpoint for attachment upload.
    """
    confluence_url, _ = get_base_urls()

    email = os.environ.get('ATLASSIAN_USER_EMAIL')
    api_token = os.environ.get('ATLASSIAN_API_TOKEN')
    auth_string = f"{email}:{api_token}"
    base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')

    headers = {
        "Authorization": f"Basic {base64_auth}",
        "X-Atlassian-Token": "no-check"
    }

    url = f"{confluence_url}/wiki/rest/api/content/{page_id}/child/attachment"

    filename = os.path.basename(file_path)

    # Determine mime type
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
    }
    mime_type = mime_types.get(ext, 'application/octet-stream')

    with open(file_path, 'rb') as f:
        files = {
            'file': (filename, f, mime_type),
        }
        data = {'comment': comment} if comment else {}

        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()

    result = response.json()
    attachment = result['results'][0] if 'results' in result else result

    return {
        "id": attachment['id'],
        "title": attachment['title'],
        "download_link": attachment['_links']['download']
    }
```

---

### 3. jira_api.py - Jira Operations

#### Purpose
Handle Jira issue reading and exporting to markdown.

#### Functions

**read_jira_issue(issue_key: str, output_file: str) -> dict**
```python
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
                  "comment,worklog,issuelinks,created,updated,priority",
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
```

**format_jira_issue_markdown(issue_data: dict) -> str**
```python
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
```

#### CLI Interface

```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Jira issue operations")
    parser.add_argument("issue_key", help="Jira issue key (e.g., PROJECT-123)")
    parser.add_argument("-o", "--output", required=True, help="Output markdown file")

    args = parser.parse_args()

    result = read_jira_issue(args.issue_key, args.output)
    print(f"✓ Issue '{result['key']}: {result['summary']}' saved to {args.output}")
```

**update_jira_issue(issue_key: str, updates: dict) -> dict**
```python
def update_jira_issue(issue_key: str, updates: dict) -> dict:
    """
    Update Jira issue fields.

    Args:
        issue_key: Jira issue key (e.g., "PROJECT-123")
        updates: Dictionary of fields to update. Supported keys:
            - summary: str - Issue title
            - description: str - Markdown text (converted to ADF)
            - labels: list[str] - Labels to set (replaces existing)
            - add_labels: list[str] - Labels to add to existing
            - remove_labels: list[str] - Labels to remove
            - link: dict - Issue link with keys:
                - type: str - Link type name (e.g., "Blocks", "Relates")
                - issue: str - Target issue key
                - direction: str - "outward" or "inward" (default: "outward")

    Returns:
        dict: Updated issue metadata

    Process:
        1. Build fields payload from updates
        2. Convert description markdown to ADF if present
        3. Handle labels (set/add/remove)
        4. Create issue links separately via link API
        5. Update issue via PUT request

    Raises:
        requests.HTTPError: If API request fails
        ValueError: If invalid update fields provided
    """
    _, jira_url = get_base_urls()
    headers = get_auth_headers()

    fields = {}

    # Summary
    if 'summary' in updates:
        fields['summary'] = updates['summary']

    # Description (convert markdown to ADF)
    if 'description' in updates:
        fields['description'] = markdown_to_adf(updates['description'])

    # Labels - set directly
    if 'labels' in updates:
        fields['labels'] = updates['labels']

    # Update issue fields
    if fields:
        url = f"{jira_url}/rest/api/3/issue/{issue_key}"
        payload = {"fields": fields}
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()

    # Handle add/remove labels via update operations
    update_ops = {}
    if 'add_labels' in updates:
        update_ops['labels'] = [{"add": label} for label in updates['add_labels']]
    if 'remove_labels' in updates:
        if 'labels' not in update_ops:
            update_ops['labels'] = []
        update_ops['labels'].extend([{"remove": label} for label in updates['remove_labels']])

    if update_ops:
        url = f"{jira_url}/rest/api/3/issue/{issue_key}"
        payload = {"update": update_ops}
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()

    # Create issue link
    if 'link' in updates:
        link_data = updates['link']
        link_payload = {
            "type": {"name": link_data['type']},
            "outwardIssue" if link_data.get('direction', 'outward') == 'outward'
                else "inwardIssue": {"key": link_data['issue']},
            "inwardIssue" if link_data.get('direction', 'outward') == 'outward'
                else "outwardIssue": {"key": issue_key}
        }
        url = f"{jira_url}/rest/api/3/issueLink"
        response = requests.post(url, headers=headers, json=link_payload)
        response.raise_for_status()

    # Return updated issue info
    return read_jira_issue_metadata(issue_key)


def read_jira_issue_metadata(issue_key: str) -> dict:
    """
    Read basic Jira issue metadata without writing to file.

    Args:
        issue_key: Jira issue key

    Returns:
        dict: Issue metadata (key, summary, status, labels)
    """
    _, jira_url = get_base_urls()
    headers = get_auth_headers()

    url = f"{jira_url}/rest/api/3/issue/{issue_key}"
    params = {"fields": "summary,status,labels"}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    fields = data['fields']

    return {
        "key": data['key'],
        "summary": fields['summary'],
        "status": fields['status']['name'],
        "labels": fields.get('labels', [])
    }
```

#### CLI Interface

```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Jira issue operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Read command
    read_parser = subparsers.add_parser("read", help="Export issue to markdown")
    read_parser.add_argument("issue_key", help="Jira issue key (e.g., PROJECT-123)")
    read_parser.add_argument("-o", "--output", help="Output markdown file")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update issue fields")
    update_parser.add_argument("issue_key", help="Jira issue key")
    update_parser.add_argument("-s", "--summary", help="New summary")
    update_parser.add_argument("-d", "--description", help="Description markdown file")
    update_parser.add_argument("-l", "--labels", nargs="+", help="Set labels (replaces existing)")
    update_parser.add_argument("--add-label", action="append", dest="add_labels", help="Add label")
    update_parser.add_argument("--remove-label", action="append", dest="remove_labels", help="Remove label")
    update_parser.add_argument("--link-type", help="Link type name")
    update_parser.add_argument("--link-issue", help="Issue to link to")
    update_parser.add_argument("--link-direction", choices=["outward", "inward"], default="outward")

    args = parser.parse_args()

    if args.command == "read":
        output_file = args.output or f"{args.issue_key}.md"
        result = read_jira_issue(args.issue_key, output_file)
        print(f"Issue '{result['key']}: {result['summary']}' saved to {output_file}")

    elif args.command == "update":
        updates = {}
        if args.summary:
            updates['summary'] = args.summary
        if args.description:
            updates['description'] = load_from_file(args.description)
        if args.labels:
            updates['labels'] = args.labels
        if args.add_labels:
            updates['add_labels'] = args.add_labels
        if args.remove_labels:
            updates['remove_labels'] = args.remove_labels
        if args.link_type and args.link_issue:
            updates['link'] = {
                'type': args.link_type,
                'issue': args.link_issue,
                'direction': args.link_direction
            }

        result = update_jira_issue(args.issue_key, updates)
        print(f"Issue '{result['key']}' updated")
        print(f"  Summary: {result['summary']}")
        print(f"  Status: {result['status']}")
        print(f"  Labels: {', '.join(result['labels']) if result['labels'] else 'none'}")
```

**Usage Examples:**
```bash
# Read issue
uv run --no-project --with requests python jira_api.py read DATAANAL-8214 -o issue.md

# Update summary
uv run --no-project --with requests python jira_api.py update PROJECT-123 -s "New Summary"

# Update description from markdown file
uv run --no-project --with requests python jira_api.py update PROJECT-123 -d description.md

# Set labels (replaces all existing labels)
uv run --no-project --with requests python jira_api.py update PROJECT-123 -l bug priority-high

# Add labels to existing
uv run --no-project --with requests python jira_api.py update PROJECT-123 --add-label needs-review

# Remove labels
uv run --no-project --with requests python jira_api.py update PROJECT-123 --remove-label wontfix

# Create issue link
uv run --no-project --with requests python jira_api.py update PROJECT-123 --link-type "Blocks" --link-issue PROJECT-456

# Combined update
uv run --no-project --with requests python jira_api.py update PROJECT-123 -s "Updated Title" -d desc.md --add-label reviewed
```

---

### 4. adf_converter.py - ADF ↔ Markdown Conversion

#### Purpose
Convert between Atlassian Document Format (ADF) and Markdown.

#### Core Functions

**adf_to_markdown(adf: dict) -> str**
```python
def adf_to_markdown(adf: dict) -> str:
    """
    Convert ADF JSON to Markdown.

    Args:
        adf: ADF document dictionary

    Returns:
        str: Markdown text

    Raises:
        ValueError: If ADF structure is invalid
    """
    if adf.get('type') != 'doc':
        raise ValueError("Invalid ADF: root type must be 'doc'")

    content = adf.get('content', [])
    markdown_lines = []

    for node in content:
        markdown_lines.append(convert_node_to_markdown(node))

    return "\n\n".join(filter(None, markdown_lines))
```

**convert_node_to_markdown(node: dict, list_depth: int = 0) -> str**
```python
def convert_node_to_markdown(node: dict, list_depth: int = 0) -> str:
    """
    Convert a single ADF node to markdown.

    Args:
        node: ADF node dictionary
        list_depth: Current list nesting depth

    Returns:
        str: Markdown representation of node
    """
    node_type = node.get('type')

    if node_type == 'paragraph':
        return convert_paragraph(node)

    elif node_type == 'heading':
        level = node.get('attrs', {}).get('level', 1)
        text = extract_text_from_content(node.get('content', []))
        return f"{'#' * level} {text}"

    elif node_type == 'bulletList':
        return convert_bullet_list(node, list_depth)

    elif node_type == 'orderedList':
        return convert_ordered_list(node, list_depth)

    elif node_type == 'codeBlock':
        language = node.get('attrs', {}).get('language', '')
        code = extract_text_from_content(node.get('content', []))
        return f"```{language}\n{code}\n```"

    elif node_type == 'blockquote':
        content = node.get('content', [])
        lines = []
        for child in content:
            child_md = convert_node_to_markdown(child, list_depth)
            for line in child_md.split('\n'):
                lines.append(f"> {line}")
        return '\n'.join(lines)

    elif node_type == 'rule':
        return '---'

    elif node_type == 'table':
        return convert_table(node)

    else:
        # Unknown node type - try to extract text
        return extract_text_from_content(node.get('content', []))
```

**convert_paragraph(node: dict) -> str**
```python
def convert_paragraph(node: dict) -> str:
    """Convert paragraph node to markdown with inline formatting."""
    content = node.get('content', [])

    if not content:
        return ""

    parts = []
    for item in content:
        if item.get('type') == 'text':
            text = item['text']
            marks = item.get('marks', [])

            # Apply marks
            for mark in marks:
                mark_type = mark['type']

                if mark_type == 'strong':
                    text = f"**{text}**"
                elif mark_type == 'em':
                    text = f"*{text}*"
                elif mark_type == 'code':
                    text = f"`{text}`"
                elif mark_type == 'strike':
                    text = f"~~{text}~~"
                elif mark_type == 'underline':
                    text = f"<u>{text}</u>"
                elif mark_type == 'link':
                    href = mark.get('attrs', {}).get('href', '')
                    title = mark.get('attrs', {}).get('title', '')
                    if title:
                        text = f"[{text}]({href} \"{title}\")"
                    else:
                        text = f"[{text}]({href})"

            parts.append(text)

        elif item.get('type') == 'hardBreak':
            parts.append("  \n")

        elif item.get('type') == 'emoji':
            parts.append(item.get('attrs', {}).get('text', ''))

        elif item.get('type') == 'mention':
            parts.append(item.get('attrs', {}).get('text', '@user'))

    return ''.join(parts)
```

**convert_bullet_list(node: dict, depth: int) -> str**
```python
def convert_bullet_list(node: dict, depth: int) -> str:
    """Convert bullet list to markdown."""
    items = []
    indent = "  " * depth

    for list_item in node.get('content', []):
        if list_item.get('type') != 'listItem':
            continue

        item_content = list_item.get('content', [])
        item_lines = []

        for child in item_content:
            if child.get('type') == 'paragraph':
                item_lines.append(convert_paragraph(child))
            elif child.get('type') in ('bulletList', 'orderedList'):
                nested = convert_node_to_markdown(child, depth + 1)
                item_lines.append(nested)

        # First line gets the bullet
        if item_lines:
            items.append(f"{indent}- {item_lines[0]}")
            # Additional lines are indented
            for line in item_lines[1:]:
                items.append(f"{indent}  {line}")

    return '\n'.join(items)
```

**convert_ordered_list(node: dict, depth: int) -> str**
```python
def convert_ordered_list(node: dict, depth: int) -> str:
    """Convert ordered list to markdown."""
    items = []
    indent = "  " * depth

    for i, list_item in enumerate(node.get('content', []), 1):
        if list_item.get('type') != 'listItem':
            continue

        item_content = list_item.get('content', [])
        item_lines = []

        for child in item_content:
            if child.get('type') == 'paragraph':
                item_lines.append(convert_paragraph(child))
            elif child.get('type') in ('bulletList', 'orderedList'):
                nested = convert_node_to_markdown(child, depth + 1)
                item_lines.append(nested)

        # First line gets the number
        if item_lines:
            items.append(f"{indent}{i}. {item_lines[0]}")
            # Additional lines are indented
            for line in item_lines[1:]:
                items.append(f"{indent}   {line}")

    return '\n'.join(items)
```

**convert_table(node: dict) -> str**
```python
def convert_table(node: dict) -> str:
    """Convert table to markdown."""
    rows = []

    for row_node in node.get('content', []):
        if row_node.get('type') != 'tableRow':
            continue

        cells = []
        for cell_node in row_node.get('content', []):
            cell_type = cell_node.get('type')
            if cell_type in ('tableHeader', 'tableCell'):
                cell_content = []
                for content_node in cell_node.get('content', []):
                    cell_content.append(convert_node_to_markdown(content_node))
                cells.append(' '.join(cell_content))

        rows.append(cells)

    if not rows:
        return ""

    # Build markdown table
    md_lines = []

    # Header row
    md_lines.append("| " + " | ".join(rows[0]) + " |")

    # Separator
    md_lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")

    # Data rows
    for row in rows[1:]:
        md_lines.append("| " + " | ".join(row) + " |")

    return '\n'.join(md_lines)
```

**markdown_to_adf(markdown: str) -> dict**
```python
def markdown_to_adf(markdown: str) -> dict:
    """
    Convert Markdown to ADF JSON.

    Args:
        markdown: Markdown text

    Returns:
        dict: ADF document

    Note: This is a simplified conversion supporting common markdown elements.
    Complex tables and advanced formatting may require additional handling.
    """
    import re

    content = []
    lines = markdown.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Heading
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            text = line.lstrip('#').strip()
            content.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": [{"type": "text", "text": text}]
            })
            i += 1

        # Code block
        elif line.startswith('```'):
            language = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            content.append({
                "type": "codeBlock",
                "attrs": {"language": language},
                "content": [{"type": "text", "text": '\n'.join(code_lines)}]
            })
            i += 1

        # Horizontal rule
        elif line.strip() in ('---', '***', '___'):
            content.append({"type": "rule"})
            i += 1

        # Bullet list
        elif line.lstrip().startswith(('- ', '* ', '+ ')):
            list_items = []
            while i < len(lines) and lines[i].lstrip().startswith(('- ', '* ', '+ ')):
                item_text = lines[i].lstrip()[2:].strip()
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": parse_inline_markdown(item_text)
                    }]
                })
                i += 1

            content.append({
                "type": "bulletList",
                "content": list_items
            })

        # Ordered list
        elif re.match(r'^\s*\d+\.\s', line):
            list_items = []
            while i < len(lines) and re.match(r'^\s*\d+\.\s', lines[i]):
                item_text = re.sub(r'^\s*\d+\.\s', '', lines[i])
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": parse_inline_markdown(item_text)
                    }]
                })
                i += 1

            content.append({
                "type": "orderedList",
                "content": list_items
            })

        # Blockquote
        elif line.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                quote_lines.append(lines[i][1:].strip())
                i += 1

            content.append({
                "type": "blockquote",
                "content": [{
                    "type": "paragraph",
                    "content": parse_inline_markdown(' '.join(quote_lines))
                }]
            })

        # Regular paragraph
        else:
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '```', '---', '- ', '* ', '+ ', '>')):
                para_lines.append(lines[i])
                i += 1

            content.append({
                "type": "paragraph",
                "content": parse_inline_markdown(' '.join(para_lines))
            })

    return {
        "version": 1,
        "type": "doc",
        "content": content
    }
```

**parse_inline_markdown(text: str) -> list**
```python
def parse_inline_markdown(text: str) -> list:
    """
    Parse inline markdown formatting to ADF nodes.

    Supports: **bold**, *italic*, `code`, ~~strike~~, [link](url)

    Args:
        text: Text with inline markdown

    Returns:
        list: ADF content nodes
    """
    import re

    # Simplified parser - handles one formatting type at a time
    nodes = []

    # Pattern for inline elements (ordered by specificity)
    patterns = [
        (r'\*\*(.+?)\*\*', 'strong'),  # Bold
        (r'\*(.+?)\*', 'em'),  # Italic
        (r'`(.+?)`', 'code'),  # Code
        (r'~~(.+?)~~', 'strike'),  # Strikethrough
        (r'\[(.+?)\]\((.+?)\)', 'link'),  # Link
    ]

    remaining = text
    current_pos = 0

    while remaining:
        found = False

        for pattern, mark_type in patterns:
            match = re.search(pattern, remaining)

            if match:
                # Add text before match
                if match.start() > 0:
                    nodes.append({
                        "type": "text",
                        "text": remaining[:match.start()]
                    })

                # Add formatted text
                if mark_type == 'link':
                    link_text = match.group(1)
                    link_url = match.group(2)
                    nodes.append({
                        "type": "text",
                        "text": link_text,
                        "marks": [{
                            "type": "link",
                            "attrs": {"href": link_url}
                        }]
                    })
                else:
                    nodes.append({
                        "type": "text",
                        "text": match.group(1),
                        "marks": [{"type": mark_type}]
                    })

                # Continue with remaining text
                remaining = remaining[match.end():]
                found = True
                break

        if not found:
            # No more patterns found, add remaining text
            nodes.append({
                "type": "text",
                "text": remaining
            })
            break

    return nodes
```

**extract_text_from_content(content: list) -> str**
```python
def extract_text_from_content(content: list) -> str:
    """Extract plain text from ADF content array."""
    texts = []

    for item in content:
        if item.get('type') == 'text':
            texts.append(item['text'])
        elif 'content' in item:
            texts.append(extract_text_from_content(item['content']))

    return ''.join(texts)
```

---

## Output Format Specifications

### Confluence Page Markdown Format

```markdown
---
title: Page Title
page_id: 123456
version: 5
status: current
---

# Page Content Starts Here

Regular paragraph text with **bold** and *italic* formatting.

## Heading 2

- Bullet point 1
- Bullet point 2
  - Nested bullet

## Code Example

```python
def example():
    return "hello"
```

## Tables

| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |
```

### Jira Issue Markdown Format

```markdown
# PROJECT-123: Issue Summary

## Metadata

- **Status:** Done
- **Created:** 2025-09-29T17:52:34.097+0900
- **Updated:** 2025-12-03T10:14:43.231+0900
- **Priority:** High
- **Assignee:** John Doe (john@example.com)
- **Reporter:** Jane Smith

## Description

Issue description content in markdown format.

## Linked Issues

- **blocks:** [PROJECT-124] Related issue (In Progress)
- **is blocked by:** [PROJECT-122] Prerequisite issue (Done)

## Comments

### John Doe - 2025-09-30T10:00:00.000+0900

First comment content.

### Jane Smith - 2025-10-01T15:30:00.000+0900

Second comment content.

## Work Logs

- **John Doe** - 2h 30m - 2025-09-30T09:00:00.000+0900
- **Jane Smith** - 1h - 2025-10-01T14:00:00.000+0900

**Total Time Logged:** 3h 30m
```

---

## Error Handling Implementation

### Standard Error Classes

```python
class AtlassianAPIError(Exception):
    """Base exception for Atlassian API errors."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class AuthenticationError(AtlassianAPIError):
    """Authentication failed."""
    pass

class PermissionError(AtlassianAPIError):
    """Insufficient permissions."""
    pass

class NotFoundError(AtlassianAPIError):
    """Resource not found."""
    pass

class RateLimitError(AtlassianAPIError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: int, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)
```

### Request Wrapper with Retry Logic

```python
def api_request_with_retry(
    func: callable,
    max_retries: int = 5,
    initial_backoff: float = 1.0
) -> requests.Response:
    """
    Execute API request with exponential backoff retry.

    Args:
        func: Function that returns requests.Response
        max_retries: Maximum retry attempts
        initial_backoff: Initial backoff time in seconds

    Returns:
        requests.Response: Successful response

    Raises:
        AtlassianAPIError: If request fails after retries
    """
    for attempt in range(max_retries):
        response = func()

        # Success
        if response.status_code == 200:
            return response

        # Rate limited
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            wait_time = min(retry_after * (2 ** attempt), 300)
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue

        # Server error - retry
        if response.status_code >= 500:
            wait_time = min(initial_backoff * (2 ** attempt), 60)
            print(f"Server error. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            continue

        # Client error - don't retry
        handle_client_error(response)

    raise AtlassianAPIError(
        f"Max retries ({max_retries}) exceeded",
        status_code=response.status_code
    )

def handle_client_error(response: requests.Response):
    """Handle 4xx client errors."""
    if response.status_code == 401:
        raise AuthenticationError(
            "Authentication failed. Check API token.",
            status_code=401,
            response=response.json() if response.text else None
        )

    if response.status_code == 403:
        raise PermissionError(
            "Insufficient permissions.",
            status_code=403,
            response=response.json() if response.text else None
        )

    if response.status_code == 404:
        raise NotFoundError(
            "Resource not found.",
            status_code=404,
            response=response.json() if response.text else None
        )

    # Generic client error
    raise AtlassianAPIError(
        f"Client error: {response.status_code}",
        status_code=response.status_code,
        response=response.json() if response.text else None
    )
```

---

## Testing Guidelines

### Unit Tests

Test files should be created for each module:

- `test_utils.py` - Test authentication and file operations
- `test_confluence_api.py` - Test Confluence operations (mock API calls)
- `test_jira_api.py` - Test Jira operations (mock API calls)
- `test_adf_converter.py` - Test ADF ↔ Markdown conversion

### Integration Tests

```bash
# Test Confluence read
uv run --no-project --with requests python confluence_api.py read 73294938154 -o test_output.md

# Test Confluence create
uv run --no-project --with requests python confluence_api.py create 73294938154 -t "Test Page" -c "## Test"

# Test Confluence sync (dry run)
uv run --no-project --with requests,pyyaml python confluence_api.py sync ./test_docs 73294938154 --dry-run

# Test Jira read
uv run --no-project --with requests python jira_api.py read DATAANAL-8214 -o test_issue.md

# Test Jira update
uv run --no-project --with requests python jira_api.py update DATAANAL-8214 --add-label test-label
```

### Test Cases

**ADF to Markdown:**
- Headings (levels 1-6)
- Paragraphs with inline formatting (bold, italic, code)
- Bullet lists (nested)
- Ordered lists (nested)
- Code blocks (with/without language)
- Blockquotes
- Tables
- Links
- Mixed content

**Markdown to ADF:**
- All above cases in reverse
- Edge cases (empty lines, special characters)
- Invalid markdown handling

**API Operations:**
- Successful requests
- Authentication failures
- Permission errors
- Not found errors
- Rate limiting
- Server errors

---

## Implementation Checklist

- [x] Install uv package manager
- [x] Set up environment variables
- [x] Implement `utils.py`
  - [x] Authentication header creation
  - [x] Base URL configuration
  - [x] File I/O functions
- [x] Implement `adf_converter.py`
  - [x] ADF to Markdown conversion
  - [x] Markdown to ADF conversion
  - [x] Support all common node types
  - [x] Handle inline formatting
- [x] Implement `confluence_api.py`
  - [x] Read page function
  - [x] Update page function
  - [x] Get page tree function
  - [x] Create page function (supports folder parent)
  - [x] Sync folder function
  - [x] Upload attachment function (returns file_id for ADF)
  - [x] CLI interface
  - [x] Error handling
- [x] Implement `jira_api.py`
  - [x] Read issue function
  - [x] Format issue as markdown
  - [x] Update issue function
  - [x] Issue link function
  - [x] CLI interface
  - [x] Error handling
- [x] Test with real API calls
  - [x] Confluence page read
  - [x] Confluence page update
  - [x] Confluence page create
  - [x] Confluence folder sync
  - [x] Confluence attachment upload
  - [x] Jira issue read
  - [x] Jira issue update
- [x] Handle edge cases
  - [x] Large pages/issues
  - [x] Special characters in content
  - [x] Empty fields
  - [x] Pagination (comments, worklogs)
- [x] Add comprehensive error handling
- [x] Document usage examples
- [ ] Create test suite

---

## Next Steps

1. Start with `utils.py` and `adf_converter.py` as they are foundational
2. Implement `confluence_api.py` read functionality first
3. Test with real Confluence page
4. Implement `jira_api.py` read functionality
5. Test with real Jira issue
6. Implement Confluence update functionality
7. Test complete workflow: Read → Edit → Update
8. Add comprehensive error handling
9. Create documentation and examples
10. Add unit tests for converters

---

## Reference Commands

```bash
# Install uv (Windows PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Set environment variables (Windows Command Prompt)
set ATLASSIAN_USER_EMAIL=your_email@domain.com
set ATLASSIAN_API_TOKEN=your_token
set JIRA_URL=https://your-domain.atlassian.net

# Set environment variables (Windows PowerShell)
$env:ATLASSIAN_USER_EMAIL="your_email@domain.com"
$env:ATLASSIAN_API_TOKEN="your_token"
$env:JIRA_URL="https://your-domain.atlassian.net"

# Confluence operations
uv run --no-project --with requests python confluence_api.py read <page_id> -o output.md
uv run --no-project --with requests python confluence_api.py update <page_id> -f input.md
uv run --no-project --with requests python confluence_api.py tree <page_id>
uv run --no-project --with requests python confluence_api.py create <parent_id> -t "Title" -f content.md
uv run --no-project --with requests,pyyaml python confluence_api.py sync ./docs <parent_id>
uv run --no-project --with requests python confluence_api.py attach <page_id> -f image.png -c "Comment"

# Jira operations
uv run --no-project --with requests python jira_api.py read <issue_key> -o output.md
uv run --no-project --with requests python jira_api.py update <issue_key> -s "New Summary"
uv run --no-project --with requests python jira_api.py update <issue_key> --add-label label-name
uv run --no-project --with requests python jira_api.py update <issue_key> --link-type "Blocks" --link-issue OTHER-123
```
