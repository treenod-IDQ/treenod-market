"""Convert between Atlassian Document Format (ADF) and Markdown."""

import re


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

    elif node_type == 'taskList':
        return convert_task_list(node, list_depth)

    elif node_type == 'taskItem':
        return convert_task_item(node, list_depth)

    elif node_type == 'inlineCard':
        return convert_inline_card(node)

    elif node_type == 'expand':
        return convert_expand(node)

    elif node_type == 'extension':
        return convert_extension(node)

    else:
        # Unknown node type - try to extract text
        return extract_text_from_content(node.get('content', []))


def convert_task_list(node: dict, depth: int) -> str:
    """
    Convert task list (checkbox list) to markdown.

    Args:
        node: Task list ADF node
        depth: Current list nesting depth

    Returns:
        str: Markdown checkbox list
    """
    items = []
    indent = "  " * depth

    for task_item in node.get('content', []):
        if task_item.get('type') != 'taskItem':
            continue

        task_md = convert_task_item(task_item, depth)
        if task_md:
            items.append(task_md)

    return '\n'.join(items)


def convert_task_item(node: dict, depth: int) -> str:
    """
    Convert task item with DONE/TODO state to markdown checkbox.

    Args:
        node: Task item ADF node
        depth: Current list nesting depth

    Returns:
        str: Markdown checkbox item
    """
    indent = "  " * depth
    state = node.get('attrs', {}).get('state', 'TODO')
    checkbox = "[x]" if state == "DONE" else "[ ]"

    item_content = node.get('content', [])
    item_lines = []
    nested_content = []

    # Process content - separate text from nested taskList
    for child in item_content:
        child_type = child.get('type')

        if child_type == 'text':
            item_lines.append(child.get('text', ''))
        elif child_type == 'paragraph':
            item_lines.append(convert_paragraph(child))
        elif child_type == 'taskList':
            # Handle nested taskList
            nested_content.append(convert_task_list(child, depth + 1))
        else:
            # Handle other content types
            converted = convert_node_to_markdown(child, depth + 1)
            if converted:
                nested_content.append(converted)

    # Build the task item
    result_lines = []

    # First line with checkbox
    if item_lines:
        result_lines.append(f"{indent}- {checkbox} {''.join(item_lines)}")
    else:
        result_lines.append(f"{indent}- {checkbox}")

    # Add nested content
    for nested in nested_content:
        result_lines.append(nested)

    return '\n'.join(result_lines)


def convert_inline_card(node: dict) -> str:
    """
    Convert Confluence page link to markdown link.

    Args:
        node: Inline card ADF node

    Returns:
        str: Markdown link (URL-only fallback)
    """
    url = node.get('attrs', {}).get('url', '')

    if not url:
        return ""

    # URL-only fallback since fetching page title requires additional API call
    return f"[{url}]({url})"


def convert_expand(node: dict) -> str:
    """
    Convert collapsible section to HTML details tag.

    Args:
        node: Expand ADF node

    Returns:
        str: HTML details/summary element
    """
    title = node.get('attrs', {}).get('title', 'Details')
    content = node.get('content', [])

    # Convert child content recursively
    content_lines = []
    for child in content:
        child_md = convert_node_to_markdown(child)
        if child_md:
            content_lines.append(child_md)

    # Build details block
    result = f"<details>\n<summary>{title}</summary>\n"
    if content_lines:
        result += "\n" + "\n\n".join(content_lines) + "\n"
    result += "</details>"

    return result


def convert_extension(node: dict) -> str:
    """
    Convert extension macro to comment with metadata.

    Args:
        node: Extension ADF node

    Returns:
        str: HTML comment with extension info
    """
    attrs = node.get('attrs', {})
    extension_title = attrs.get('parameters', {}).get('extensionTitle', '')

    if not extension_title:
        extension_title = attrs.get('text', 'Unknown extension')

    return f"<!-- Extension: {extension_title} -->"


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

        elif item.get('type') == 'inlineCard':
            parts.append(convert_inline_card(item))

    return ''.join(parts)


def convert_bullet_list(node: dict, depth: int) -> str:
    """Convert bullet list to markdown."""
    items = []
    indent = "  " * depth

    for list_item in node.get('content', []):
        if list_item.get('type') != 'listItem':
            continue

        item_content = list_item.get('content', [])
        first_line = None
        nested_blocks = []

        for child in item_content:
            if child.get('type') == 'paragraph':
                if first_line is None:
                    first_line = convert_paragraph(child)
                else:
                    nested_blocks.append(convert_paragraph(child))
            elif child.get('type') in ('bulletList', 'orderedList', 'taskList'):
                nested = convert_node_to_markdown(child, depth + 1)
                nested_blocks.append(nested)
            else:
                converted = convert_node_to_markdown(child, depth + 1)
                if converted:
                    nested_blocks.append(converted)

        # First line gets the bullet
        if first_line is not None:
            items.append(f"{indent}- {first_line}")
        else:
            items.append(f"{indent}-")

        # Nested blocks are added as-is (they already have proper indentation)
        for block in nested_blocks:
            items.append(block)

    return '\n'.join(items)


