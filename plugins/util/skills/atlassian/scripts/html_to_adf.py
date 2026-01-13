"""Convert HTML content to Atlassian Document Format (ADF) using lxml."""

import html as html_module
import json

from lxml import html


def html_to_adf(html_content: str) -> list:
    """
    Convert HTML content to ADF nodes.

    Supports:
        - h1-h6: ADF heading nodes
        - p, span.paragraph: ADF paragraph nodes
        - ul, ol: ADF bulletList/orderedList nodes
        - table: ADF table node
        - pre, code: ADF codeBlock node
        - strong, em, code (inline): ADF marks
        - a: ADF link mark
        - hr: ADF rule node
        - blockquote: ADF blockquote node

    Args:
        html_content: HTML string to convert

    Returns:
        list: List of ADF content nodes
    """
    if not html_content or not html_content.strip():
        return []

    tree = html.fromstring(html_content)
    nodes = []

    # Process top-level elements
    for elem in _get_block_children(tree):
        node = convert_element_to_adf(elem)
        if node:
            nodes.append(node)

    return nodes


def _get_block_children(tree) -> list:
    """Get direct block-level children, handling marimo wrapper spans and custom elements."""
    # If root is a marimo markdown wrapper span, get its children
    if tree.tag == 'span' and 'markdown' in tree.get('class', ''):
        return list(tree)

    # Handle marimo-ui-element wrapper - extract children
    if tree.tag == 'marimo-ui-element':
        children = []
        for child in tree:
            children.extend(_get_block_children(child))
        return children if children else [tree]

    # Handle marimo-table directly
    if tree.tag == 'marimo-table':
        return [tree]

    # If root is html/body/div, traverse down
    if tree.tag in ('html', 'body', 'div'):
        children = []
        for child in tree:
            if child.tag in ('html', 'body', 'div', 'marimo-ui-element'):
                children.extend(_get_block_children(child))
            else:
                children.append(child)
        return children

    return [tree]


def convert_element_to_adf(elem) -> dict | None:
    """
    Convert single lxml HTML element to ADF node.

    Args:
        elem: lxml HtmlElement

    Returns:
        dict: ADF node or None if element should be skipped
    """
    tag = elem.tag

    # Headings
    if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        level = int(tag[1])
        return {
            "type": "heading",
            "attrs": {"level": level},
            "content": extract_inline_content(elem)
        }

    # Paragraph - regular p or span.paragraph
    if tag == 'p' or (tag == 'span' and 'paragraph' in elem.get('class', '')):
        content = extract_inline_content(elem)
        if content:
            return {
                "type": "paragraph",
                "content": content
            }
        return None

    # Bullet list
    if tag == 'ul':
        return create_bullet_list_adf(elem)

    # Ordered list
    if tag == 'ol':
        return create_ordered_list_adf(elem)

    # Table
    if tag == 'table':
        return create_table_adf(elem)

    # Marimo table component
    if tag == 'marimo-table':
        return create_marimo_table_adf(elem)

    # Marimo UI element wrapper - process children
    if tag == 'marimo-ui-element':
        for child in elem:
            result = convert_element_to_adf(child)
            if result:
                return result
        return None

    # Code block (pre > code)
    if tag == 'pre':
        return create_code_block_adf(elem)

    # Horizontal rule
    if tag == 'hr':
        return {"type": "rule"}

    # Blockquote
    if tag == 'blockquote':
        return create_blockquote_adf(elem)

    # Skip other elements
    return None


def extract_inline_content(elem) -> list:
    """
    Extract inline content with marks (bold, italic, code, links).

    Handles mixed content with text and inline elements.

    Args:
        elem: lxml HtmlElement

    Returns:
        list: ADF text nodes with marks
    """
    content = []

    def process_node(node, inherited_marks=None):
        """Recursively process nodes, accumulating marks."""
        if inherited_marks is None:
            inherited_marks = []

        # Handle text content
        if node.text:
            text_node = {"type": "text", "text": node.text}
            if inherited_marks:
                text_node["marks"] = list(inherited_marks)
            content.append(text_node)

        # Process children
        for child in node:
            child_marks = list(inherited_marks)

            # Determine marks for this child
            if child.tag in ('strong', 'b'):
                child_marks.append({"type": "strong"})
            elif child.tag in ('em', 'i'):
                child_marks.append({"type": "em"})
            elif child.tag == 'code':
                child_marks.append({"type": "code"})
            elif child.tag == 'a':
                href = child.get('href', '')
                if href:
                    child_marks.append({"type": "link", "attrs": {"href": href}})
            elif child.tag == 'u':
                child_marks.append({"type": "underline"})
            elif child.tag in ('s', 'del', 'strike'):
                child_marks.append({"type": "strike"})

            # Recursively process this child
            process_node(child, child_marks)

            # Handle tail text (text after this element, before next sibling)
            if child.tail:
                text_node = {"type": "text", "text": child.tail}
                if inherited_marks:
                    text_node["marks"] = list(inherited_marks)
                content.append(text_node)

    process_node(elem)

    # Remove empty text nodes
    content = [n for n in content if n.get('text', '').strip() or n.get('text', '') == ' ']

    return content


