"""Document parsing using docling (with fast-path for plain text and markdown)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from openlibrarian.exceptions import ParseError

# Docling converter is expensive to initialize — use a module-level singleton.
_converter = None

PLAIN_TEXT_EXTENSIONS = {".md", ".txt", ".markdown", ".rst"}


@dataclass
class Section:
    """A section of a parsed document."""

    heading: str
    content: str
    level: int = 0


@dataclass
class ParsedDocument:
    """Result of parsing a document file."""

    source_path: str
    full_text: str
    sections: list[Section] = field(default_factory=list)


def _get_converter():
    """Lazy-init the docling DocumentConverter singleton."""
    global _converter
    if _converter is None:
        try:
            from docling.document_converter import DocumentConverter

            _converter = DocumentConverter()
        except ImportError as e:
            raise ParseError(
                "docling is required for PDF/DOCX parsing. Install with: pip install docling"
            ) from e
    return _converter


def _parse_markdown_sections(text: str) -> list[Section]:
    """Extract sections from markdown-style headings."""
    sections: list[Section] = []
    current_heading = ""
    current_level = 0
    current_lines: list[str] = []

    for line in text.split("\n"):
        match = re.match(r"^(#{1,6})\s+(.*)", line)
        if match:
            if current_lines or current_heading:
                sections.append(
                    Section(
                        heading=current_heading,
                        content="\n".join(current_lines).strip(),
                        level=current_level,
                    )
                )
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Last section
    if current_lines or current_heading:
        sections.append(
            Section(
                heading=current_heading,
                content="\n".join(current_lines).strip(),
                level=current_level,
            )
        )

    return sections


def parse_file(file_path: Path, source_path: str) -> ParsedDocument:
    """Parse a document file and return structured content.

    Args:
        file_path: Local path to the downloaded file.
        source_path: Original path in the document source (used as identifier).
    """
    suffix = file_path.suffix.lower()

    # Fast path for plain text files — skip docling entirely
    if suffix in PLAIN_TEXT_EXTENSIONS:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise ParseError(f"Failed to read {source_path}: {e}") from e
        sections = _parse_markdown_sections(text) if suffix in {".md", ".markdown"} else []
        return ParsedDocument(source_path=source_path, full_text=text, sections=sections)

    # Use docling for everything else (PDF, DOCX, PPTX, HTML, etc.)
    try:
        converter = _get_converter()
        result = converter.convert(str(file_path))
        text = result.document.export_to_markdown()
        sections = _parse_markdown_sections(text)
        return ParsedDocument(source_path=source_path, full_text=text, sections=sections)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Failed to parse {source_path}: {e}") from e