def convert_ordered_list(node: dict, depth: int) -> str:
    """Convert ordered list to markdown."""
    items = []
    indent = "  " * depth

    for i, list_item in enumerate(node.get('content', []), 1):
        if list_item.get('type') != 'listItem':
            continue

        item_content = list_item.get('content', [])
        first_line = None
        nested_blocks = []

        for child in item_content:
            if child.get('type') == 'paragraph':
                if first_line is None:
                    first_line = convert_paragraph(child)
                else:
                    nested_blocks.append(convert_paragraph(child))
            elif child.get('type') in ('bulletList', 'orderedList', 'taskList'):
                nested = convert_node_to_markdown(child, depth + 1)
                nested_blocks.append(nested)
            else:
                converted = convert_node_to_markdown(child, depth + 1)
                if converted:
                    nested_blocks.append(converted)

        # First line gets the number
        if first_line is not None:
            items.append(f"{indent}{i}. {first_line}")
        else:
            items.append(f"{indent}{i}.")

        # Nested blocks are added as-is (they already have proper indentation)
        for block in nested_blocks:
            items.append(block)

    return '\n'.join(items)


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


def add_spacing_before_blocks(content: list) -> list:
    """
    Add empty paragraph before rule and heading nodes for visual spacing.

    Confluence pages have cramped default line-height. Adding empty paragraphs
    before horizontal rules and h2-h4 headings improves visual separation.

    Args:
        content: List of ADF content nodes

    Returns:
        list: Content with spacing paragraphs inserted
    """
    result = []
    empty_para = {"type": "paragraph", "content": []}

    for i, node in enumerate(content):
        node_type = node.get("type")

        # Add spacing before rule (but not at document start)
        if node_type == "rule" and i > 0:
            result.append({"type": "paragraph", "content": []})

        # Add spacing before h2-h4 headings (but not at document start)
        if node_type == "heading" and i > 0:
            level = node.get("attrs", {}).get("level", 1)
            if level >= 2:
                result.append({"type": "paragraph", "content": []})

        result.append(node)

    return result


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

        # Code block (may be indented)
        elif line.lstrip().startswith('```'):
            indent_prefix = line[:len(line) - len(line.lstrip())]
            language = line.lstrip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith('```'):
                # Remove common indent prefix if present
                code_line = lines[i]
                if code_line.startswith(indent_prefix):
                    code_line = code_line[len(indent_prefix):]
                code_lines.append(code_line)
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
            indent = get_bullet_indent(line)
            bullet_list, i = parse_bullet_list(lines, i, indent)
            content.append(bullet_list)

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

        # Table (line starts with |)
        elif line.startswith('|'):
            table, i = parse_markdown_table(lines, i)
            if table:
                content.append(table)

        # Regular paragraph
        else:
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '```', '---', '- ', '* ', '+ ', '>', '|')) and not lines[i].lstrip().startswith('```'):
                para_lines.append(lines[i])
                i += 1

            content.append({
                "type": "paragraph",
                "content": parse_inline_markdown(' '.join(para_lines))
            })

    # Add spacing for better Confluence rendering
    content = add_spacing_before_blocks(content)

    return {
        "version": 1,
        "type": "doc",
        "content": content
    }


def _parse_column_widths(separator_line: str, total_width: int = 760) -> list:
    """
    Parse column widths from markdown table separator row.

    Uses dash count ratio to calculate pixel widths.

    Args:
        separator_line: The separator row (e.g., |------|------------------------|)
        total_width: Total table width in pixels (default 760)

    Returns:
        list: Column widths in pixels, or None if parsing fails
    """
    parts = separator_line.split('|')[1:-1]
    if not parts:
        return None

    # Count dashes in each cell
    dash_counts = []
    for part in parts:
        dashes = part.count('-')
        dash_counts.append(max(dashes, 1))

    # Calculate widths based on ratio
    total_dashes = sum(dash_counts)
    widths = [int((count / total_dashes) * total_width) for count in dash_counts]

    return widths


def parse_markdown_table(lines: list, start: int) -> tuple:
    """
    Parse markdown table into ADF table node.

    Args:
        lines: All lines
        start: Starting line index

    Returns:
        tuple: (ADF table node or None, next line index)
    """
    i = start
    rows = []
    col_widths = None

    while i < len(lines) and lines[i].startswith('|'):
        line = lines[i].strip()
        # Parse separator row for column widths
        if re.match(r'^\|[\s\-:|]+\|$', line):
            col_widths = _parse_column_widths(line)
            i += 1
            continue

        # Parse cells
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        rows.append(cells)
        i += 1

    if not rows:
        return None, start

    # Build ADF table
    table_rows = []
    for row_idx, cells in enumerate(rows):
        row_content = []
        for col_idx, cell in enumerate(cells):
            cell_type = "tableHeader" if row_idx == 0 else "tableCell"
            cell_node = {
                "type": cell_type,
                "content": [{
                    "type": "paragraph",
                    "content": parse_inline_markdown(cell) if cell else []
                }]
            }
            # Add column width if available
            if col_widths and col_idx < len(col_widths):
                cell_node["attrs"] = {"colwidth": [col_widths[col_idx]]}
            row_content.append(cell_node)
        table_rows.append({
            "type": "tableRow",
            "content": row_content
        })

    return {
        "type": "table",
        "content": table_rows
    }, i


