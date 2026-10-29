"""PDF chapters come from the embedded outline when the PDF has one.

Numbered layout lines ("1  Introduction", listing captions, ToC rows) made the
text heuristics report hundreds of chapters for a technical book whose outline
lists 14. The outline is preferred; the heuristics remain the fallback.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pypdf = pytest.importorskip("pypdf")

from book_to_skill.utils import extract_single_file  # noqa: E402

# Body text the heuristic scan counts as 5 chapters.
_LINES = [f"Chapter {n}" for n in range(1, 6)]


def _text_pdf(path: Path, lines: list[str]) -> None:
    """Write a one-page PDF with real, extractable text (no extra deps)."""
    ops = "".join(
        f"BT /F1 12 Tf 72 {720 - 20 * i} Td ({line}) Tj ET\n" for i, line in enumerate(lines)
    ).encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(ops) + ops + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    path.write_bytes(bytes(out))


def _add_outline(path: Path) -> None:
    writer = pypdf.PdfWriter(clone_from=str(path))
    writer.add_outline_item("Cover", 0)
    writer.add_outline_item("Preface", 0)
    for part, chapters in (("Part I. Storage", ["Chapter 1", "Chapter 2"]),
                           ("Part II. Distribution", ["Chapter 3"])):
        parent = writer.add_outline_item(part, 0)
        for title in chapters:
            writer.add_outline_item(title, 0, parent=parent)
    writer.add_outline_item("Index", 0)
    with open(path, "wb") as f:
        writer.write(f)


def test_outline_wins_over_numbered_lines(tmp_path):
    pdf = tmp_path / "book.pdf"
    _text_pdf(pdf, _LINES)
    _add_outline(pdf)
    result = extract_single_file(pdf, "text", "never")
    assert result["chapters_method"] == "outline"
    assert result["chapter_headings_sample"] == ["Chapter 1", "Chapter 2", "Chapter 3"]
    assert result["chapters_detected"] == 3


def test_no_outline_falls_back_to_heuristics(tmp_path):
    pdf = tmp_path / "book.pdf"
    _text_pdf(pdf, _LINES)
    result = extract_single_file(pdf, "text", "never")
    assert result["chapters_method"] == "numeric"
    assert result["chapters_detected"] == 5
