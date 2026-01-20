"""Convert marimo notebook HTML exports to Confluence pages."""

import json
import os
import re
import tempfile

import requests

from utils import get_auth_headers, get_base_urls
from html_to_adf import html_to_adf, create_adf_document, create_media_single_node
from vegalite_renderer import render_vegalite_to_png
from confluence_api import upload_attachment


def extract_marimo_config(html_content: str) -> dict:
    """
    Extract __MARIMO_MOUNT_CONFIG__ JSON from marimo HTML export.

    Args:
        html_content: Full HTML content of marimo export

    Returns:
        dict: Parsed marimo mount config

    Raises:
        ValueError: If config not found or invalid JSON
    """
    # Find the config assignment
    pattern = r'window\.__MARIMO_MOUNT_CONFIG__\s*=\s*(\{[\s\S]*?\});?\s*</script>'
    match = re.search(pattern, html_content)

    if not match:
        raise ValueError("Could not find __MARIMO_MOUNT_CONFIG__ in HTML")

    json_str = match.group(1)

    # Remove trailing commas (JavaScript allows them, JSON doesn't)
    # Handle trailing comma before } or ]
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

    # Parse JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in __MARIMO_MOUNT_CONFIG__: {e}")


def extract_cell_outputs(config: dict) -> list:
    """
    Extract cell outputs from marimo config in order.

    Args:
        config: Marimo mount config dict

    Returns:
        list: List of output dicts with cell_id, output_type, and data
    """
    notebook_cells = config.get('notebook', {}).get('cells', [])
    session_cells = config.get('session', {}).get('cells', [])

    # Create mapping from cell id to session output
    session_map = {cell['id']: cell for cell in session_cells}

    outputs = []

    for nb_cell in notebook_cells:
        cell_id = nb_cell['id']
        session_cell = session_map.get(cell_id, {})

        for output in session_cell.get('outputs', []):
            if output.get('type') != 'data':
                continue

            data = output.get('data', {})

            # Skip empty outputs
            if not data or (len(data) == 1 and data.get('text/plain') == ''):
                continue

            # Determine output type priority
            if 'text/markdown' in data:
                outputs.append({
                    'cell_id': cell_id,
                    'output_type': 'markdown',
                    'data': data['text/markdown']
                })
            elif any(k.startswith('application/vnd.vegalite.v') for k in data.keys()):
                # Support vegalite v3, v4, v5+
                vegalite_key = next(k for k in data.keys() if k.startswith('application/vnd.vegalite.v'))
                spec_data = data[vegalite_key]
                # Handle both string and dict
                if isinstance(spec_data, str):
                    spec_data = json.loads(spec_data)
                outputs.append({
                    'cell_id': cell_id,
                    'output_type': 'vegalite',
                    'data': spec_data
                })
            elif 'text/html' in data:
                outputs.append({
                    'cell_id': cell_id,
                    'output_type': 'html',
                    'data': data['text/html']
                })
            elif 'text/plain' in data and data['text/plain'].strip():
                outputs.append({
                    'cell_id': cell_id,
                    'output_type': 'plain',
                    'data': data['text/plain']
                })

    return outputs


def _extract_vegalite_from_html(html_content: str) -> list:
    """
    Extract vegalite specs from marimo-mime-renderer elements in HTML.

    Args:
        html_content: HTML string that may contain marimo-mime-renderer elements

    Returns:
        list: List of dicts with 'spec' (vegalite dict) and 'index' (position in HTML)
    """
    import html as html_module
    from lxml import html

    vegalite_specs = []

    try:
        tree = html.fromstring(html_content)
    except Exception:
        return []

    # Find all marimo-mime-renderer elements
    for i, elem in enumerate(tree.iter('marimo-mime-renderer')):
        mime_type = elem.get('data-mime', '')
        data_attr = elem.get('data-data', '')

        if not mime_type or not data_attr:
            continue

        # Unescape and check if it's vegalite
        mime_type = html_module.unescape(mime_type).strip('"')
        if not mime_type.startswith('application/vnd.vegalite.v'):
            continue

        try:
            # Unescape the data attribute
            json_str = html_module.unescape(data_attr)
            json_str = json_str.strip()
            if json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1]
            json_str = json_str.replace('\\"', '"')
            json_str = json_str.replace('\\n', '\n')
            json_str = json_str.replace('\\\\', '\\')

            spec = json.loads(json_str)
            vegalite_specs.append({
                'spec': spec,
                'index': i
            })
        except (json.JSONDecodeError, ValueError):
            continue

    return vegalite_specs


