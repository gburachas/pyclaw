"""Tests for Telegram channel features."""

import pytest

from pyclaw.channels.telegram import markdown_to_telegram_html


# ---------------------------------------------------------------------------
# markdown_to_telegram_html
# ---------------------------------------------------------------------------


class TestMarkdownToTelegramHTML:
    def test_empty_string(self):
        assert markdown_to_telegram_html("") == ""

    def test_plain_text(self):
        assert markdown_to_telegram_html("Hello world") == "Hello world"

    def test_bold_double_star(self):
        assert markdown_to_telegram_html("**bold**") == "<b>bold</b>"

    def test_bold_double_underscore(self):
        assert markdown_to_telegram_html("__bold__") == "<b>bold</b>"

    def test_italic(self):
        assert markdown_to_telegram_html("_italic_") == "<i>italic</i>"

    def test_strikethrough(self):
        assert markdown_to_telegram_html("~~strike~~") == "<s>strike</s>"

    def test_inline_code(self):
        result = markdown_to_telegram_html("use `foo()` here")
        assert result == "use <code>foo()</code> here"

    def test_inline_code_html_escaped(self):
        result = markdown_to_telegram_html("use `a<b>` here")
        assert "<code>a&lt;b&gt;</code>" in result

    def test_code_block(self):
        md = "```python\nprint('hi')\n```"
        result = markdown_to_telegram_html(md)
        assert "<pre><code>" in result
        assert "print(&#x27;hi&#x27;)" in result or "print('hi')" in result

    def test_code_block_html_escaped(self):
        md = "```\na < b && c > d\n```"
        result = markdown_to_telegram_html(md)
        assert "&lt;" in result
        assert "&amp;" in result

    def test_link(self):
        result = markdown_to_telegram_html("[click](https://example.com)")
        assert result == '<a href="https://example.com">click</a>'

    def test_header_stripped(self):
        result = markdown_to_telegram_html("## Title")
        assert result == "Title"

    def test_blockquote_stripped(self):
        result = markdown_to_telegram_html("> quoted text")
        assert result == "quoted text"

    def test_list_marker_dash(self):
        result = markdown_to_telegram_html("- item one")
        assert result == "• item one"

    def test_list_marker_star(self):
        result = markdown_to_telegram_html("* item two")
        assert result == "• item two"

    def test_html_entities_escaped(self):
        result = markdown_to_telegram_html("a < b & c > d")
        assert "a &lt; b &amp; c &gt; d" == result

    def test_mixed_formatting(self):
        md = "**bold** and _italic_ and `code`"
        result = markdown_to_telegram_html(md)
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<code>code</code>" in result

    def test_code_block_preserves_markdown(self):
        """Markdown inside code blocks should NOT be converted."""
        md = "```\n**not bold** _not italic_\n```"
        result = markdown_to_telegram_html(md)
        assert "<b>" not in result
        assert "<i>" not in result
        assert "**not bold**" in result or "not bold" in result
