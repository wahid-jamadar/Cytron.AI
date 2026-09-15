"""
modules/documentation_generator/parser.py
─────────────────────────────────────────
Parser to convert Markdown text into structured blocks (Headings, Paragraphs, Lists, Code Blocks, Tables).
"""

import re
from typing import List, Dict, Any


def parse_markdown_to_blocks(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parses a markdown string into a structured list of blocks.
    Supported block types:
      - heading (level: int, text: str)
      - paragraph (text: str)
      - code_block (language: str, code: str)
      - list (ordered: bool, items: List[str])
      - table (headers: List[str], rows: List[List[str]])
    """
    if not markdown_text:
        return []

    lines = markdown_text.splitlines()
    blocks: List[Dict[str, Any]] = []

    in_code_block = False
    code_lang = ""
    code_lines: List[str] = []

    in_table = False
    table_headers: List[str] = []
    table_rows: List[List[str]] = []

    in_list = False
    list_ordered = False
    list_items: List[str] = []

    def close_table():
        nonlocal in_table, table_headers, table_rows
        if in_table:
            if table_headers or table_rows:
                blocks.append({
                    "type": "table",
                    "headers": table_headers,
                    "rows": table_rows
                })
            table_headers = []
            table_rows = []
            in_table = False

    def close_list():
        nonlocal in_list, list_ordered, list_items
        if in_list:
            if list_items:
                blocks.append({
                    "type": "list",
                    "ordered": list_ordered,
                    "items": list_items
                })
            list_items = []
            in_list = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Handle Code Block
        if stripped.startswith("```"):
            if in_code_block:
                # Close code block
                blocks.append({
                    "type": "code_block",
                    "language": code_lang,
                    "code": "\n".join(code_lines)
                })
                code_lines = []
                code_lang = ""
                in_code_block = False
            else:
                # Close other open blocks first
                close_table()
                close_list()
                in_code_block = True
                code_lang = stripped[3:].strip()
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Handle Headings
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            close_table()
            close_list()
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            # Remove inline formatting like bold or links inside heading text for cleaner titles
            text = re.sub(r"\*\*|__", "", text)
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
            blocks.append({
                "type": "heading",
                "level": level,
                "text": text
            })
            i += 1
            continue

        # Handle Tables
        if stripped.startswith("|"):
            close_list()
            # Split cell values
            cells = [c.strip() for c in stripped.split("|")]
            # Remove empty first and last elements due to leading/trailing pipes
            if cells and cells[0] == "":
                cells.pop(0)
            if cells and cells[-1] == "":
                cells.pop()

            # Check if this is a separator line (e.g., |---|---|)
            is_separator = False
            if cells:
                # If cells contain only dashes, colons, and spaces
                is_separator = all(re.match(r"^:?-+:?$", cell) for cell in cells)

            if is_separator:
                # Just skip separator lines
                in_table = True
            elif not in_table:
                # First line of table is header
                table_headers = cells
                table_rows = []
                in_table = True
            else:
                # Row of table
                table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                close_table()

        # Handle Lists (Ordered / Unordered)
        unordered_match = re.match(r"^([\-\*\+])\s+(.*)$", stripped)
        ordered_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)

        if unordered_match or ordered_match:
            # Determine list type
            is_ordered = bool(ordered_match)
            item_text = ordered_match.group(2).strip() if is_ordered else unordered_match.group(2).strip()
            
            # Clean formatting markers from list items
            item_text = re.sub(r"\*\*|__", "", item_text)
            item_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", item_text)

            if in_list and list_ordered == is_ordered:
                list_items.append(item_text)
            else:
                close_list()
                in_list = True
                list_ordered = is_ordered
                list_items = [item_text]
            i += 1
            continue
        else:
            if in_list:
                close_list()

        # Handle Paragraphs (ignore blank lines)
        if stripped != "":
            # Check if we can append this line to the previous paragraph
            # to make paragraphs flow nicer
            clean_text = re.sub(r"\*\*|__", "", stripped)
            clean_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_text)
            
            if blocks and blocks[-1]["type"] == "paragraph":
                blocks[-1]["text"] += " " + clean_text
            else:
                blocks.append({
                    "type": "paragraph",
                    "text": clean_text
                })
        
        i += 1

    # Close any remaining blocks
    close_table()
    close_list()

    return blocks