def _remove_mime_renderers_from_html(html_content: str) -> str:
    """
    Remove marimo-mime-renderer elements from HTML, keeping surrounding content.

    Args:
        html_content: HTML string

    Returns:
        str: HTML with mime-renderer elements removed
    """
    from lxml import html
    from lxml.html import tostring

    try:
        tree = html.fromstring(html_content)
    except Exception:
        return html_content

    # Find and remove all marimo-mime-renderer elements
    for elem in tree.iter('marimo-mime-renderer'):
        parent = elem.getparent()
        if parent is not None:
            # Preserve tail text
            if elem.tail:
                prev = elem.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or '') + elem.tail
                else:
                    parent.text = (parent.text or '') + elem.tail
            parent.remove(elem)

    return tostring(tree, encoding='unicode')


def convert_outputs_to_adf(outputs: list, page_id: str = None) -> tuple:
    """
    Convert cell outputs to ADF nodes.

    Args:
        outputs: List of output dicts from extract_cell_outputs
        page_id: Page ID for uploading chart attachments (optional)

    Returns:
        tuple: (list of ADF nodes, list of temp chart files to upload)
    """
    adf_nodes = []
    chart_files = []
    chart_counter = 0

    for output in outputs:
        output_type = output['output_type']
        data = output['data']

        if output_type == 'markdown':
            # Parse HTML to ADF
            nodes = html_to_adf(data)
            adf_nodes.extend(nodes)

        elif output_type == 'html':
            # Extract vegalite specs from marimo-mime-renderer elements
            vegalite_specs = _extract_vegalite_from_html(data)

            # Process each vegalite chart
            for vl in vegalite_specs:
                chart_file = render_vegalite_to_png(
                    vl['spec'],
                    output_path=None,
                    scale=2.0
                )
                # Get image dimensions for proper sizing
                try:
                    from PIL import Image
                    with Image.open(chart_file) as img:
                        img_width, img_height = img.size
                except ImportError:
                    img_width, img_height = None, None

                chart_id = f"{output['cell_id']}_{chart_counter}"
                chart_counter += 1
                chart_files.append({
                    'path': chart_file,
                    'cell_id': chart_id,
                    'width': img_width,
                    'height': img_height
                })

            # Remove mime-renderer elements and convert remaining HTML to ADF
            cleaned_html = _remove_mime_renderers_from_html(data) if vegalite_specs else data
            nodes = html_to_adf(cleaned_html)
            adf_nodes.extend(nodes)

            # Add chart placeholders after the HTML content
            for vl in vegalite_specs:
                chart_id = f"{output['cell_id']}_{chart_counter - len(vegalite_specs) + vegalite_specs.index(vl)}"
                adf_nodes.append({
                    '_chart_placeholder': True,
                    'cell_id': chart_id
                })

        elif output_type == 'vegalite':
            # Render chart to PNG (defer upload)
            chart_file = render_vegalite_to_png(
                data,
                output_path=None,  # Use temp file
                scale=2.0
            )
            chart_files.append({
                'path': chart_file,
                'cell_id': output['cell_id']
            })
            # Placeholder - will be replaced after upload
            adf_nodes.append({
                '_chart_placeholder': True,
                'cell_id': output['cell_id']
            })

        elif output_type == 'plain':
            # Convert plain text to paragraph
            adf_nodes.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": data}]
            })

    return adf_nodes, chart_files


