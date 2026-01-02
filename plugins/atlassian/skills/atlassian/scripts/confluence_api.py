"""Confluence page operations via REST API v2."""

import json
import os
import base64
import requests
from utils import get_auth_headers, get_base_urls, save_to_file, load_from_file
from adf_converter import adf_to_markdown, markdown_to_adf


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

    Raises:
        requests.HTTPError: If API request fails
    """
    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

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

        links = data.get("_links", {})
        if "next" not in links:
            break

        next_link = links["next"]
        if "cursor=" in next_link:
            cursor = next_link.split("cursor=")[1].split("&")[0]
        else:
            break

    return pages


def create_confluence_page(
    parent_id: str,
    title: str,
    markdown_file: str = None,
    content: str = None,
    space_id: str = None
) -> dict:
    """
    Create a new Confluence page under a parent page or folder.

    Args:
        parent_id: Parent page ID or folder ID
        title: Page title
        markdown_file: Path to markdown file (optional)
        content: Inline markdown content (optional)
        space_id: Space ID (optional, derived from parent if not provided)

    Returns:
        dict: Created page metadata

    Raises:
        requests.HTTPError: If API request fails
    """
    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

    # Get parent info to determine space (try folder first, then page)
    if not space_id:
        # Try as folder first
        folder_url = f"{confluence_url}/wiki/api/v2/folders/{parent_id}"
        response = requests.get(folder_url, headers=headers)
        if response.status_code == 200:
            folder = response.json()
            space_id = folder['spaceId']
        else:
            # Try as page
            parent_url = f"{confluence_url}/wiki/api/v2/pages/{parent_id}"
            response = requests.get(parent_url, headers=headers)
            response.raise_for_status()
            parent_page = response.json()
            space_id = parent_page['spaceId']

    # Get content
    markdown_content = ""
    if markdown_file:
        markdown_content = load_from_file(markdown_file)
        # Extract metadata if present
        if markdown_content.startswith('---'):
            parts = markdown_content.split('---', 2)
            if len(parts) >= 3:
                markdown_content = parts[2].strip()
    elif content:
        markdown_content = content

    # Convert markdown to ADF
    adf_content = markdown_to_adf(markdown_content)

    # Prepare create payload
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

    created_page = response.json()

    return {
        "id": created_page['id'],
        "title": created_page['title'],
        "version": created_page['version']['number'],
        "status": created_page['status'],
        "url": f"{confluence_url}/wiki/spaces/{created_page.get('spaceId', '')}/pages/{created_page['id']}"
    }


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


def upload_attachment(page_id: str, file_path: str, comment: str = "") -> dict:
    """
    Upload file attachment to Confluence page.

    Args:
        page_id: Confluence page ID
        file_path: Path to file to upload
        comment: Optional comment for the attachment

    Returns:
        dict: Attachment metadata (id, title, download_link)

    Raises:
        FileNotFoundError: If file doesn't exist
        requests.HTTPError: If API request fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    confluence_url, _ = get_base_urls()

    # Build auth headers manually (need X-Atlassian-Token, no Content-Type)
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

    headers = {
        "Authorization": f"Basic {base64_auth}",
        "X-Atlassian-Token": "no-check"
    }

    # Determine mime type from file extension
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf'
    }
    mime_type = mime_types.get(ext, 'application/octet-stream')

    # Prepare multipart form data
    with open(file_path, 'rb') as f:
        files = {
            'file': (filename, f, mime_type)
        }
        data = {}
        if comment:
            data['comment'] = comment

        # Upload attachment using v1 API
        url = f"{confluence_url}/wiki/rest/api/content/{page_id}/child/attachment"
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()

    result = response.json()

    # Extract first attachment from results
    if result.get('results') and len(result['results']) > 0:
        attachment = result['results'][0]
        extensions = attachment.get('extensions', {})
        return {
            "id": attachment['id'],
            "title": attachment['title'],
            "download_link": confluence_url + attachment['_links']['download'],
            "file_id": extensions.get('fileId'),  # UUID for ADF media node
            "collection": extensions.get('collectionName')  # For ADF media node
        }
    else:
        raise ValueError("No attachment information in response")


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

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new page under parent")
    create_parser.add_argument("parent_id", help="Parent page ID")
    create_parser.add_argument("-t", "--title", required=True, help="Page title")
    create_parser.add_argument("-f", "--file", help="Markdown file (optional)")
    create_parser.add_argument("-c", "--content", help="Inline content (optional)")

    # Tree command
    tree_parser = subparsers.add_parser("tree", help="Get page tree (descendants)")
    tree_parser.add_argument("page_id", help="Confluence page ID")
    tree_parser.add_argument("-d", "--depth", choices=["all", "root"], default="all",
                            help="Depth: 'all' for all descendants, 'root' for direct children only")
    tree_parser.add_argument("-o", "--output", help="Output JSON file (optional)")

    # Attach command
    attach_parser = subparsers.add_parser("attach", help="Upload file attachment to page")
    attach_parser.add_argument("page_id", help="Confluence page ID")
    attach_parser.add_argument("-f", "--file", required=True, help="File to upload")
    attach_parser.add_argument("-c", "--comment", help="Optional comment for attachment")

    # TODO: Implement sync command (documented in SKILL.md but not implemented)
    # sync_parser = subparsers.add_parser("sync", help="Sync folder to Confluence")
    # sync_parser.add_argument("folder", help="Local folder path")
    # sync_parser.add_argument("parent_id", help="Parent page ID")
    # sync_parser.add_argument("--dry-run", action="store_true", help="Preview without changes")

    args = parser.parse_args()

    if args.command == "read":
        output_file = args.output or f"confluence_{args.page_id}.md"
        result = read_confluence_page(args.page_id, output_file)
        print(f"✓ Page '{result['title']}' saved to {output_file}")

    elif args.command == "update":
        result = update_confluence_page(args.page_id, args.file, args.title)
        print(f"✓ Page '{result['title']}' updated (version {result['version']})")

    elif args.command == "create":
        result = create_confluence_page(
            args.parent_id,
            args.title,
            markdown_file=args.file,
            content=args.content
        )
        print(f"✓ Page '{result['title']}' created (id: {result['id']})")
        print(f"  URL: {result['url']}")

    elif args.command == "tree":
        pages = get_page_tree(args.page_id, args.depth)
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(pages, f, indent=2)
            print(f"✓ Found {len(pages)} pages, saved to {args.output}")
        else:
            for page in pages:
                print(f"[{page['id']}] {page['title']}")
            print(f"\n✓ Found {len(pages)} pages")

    elif args.command == "attach":
        result = upload_attachment(args.page_id, args.file, args.comment or "")
        print(f"✓ Attachment '{result['title']}' uploaded (id: {result['id']})")
        print(f"  Download: {result['download_link']}")
        if result.get('file_id'):
            print(f"  File ID (for ADF): {result['file_id']}")
            print(f"  Collection: {result['collection']}")