def create_bullet_list_adf(elem) -> dict:
    """
    Convert ul element with nested list support using XPath.

    Args:
        elem: lxml ul element

    Returns:
        dict: ADF bulletList node
    """
    items = []

    # Select only direct li children
    for li in elem.xpath('./li'):
        item_content = _process_list_item(li)
        items.append({"type": "listItem", "content": item_content})

    return {"type": "bulletList", "content": items}


def create_ordered_list_adf(elem) -> dict:
    """
    Convert ol element with nested list support.

    Args:
        elem: lxml ol element

    Returns:
        dict: ADF orderedList node
    """
    items = []

    for li in elem.xpath('./li'):
        item_content = _process_list_item(li)
        items.append({"type": "listItem", "content": item_content})

    return {"type": "orderedList", "content": items}


def _process_list_item(li) -> list:
    """
    Process a list item, handling text and nested lists.

    Args:
        li: lxml li element

    Returns:
        list: ADF content nodes for the list item
    """
    item_content = []

    # Get direct text content (before any nested list)
    text_parts = []
    if li.text and li.text.strip():
        text_parts.append(li.text.strip())

    # Collect inline elements and their tails before nested lists
    for child in li:
        if child.tag in ('ul', 'ol'):
            # Process nested list
            if text_parts or item_content:
                # First add the text content as paragraph
                if text_parts and not item_content:
                    item_content.append({
                        "type": "paragraph",
                        "content": [{"type": "text", "text": ' '.join(text_parts)}]
                    })
                    text_parts = []

            # Add nested list
            if child.tag == 'ul':
                item_content.append(create_bullet_list_adf(child))
            else:
                item_content.append(create_ordered_list_adf(child))

            # Get tail text after nested list
            if child.tail and child.tail.strip():
                text_parts.append(child.tail.strip())
        else:
            # Inline element - get its text content
            if child.text:
                text_parts.append(child.text)
            if child.tail:
                text_parts.append(child.tail)

    # If we only have text, create a single paragraph
    if not item_content:
        text = _get_li_text(li).strip()
        if text:
            item_content.append({
                "type": "paragraph",
                "content": _extract_li_inline_content(li)
            })
        else:
            # Empty list item
            item_content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": ""}]
            })

    return item_content


def _get_li_text(li) -> str:
    """Get text from li, excluding nested list text."""
    text_parts = []
    if li.text:
        text_parts.append(li.text)

    for child in li:
        if child.tag not in ('ul', 'ol'):
            text_parts.append(child.text_content())
        if child.tail and child.tag not in ('ul', 'ol'):
            text_parts.append(child.tail)

    return ''.join(text_parts)


def _extract_li_inline_content(li) -> list:
    """Extract inline content from li, excluding nested lists."""
    content = []

    def process_node(node, inherited_marks=None):
        if inherited_marks is None:
            inherited_marks = []

        if node.text:
            text_node = {"type": "text", "text": node.text}
            if inherited_marks:
                text_node["marks"] = list(inherited_marks)
            content.append(text_node)

        for child in node:
            # Skip nested lists
            if child.tag in ('ul', 'ol'):
                if child.tail:
                    text_node = {"type": "text", "text": child.tail}
                    if inherited_marks:
                        text_node["marks"] = list(inherited_marks)
                    content.append(text_node)
                continue

            child_marks = list(inherited_marks)
            if child.tag in ('strong', 'b'):
                child_marks.append({"type": "strong"})
            elif child.tag in ('em', 'i'):
                child_marks.append({"type": "em"})
            elif child.tag == 'code':
                child_marks.append({"type": "code"})
            elif child.tag == 'a':
                href = child.get('href', '')
                if href:
                    child_marks.append({"type": "link", "attrs": {"href": href}})

            process_node(child, child_marks)

            if child.tail:
                text_node = {"type": "text", "text": child.tail}
                if inherited_marks:
                    text_node["marks"] = list(inherited_marks)
                content.append(text_node)

    process_node(li)

    content = [n for n in content if n.get('text', '')]
    return content if content else [{"type": "text", "text": ""}]