def upload_charts_and_replace_placeholders(
    page_id: str,
    adf_nodes: list,
    chart_files: list
) -> list:
    """
    Upload chart files as attachments and replace placeholders with media nodes.

    Args:
        page_id: Confluence page ID
        adf_nodes: ADF nodes with placeholders
        chart_files: List of chart file info dicts

    Returns:
        list: ADF nodes with placeholders replaced by mediaSingle nodes
    """
    # Upload each chart and build mapping
    chart_media = {}

    for chart in chart_files:
        cell_id = chart['cell_id']
        file_path = chart['path']

        # Upload attachment
        result = upload_attachment(
            page_id,
            file_path,
            comment=f"Chart from cell {cell_id}"
        )

        # Create media node with width capped to Confluence container (760px)
        if result.get('file_id') and result.get('collection'):
            # Only set width if image is larger than container
            max_width = 760
            img_width = chart.get('width')

            if img_width and img_width > max_width:
                # Cap to container width
                chart_media[cell_id] = create_media_single_node(
                    result['file_id'],
                    result['collection'],
                    width=max_width,
                    width_type="pixel"
                )
            else:
                # Use original size (no width constraint)
                chart_media[cell_id] = create_media_single_node(
                    result['file_id'],
                    result['collection']
                )

        # Clean up temp file
        try:
            os.unlink(file_path)
        except OSError:
            pass

    # Replace placeholders
    result_nodes = []
    for node in adf_nodes:
        if node.get('_chart_placeholder'):
            cell_id = node['cell_id']
            if cell_id in chart_media:
                result_nodes.append(chart_media[cell_id])
        else:
            result_nodes.append(node)

    return result_nodes


def _get_first_h1_text(adf_nodes: list) -> str | None:
    """
    Extract text from the first H1 heading in ADF nodes.

    Args:
        adf_nodes: List of ADF nodes

    Returns:
        str: Text content of first H1, or None if not found
    """
    for node in adf_nodes:
        if node.get('type') == 'heading' and node.get('attrs', {}).get('level') == 1:
            content = node.get('content', [])
            texts = []
            for item in content:
                if item.get('type') == 'text':
                    texts.append(item.get('text', ''))
            return ''.join(texts)
    return None


def _remove_first_h1(adf_nodes: list) -> list:
    """
    Remove first H1 heading from content.

    Confluence page title serves as H1, so the content's H1 should be removed
    to avoid duplication.

    Args:
        adf_nodes: List of ADF nodes

    Returns:
        list: ADF nodes with first H1 removed
    """
    if not adf_nodes:
        return adf_nodes

    first_node = adf_nodes[0]
    if first_node.get('type') == 'heading' and first_node.get('attrs', {}).get('level') == 1:
        return adf_nodes[1:]

    return adf_nodes


def convert_marimo_html(
    html_file: str,
    page_id: str = None,
    parent_id: str = None,
    title: str = None,
    include_code: bool = False
) -> dict:
    """
    Convert marimo HTML export to Confluence page.

    Args:
        html_file: Path to marimo HTML export file
        page_id: Existing page ID to update (optional)
        parent_id: Parent page ID for new page (required if no page_id)
        title: Page title (extracted from notebook if not provided)
        include_code: Include code cells in output (default: False)

    Returns:
        dict: Page metadata (id, title, version, url)

    Process:
        1. Parse HTML file to extract notebook config
        2. Extract cell outputs from session data
        3. Convert outputs to ADF nodes
        4. Upload chart images as attachments
        5. Create/update Confluence page with ADF content

    Raises:
        FileNotFoundError: If HTML file doesn't exist
        ValueError: If HTML doesn't contain marimo config
        requests.HTTPError: If API request fails
    """
    # Read HTML file
    if not os.path.exists(html_file):
        raise FileNotFoundError(f"HTML file not found: {html_file}")

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract config
    config = extract_marimo_config(html_content)

    # Extract outputs
    outputs = extract_cell_outputs(config)

    # Convert to ADF
    adf_nodes, chart_files = convert_outputs_to_adf(outputs)

    # Extract title from first H1 if not provided
    first_h1_text = _get_first_h1_text(adf_nodes)
    if not title:
        if first_h1_text:
            title = first_h1_text
        else:
            filename = config.get('filename', 'Untitled')
            title = os.path.splitext(filename)[0].replace('_', ' ').title()

    # Always remove first H1 (Confluence page title serves as H1)
    adf_nodes = _remove_first_h1(adf_nodes)

    confluence_url, _ = get_base_urls()
    headers = get_auth_headers()

    if page_id:
        # Update existing page
        # First upload charts
        if chart_files:
            adf_nodes = upload_charts_and_replace_placeholders(
                page_id, adf_nodes, chart_files
            )

        # Get current page info
        url = f"{confluence_url}/wiki/api/v2/pages/{page_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        current_page = response.json()

        # Prepare update payload
        adf_doc = create_adf_document(adf_nodes)
        payload = {
            "id": page_id,
            "status": "current",
            "title": title or current_page['title'],
            "spaceId": current_page['spaceId'],
            "body": {
                "representation": "atlas_doc_format",
                "value": json.dumps(adf_doc)
            },
            "version": {
                "number": current_page['version']['number'] + 1,
                "message": "Updated from marimo notebook"
            }
        }

        # Update page
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

    else:
        # Create new page
        if not parent_id:
            raise ValueError("parent_id required when creating new page")

        # Get parent info
        parent_url = f"{confluence_url}/wiki/api/v2/pages/{parent_id}"
        response = requests.get(parent_url, headers=headers)
        response.raise_for_status()
        parent_page = response.json()
        space_id = parent_page['spaceId']

        # Create page first (needed for attachment upload)
        adf_doc = create_adf_document([{
            "type": "paragraph",
            "content": [{"type": "text", "text": "Loading..."}]
        }])

        payload = {
            "spaceId": space_id,
            "status": "current",
            "title": title,
            "parentId": parent_id,
            "body": {
                "representation": "atlas_doc_format",
                "value": json.dumps(adf_doc)
            }
        }

        url = f"{confluence_url}/wiki/api/v2/pages"
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        page_id = result['id']

        # Upload charts if any
        if chart_files:
            adf_nodes = upload_charts_and_replace_placeholders(
                page_id, adf_nodes, chart_files
            )

        # Update with full content
        adf_doc = create_adf_document(adf_nodes)
        payload = {
            "id": page_id,
            "status": "current",
            "title": title,
            "spaceId": space_id,
            "body": {
                "representation": "atlas_doc_format",
                "value": json.dumps(adf_doc)
            },
            "version": {
                "number": result['version']['number'] + 1,
                "message": "Content from marimo notebook"
            }
        }

        url = f"{confluence_url}/wiki/api/v2/pages/{page_id}"
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

    return {
        "id": result['id'],
        "title": result['title'],
        "version": result['version']['number'],
        "status": result['status'],
        "url": f"{confluence_url}/wiki/spaces/{result.get('spaceId', '')}/pages/{result['id']}"
    }


