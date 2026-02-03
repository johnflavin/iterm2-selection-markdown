#!/usr/bin/env python3
"""
iTerm2 Debug Tool: Inspect Selected Text with Style Information

This script outputs the selected text from iTerm2 along with per-character
style information (bold, italic, colors, etc.) in JSON format.

Purpose: Allow Claude Code (or developers) to "see" terminal output as
iTerm2 renders it, enabling debugging of the Markdown conversion logic.

Usage:
    1. Enable iTerm2 Python API: Preferences → General → Magic → Enable Python API
    2. Select text in iTerm2
    3. Run this script from Scripts menu (or install it there)
    4. Check output file or terminal for JSON

Installation:
    Copy to: ~/Library/Application Support/iTerm2/Scripts/
    Or run via: Scripts → Manage → New Python Script

Output:
    - Writes JSON to ~/.config/iterm2-markdown/debug-output.json
    - Also prints to iTerm2's script console
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

import iterm2


def color_to_dict(color):
    """Convert an iTerm2 Color object to a serializable dict."""
    if color is None:
        return None

    # Color can be various types - try to extract useful info
    try:
        # Check if it has RGB components
        if hasattr(color, 'red') and hasattr(color, 'green') and hasattr(color, 'blue'):
            return {
                "type": "rgb",
                "red": color.red,
                "green": color.green,
                "blue": color.blue,
            }
        # Check if it's an indexed color
        if hasattr(color, 'color_index'):
            return {
                "type": "indexed",
                "index": color.color_index,
            }
        # Fallback: stringify it
        return {"type": "unknown", "value": str(color)}
    except Exception as e:
        return {"type": "error", "error": str(e)}


def style_to_dict(style):
    """Convert an iTerm2 CellStyle object to a serializable dict."""
    if style is None:
        return None

    return {
        "bold": getattr(style, 'bold', None),
        "italic": getattr(style, 'italic', None),
        "underline": getattr(style, 'underline', None),
        "strikethrough": getattr(style, 'strikethrough', None),
        "faint": getattr(style, 'faint', None),
        "inverse": getattr(style, 'inverse', None),
        "invisible": getattr(style, 'invisible', None),
        "blink": getattr(style, 'blink', None),
        "fg_color": color_to_dict(getattr(style, 'fg_color', None)),
        "bg_color": color_to_dict(getattr(style, 'bg_color', None)),
    }


def styles_equal(s1, s2):
    """Check if two style dicts are equivalent."""
    if s1 is None and s2 is None:
        return True
    if s1 is None or s2 is None:
        return False
    return s1 == s2


async def get_selection_with_styles(session):
    """
    Get the selected text from a session along with style information.

    Returns a list of line dictionaries, each containing:
    - line_number: int
    - hard_eol: bool
    - text: str (full line text)
    - runs: list of style runs
    """
    # Get the selection
    selection = await session.async_get_selection()
    if not selection or not selection.sub_selections:
        return None, "No text selected"

    # Get selection coordinates
    sub = selection.sub_selections[0]

    # Get the windowed coordinate range
    # SubSelection has start and end as iterm2.Point objects
    start_coord = sub.start
    end_coord = sub.end

    # Get screen contents with style information
    # We need to get the lines that contain the selection
    line_info = await session.async_get_line_info()

    # Determine line range
    # Note: coordinates can be negative (scrollback) or positive (visible)
    first_line = start_coord.y
    last_line = end_coord.y
    num_lines = last_line - first_line + 1

    # Fetch the contents
    try:
        contents = await session.async_get_contents(first_line, num_lines)
    except Exception as e:
        return None, f"Failed to get contents: {e}"

    lines_data = []

    for i, line in enumerate(contents):
        line_num = first_line + i
        line_text = line.string

        # Determine selection bounds for this line
        if line_num == start_coord.y and line_num == end_coord.y:
            # Selection is entirely within this line
            sel_start = start_coord.x
            sel_end = end_coord.x
        elif line_num == start_coord.y:
            # First line of multi-line selection
            sel_start = start_coord.x
            sel_end = len(line_text)
        elif line_num == end_coord.y:
            # Last line of multi-line selection
            sel_start = 0
            sel_end = end_coord.x
        else:
            # Middle line - entire line is selected
            sel_start = 0
            sel_end = len(line_text)

        # Extract only the selected portion
        selected_text = line_text[sel_start:sel_end] if sel_end > sel_start else ""

        # Build runs of consistent styling
        runs = []
        current_run_start = sel_start
        current_style = None
        current_text = ""

        for x in range(sel_start, min(sel_end, len(line_text))):
            char = line_text[x] if x < len(line_text) else ""
            style = style_to_dict(line.style_at(x))

            if current_style is None:
                # First character
                current_style = style
                current_text = char
            elif styles_equal(style, current_style):
                # Same style, extend run
                current_text += char
            else:
                # Style changed, save current run and start new one
                if current_text:
                    runs.append({
                        "text": current_text,
                        "start": current_run_start,
                        "end": current_run_start + len(current_text),
                        "style": current_style,
                    })
                current_run_start = x
                current_style = style
                current_text = char

        # Don't forget the last run
        if current_text:
            runs.append({
                "text": current_text,
                "start": current_run_start,
                "end": current_run_start + len(current_text),
                "style": current_style,
            })

        lines_data.append({
            "line_number": line_num,
            "hard_eol": line.hard_eol,
            "full_line_text": line_text,
            "selected_text": selected_text,
            "selection_start": sel_start,
            "selection_end": sel_end,
            "runs": runs,
        })

    return lines_data, None


async def main(connection):
    """Main entry point for the iTerm2 script."""

    # Get the current app and session
    app = await iterm2.async_get_app(connection)
    session = app.current_terminal_window.current_tab.current_session

    if not session:
        print("No active session found")
        return

    # Get selection with styles
    lines_data, error = await get_selection_with_styles(session)

    if error:
        result = {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
    else:
        # Also create a simple text representation for quick viewing
        simple_text = "\n".join(
            line["selected_text"] for line in lines_data
        )

        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "session_id": session.session_id,
            "num_lines": len(lines_data),
            "simple_text": simple_text,
            "lines": lines_data,
        }

    # Output to file
    output_dir = Path.home() / ".config" / "iterm2-markdown"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "debug-output.json"

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Debug output written to: {output_file}")

    # Also print a summary
    if result["success"]:
        print(f"\nSelected {result['num_lines']} lines")
        print(f"\nSimple text:\n{result['simple_text'][:500]}...")

        # Print style summary
        all_styles = set()
        for line in lines_data:
            for run in line["runs"]:
                style = run["style"]
                if style:
                    for key, val in style.items():
                        if val and key not in ("fg_color", "bg_color"):
                            all_styles.add(key)

        if all_styles:
            print(f"\nStyles found: {', '.join(all_styles)}")
        else:
            print("\nNo text styles (bold/italic/etc) found")
    else:
        print(f"\nError: {result['error']}")


# iTerm2 script entry point
iterm2.run_until_complete(main)