def create_table_adf(elem) -> dict:
    """
    Convert table element to ADF table node.

    Args:
        elem: lxml table element

    Returns:
        dict: ADF table node
    """
    rows = []

    # Process thead
    for tr in elem.xpath('.//thead/tr'):
        cells = []
        for th in tr.xpath('.//th'):
            cells.append({
                "type": "tableHeader",
                "content": [{
                    "type": "paragraph",
                    "content": extract_inline_content(th) or [{"type": "text", "text": ""}]
                }]
            })
        if cells:
            rows.append({"type": "tableRow", "content": cells})

    # Process tbody
    for tr in elem.xpath('.//tbody/tr'):
        cells = []
        for cell in tr.xpath('.//td | .//th'):
            cell_type = "tableHeader" if cell.tag == 'th' else "tableCell"
            cells.append({
                "type": cell_type,
                "content": [{
                    "type": "paragraph",
                    "content": extract_inline_content(cell) or [{"type": "text", "text": ""}]
                }]
            })
        if cells:
            rows.append({"type": "tableRow", "content": cells})

    # If no thead/tbody, process tr directly
    if not rows:
        for tr in elem.xpath('.//tr'):
            cells = []
            for cell in tr.xpath('.//td | .//th'):
                cell_type = "tableHeader" if cell.tag == 'th' else "tableCell"
                cells.append({
                    "type": cell_type,
                    "content": [{
                        "type": "paragraph",
                        "content": extract_inline_content(cell) or [{"type": "text", "text": ""}]
                    }]
                })
            if cells:
                rows.append({"type": "tableRow", "content": cells})

    return {"type": "table", "content": rows}


def create_marimo_table_adf(elem) -> dict | None:
    """
    Convert marimo-table custom element to ADF table node.

    Marimo tables store data in the data-data attribute as escaped JSON.
    Format: data-data='&quot;[{...}, ...]&quot;'

    Args:
        elem: lxml marimo-table element

    Returns:
        dict: ADF table node or None if no data
    """
    data_attr = elem.get('data-data')
    if not data_attr:
        return None

    try:
        # Unescape HTML entities
        json_str = html_module.unescape(data_attr)

        # Remove outer quotes if present (marimo wraps JSON string in quotes)
        json_str = json_str.strip()
        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = json_str[1:-1]

        # Unescape escaped quotes within the string
        json_str = json_str.replace('\\"', '"')
        json_str = json_str.replace('\\\\', '\\')

        # Parse JSON
        rows_data = json.loads(json_str)

        if not rows_data or not isinstance(rows_data, list):
            return None

        # Extract column headers from first row keys
        if not rows_data[0]:
            return None

        headers = list(rows_data[0].keys())

        # Build ADF table
        table_rows = []

        # Header row
        header_cells = []
        for header in headers:
            header_cells.append({
                "type": "tableHeader",
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": str(header)}]
                }]
            })
        table_rows.append({"type": "tableRow", "content": header_cells})

        # Data rows
        for row in rows_data:
            data_cells = []
            for header in headers:
                value = row.get(header, '')
                data_cells.append({
                    "type": "tableCell",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": str(value)}]
                    }]
                })
            table_rows.append({"type": "tableRow", "content": data_cells})

        return {"type": "table", "content": table_rows}

    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def create_code_block_adf(elem) -> dict:
    """
    Convert pre element to ADF codeBlock node.

    Args:
        elem: lxml pre element

    Returns:
        dict: ADF codeBlock node
    """
    # Look for code element inside pre
    code_elem = elem.find('.//code')
    if code_elem is not None:
        # Extract language from class (e.g., "language-python")
        code_class = code_elem.get('class', '')
        language = ''
        for cls in code_class.split():
            if cls.startswith('language-'):
                language = cls[9:]
                break

        code_text = code_elem.text_content()
    else:
        language = ''
        code_text = elem.text_content()

    return {
        "type": "codeBlock",
        "attrs": {"language": language},
        "content": [{"type": "text", "text": code_text}]
    }


def create_blockquote_adf(elem) -> dict:
    """
    Convert blockquote element to ADF blockquote node.

    Args:
        elem: lxml blockquote element

    Returns:
        dict: ADF blockquote node
    """
    content = []

    for child in elem:
        node = convert_element_to_adf(child)
        if node:
            content.append(node)

    # If no block children, treat as paragraph
    if not content:
        inline_content = extract_inline_content(elem)
        if inline_content:
            content.append({
                "type": "paragraph",
                "content": inline_content
            })

    return {"type": "blockquote", "content": content}


def create_adf_document(nodes: list) -> dict:
    """
    Wrap ADF nodes in a document structure.

    Args:
        nodes: List of ADF content nodes

    Returns:
        dict: Complete ADF document
    """
    return {
        "version": 1,
        "type": "doc",
        "content": nodes
    }


def create_media_single_node(file_id: str, collection: str, width: int = None) -> dict:
    """
    Create ADF mediaSingle node for an attachment.

    Args:
        file_id: Attachment file UUID
        collection: Collection name (contentId-pageId)
        width: Optional width percentage (1-100)

    Returns:
        dict: ADF mediaSingle node
    """
    media_node = {
        "type": "media",
        "attrs": {
            "type": "file",
            "id": file_id,
            "collection": collection
        }
    }

    media_single = {
        "type": "mediaSingle",
        "attrs": {"layout": "center"},
        "content": [media_node]
    }

    if width:
        media_single["attrs"]["width"] = width

    return media_single