def get_bullet_indent(line: str) -> int:
    """
    Get indentation level for bullet list item.

    Args:
        line: Line of text

    Returns:
        int: Indentation level (0, 1, 2 for depths 1-3)
    """
    spaces = len(line) - len(line.lstrip())
    return min(spaces // 2, 2)  # Max depth 3 (index 2)


def parse_bullet_list(lines: list, start: int, base_indent: int = 0) -> tuple:
    """
    Parse markdown bullet list with nested items into ADF.

    Args:
        lines: All lines
        start: Starting line index
        base_indent: Base indentation level for this list

    Returns:
        tuple: (ADF bulletList node, next line index)
    """
    list_items = []
    i = start

    while i < len(lines):
        line = lines[i]

        # Check if line is a bullet item
        if not line.lstrip().startswith(('- ', '* ', '+ ')):
            break

        indent = get_bullet_indent(line)

        # If indent is less than base, this item belongs to parent list
        if indent < base_indent:
            break

        # If indent equals base, this is our item
        if indent == base_indent:
            item_text = line.lstrip()[2:].strip()
            item_content = [{
                "type": "paragraph",
                "content": parse_inline_markdown(item_text)
            }]

            i += 1

            # Check for nested items
            if i < len(lines):
                next_line = lines[i]
                if next_line.lstrip().startswith(('- ', '* ', '+ ')):
                    next_indent = get_bullet_indent(next_line)
                    if next_indent > base_indent:
                        nested_list, i = parse_bullet_list(lines, i, next_indent)
                        item_content.append(nested_list)

            list_items.append({
                "type": "listItem",
                "content": item_content
            })
        else:
            # Indent is greater - should not happen at this level
            break

    return {"type": "bulletList", "content": list_items}, i


# Pre-compiled patterns for inline markdown (order matters: bold before italic)
_INLINE_PATTERNS = [
    (re.compile(r'\*\*(.+?)\*\*'), 'strong'),
    (re.compile(r'\*(.+?)\*'), 'em'),
    (re.compile(r'`(.+?)`'), 'code'),
    (re.compile(r'~~(.+?)~~'), 'strike'),
    (re.compile(r'\[(.+?)\]\((.+?)\)'), 'link'),
]

# Pattern for line breaks in table cells
_BR_PATTERN = re.compile(r'<br\s*/?>')


def parse_inline_markdown(text: str) -> list:
    """
    Parse inline markdown formatting to ADF nodes.

    Supports: **bold**, *italic*, `code`, ~~strike~~, [link](url), <br> line breaks

    Args:
        text: Text with inline markdown

    Returns:
        list: ADF content nodes
    """
    if not text:
        return []

    # Split by <br> or <br/> tags to handle line breaks
    segments = _BR_PATTERN.split(text)

    all_nodes = []
    for idx, segment in enumerate(segments):
        segment_nodes = _parse_segment_inline(segment)
        all_nodes.extend(segment_nodes)

        # Add hardBreak between segments (but not after last)
        if idx < len(segments) - 1:
            all_nodes.append({"type": "hardBreak"})

    return all_nodes


def _parse_segment_inline(text: str) -> list:
    """
    Parse inline markdown formatting for a single segment (without <br> tags).

    Args:
        text: Text segment with inline markdown

    Returns:
        list: ADF content nodes
    """
    if not text:
        return []

    nodes = []
    pos = 0

    while pos < len(text):
        # Find earliest match among all patterns
        earliest_match = None
        earliest_start = len(text)
        earliest_type = None

        for pattern, mark_type in _INLINE_PATTERNS:
            match = pattern.search(text, pos)
            if match and match.start() < earliest_start:
                earliest_match = match
                earliest_start = match.start()
                earliest_type = mark_type

        if earliest_match is None:
            # No more patterns, add remaining text
            if pos < len(text):
                nodes.append({"type": "text", "text": text[pos:]})
            break

        # Add text before match
        if earliest_start > pos:
            nodes.append({"type": "text", "text": text[pos:earliest_start]})

        # Add formatted text
        if earliest_type == 'link':
            nodes.append({
                "type": "text",
                "text": earliest_match.group(1),
                "marks": [{"type": "link", "attrs": {"href": earliest_match.group(2)}}]
            })
        else:
            nodes.append({
                "type": "text",
                "text": earliest_match.group(1),
                "marks": [{"type": earliest_type}]
            })

        pos = earliest_match.end()

    return nodes


def extract_text_from_content(content: list) -> str:
    """Extract plain text from ADF content array."""
    texts = []

    for item in content:
        if item.get('type') == 'text':
            texts.append(item['text'])
        elif 'content' in item:
            texts.append(extract_text_from_content(item['content']))

    return ''.join(texts)