def preview_marimo_html(html_file: str) -> dict:
    """
    Preview marimo HTML conversion without uploading.

    Args:
        html_file: Path to marimo HTML export file

    Returns:
        dict: Preview info with cell count, output types, chart count
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    config = extract_marimo_config(html_content)
    outputs = extract_cell_outputs(config)

    # Count output types
    type_counts = {}
    for output in outputs:
        t = output['output_type']
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "filename": config.get('filename'),
        "version": config.get('version'),
        "cell_count": len(config.get('notebook', {}).get('cells', [])),
        "output_count": len(outputs),
        "output_types": type_counts
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert marimo HTML export to Confluence page"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Convert command
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert marimo HTML to Confluence page"
    )
    convert_parser.add_argument("html_file", help="Path to marimo HTML export")
    convert_parser.add_argument(
        "--page-id",
        help="Existing page ID to update"
    )
    convert_parser.add_argument(
        "--parent-id",
        help="Parent page ID for new page"
    )
    convert_parser.add_argument(
        "-t", "--title",
        help="Page title (default: extracted from notebook)"
    )
    convert_parser.add_argument(
        "--include-code",
        action="store_true",
        help="Include code cells in output"
    )

    # Preview command
    preview_parser = subparsers.add_parser(
        "preview",
        help="Preview marimo HTML structure without uploading"
    )
    preview_parser.add_argument("html_file", help="Path to marimo HTML export")

    args = parser.parse_args()

    if args.command == "convert":
        if not args.page_id and not args.parent_id:
            parser.error("Either --page-id or --parent-id is required")

        result = convert_marimo_html(
            args.html_file,
            page_id=args.page_id,
            parent_id=args.parent_id,
            title=args.title,
            include_code=args.include_code
        )
        print(f"Page '{result['title']}' {'updated' if args.page_id else 'created'}")
        print(f"  ID: {result['id']}")
        print(f"  Version: {result['version']}")
        print(f"  URL: {result['url']}")

    elif args.command == "preview":
        info = preview_marimo_html(args.html_file)
        print(f"Notebook: {info['filename']}")
        print(f"Marimo version: {info['version']}")
        print(f"Cells: {info['cell_count']}")
        print(f"Outputs: {info['output_count']}")
        print("Output types:")
        for t, count in info['output_types'].items():
            print(f"  - {t}: {count}")
