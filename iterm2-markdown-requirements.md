# iTerm2 Markdown Export Tool - Requirements

## Overview

An iTerm2 Python script that converts selected terminal text (with ANSI styling) to properly formatted Markdown, suitable for pasting into Obsidian or other Markdown editors.

## Primary Use Case

Copying Claude Code output from iTerm2 and pasting it into Obsidian with formatting preserved.

## Input

- Selected text in iTerm2 terminal
- Per-character style information via iTerm2 Python API (`CellStyle`)

## Output

- Markdown-formatted text copied to macOS clipboard
- Ready to paste into Obsidian or other Markdown editors

---

## Formatting Conversions

### Text Styles

| Terminal Style | Markdown Output | Notes |
|----------------|-----------------|-------|
| Bold | `**text**` | Primary formatting used by Claude Code |
| Italic | `*text*` | Less common but should be supported |
| Bold + Italic | `***text***` | Combination |
| Underline | `<u>text</u>` | HTML fallback (Obsidian supports) |
| Strikethrough | `~~text~~` | Standard Markdown |
| Faint/Dim | Plain text | No Markdown equivalent; drop styling |
| Inverse | Plain text | No Markdown equivalent; drop styling |

### Code Detection

Detecting inline code vs code blocks is challenging since we only have color information.

#### Approach 1: Color-Based Heuristics

- Track foreground color changes
- If a colored span is:
  - Short (< ~80 chars) and inline → wrap with single backticks `` `code` ``
  - Multi-line or long → wrap with triple backticks
- Problem: False positives with other colored output

#### Approach 2: Pattern Recognition

- Look for patterns that suggest code:
  - Consistent indentation with color
  - Known syntax patterns (function names, brackets, etc.)
- Problem: Fragile and language-dependent

#### Approach 3: Conservative / Manual

- Only convert explicitly styled text (bold/italic)
- Leave colored text as-is
- User manually adds backticks if needed
- Problem: Loses code formatting

#### Recommended Approach

Start with **Approach 1** with configurable thresholds:
- Define a "default" foreground color (the main text color)
- Any text with a different foreground color is potentially code
- Short spans (configurable, default ~60 chars) on a single line → inline code
- Longer spans or multi-line → code block
- Provide a way to disable code detection if it causes problems

### Leading Whitespace

- Strip exactly 2 leading spaces from each non-empty line
- Configurable number of spaces to strip (default: 2)
- Preserve additional indentation beyond the stripped amount

### Line Handling

- Preserve blank lines
- Handle soft-wrapped lines (iTerm2's `hard_eol` property)
- Normalize line endings to `\n`

---

## Configuration Options

```python
config = {
    "strip_leading_spaces": 2,           # Number of leading spaces to remove
    "detect_code_blocks": True,          # Enable color-based code detection
    "inline_code_max_length": 60,        # Max length for inline code
    "default_fg_color": None,            # Auto-detect or specify
    "include_underline": True,           # Convert underline to <u> tags
    "debug_mode": False,                 # Output style info for debugging
}
```

---

## Edge Cases

1. **Nested styles**: Bold text that's also colored (code within emphasis)
2. **Style boundaries**: Ensure Markdown delimiters don't break mid-word
3. **Escape characters**: Escape existing `*`, `` ` ``, `~` in text that would conflict
4. **Empty selections**: Handle gracefully with user feedback
5. **Very long selections**: Performance considerations
6. **Mixed content**: Headers, lists, etc. rendered by Claude Code

---

## Testing & Debugging Tool

A companion tool that outputs the raw style information for selected text, allowing Claude Code (or developers) to see:

1. The exact text content
2. Per-character or per-run style attributes
3. Color values (RGB or indexed)
4. Line boundaries and hard EOL markers

### Output Format (JSON)

```json
{
  "lines": [
    {
      "line_number": 0,
      "hard_eol": true,
      "runs": [
        {
          "text": "  This is ",
          "start": 0,
          "end": 10,
          "style": {
            "bold": false,
            "italic": false,
            "fg_color": {"type": "indexed", "value": 7},
            "bg_color": null
          }
        },
        {
          "text": "bold",
          "start": 10,
          "end": 14,
          "style": {
            "bold": true,
            "italic": false,
            "fg_color": {"type": "indexed", "value": 7},
            "bg_color": null
          }
        },
        {
          "text": " text",
          "start": 14,
          "end": 19,
          "style": {
            "bold": false,
            "italic": false,
            "fg_color": {"type": "indexed", "value": 7},
            "bg_color": null
          }
        }
      ]
    }
  ]
}
```

This JSON can be:
- Saved to a file for Claude Code to read
- Displayed in terminal for manual inspection
- Used to validate conversion logic

---

## Trigger Mechanisms

### Option A: iTerm2 Scripts Menu
- Appears under Scripts menu
- Can be assigned keyboard shortcut in iTerm2 preferences

### Option B: Services Menu
- Register as macOS Service
- Accessible via right-click or keyboard shortcut

### Option C: Alfred/Raycast Integration
- Trigger via launcher
- More steps but flexible

**Recommended**: Start with Option A (iTerm2 Scripts Menu)

---

## Implementation Phases

### Phase 1: Debug Tool
- Create the testing tool that dumps style info to JSON
- Validate we can access all needed information
- Let Claude Code "see" what the terminal looks like

### Phase 2: Basic Conversion
- Bold → `**text**`
- Italic → `*text*`
- Strip leading spaces
- Copy to clipboard

### Phase 3: Code Detection
- Implement color-based heuristics
- Inline code with backticks
- Code blocks with triple backticks

### Phase 4: Polish
- Configuration file support
- Error handling and user feedback
- Performance optimization

---

## Open Questions

1. **Code block language detection**: Should we try to detect the language for syntax highlighting hints? (```python, ```bash, etc.)

2. **Partial line selection**: How should we handle selections that start/end mid-line?

3. **Color theme awareness**: Should we try to detect the user's color theme to better identify "default" vs "highlighted" text?

4. **Clipboard format**: Should we put both plain text and rich text (RTF/HTML) on the clipboard so apps can choose?

---

## Dependencies

- iTerm2 with Python API enabled (Preferences → General → Magic)
- Python 3.x (bundled with iTerm2's Python runtime)
- `iterm2` Python package (bundled)
- `pyperclip` or `subprocess` for clipboard access

---

## File Locations

TBD - where should the scripts live?

- iTerm2 scripts: `~/Library/Application Support/iTerm2/Scripts/`
- Configuration: `~/.config/iterm2-markdown/config.json`
- Debug output: `~/.config/iterm2-markdown/debug-output.json`
