"""Chapter bodies must not swallow part conclusions or back matter."""

from __future__ import annotations

from book_to_skill.utils import split_chapter_contents

_FILLER = "x" * 5000


def _database_internals_fixture() -> tuple[str, list[str]]:
    lines: list[str] = []
    for number in range(1, 15):
        lines.append(f"Chapter {number}")
        lines.append(f"body-{number}")
        if number == 7:
            lines.extend(["Part I Conclusion", _FILLER, "part1-conclusion"])
        if number == 14:
            lines.extend(
                [
                    "Part II Conclusion",
                    _FILLER,
                    "part2-conclusion",
                    "Bibliography",
                    _FILLER,
                    "bib-content",
                    "Index",
                    _FILLER,
                    "index-content",
                ]
            )
    titles = [f"Chapter {n}" for n in range(1, 15)]
    return "\n".join(lines), titles


def _naive_outline_split(text: str, chapter_titles: list[str]) -> dict[str, str]:
    """Previous behavior: slice only at the next outline title (no back-matter cut)."""
    lines = text.splitlines()
    starts: list[tuple[str, int]] = []
    cursor = 0
    for title in chapter_titles:
        needle = title.casefold()
        found = None
        for index in range(cursor, len(lines)):
            if lines[index].strip().casefold() == needle:
                found = index
                break
        if found is None:
            break
        starts.append((title, found))
        cursor = found + 1
    bodies: dict[str, str] = {}
    for index, (title, start) in enumerate(starts):
        end = starts[index + 1][1] if index + 1 < len(starts) else len(lines)
        bodies[title] = "\n".join(lines[start + 1 : end])
    return bodies


def test_part_conclusions_and_back_matter_are_excluded_from_chapter_bodies():
    text, titles = _database_internals_fixture()
    before = _naive_outline_split(text, titles)
    after = dict(split_chapter_contents(text, chapter_titles=titles))

    ch7, ch14 = "Chapter 7", "Chapter 14"
    assert len(before[ch7]) > len(after[ch7]) + len(_FILLER)
    assert len(before[ch14]) > len(after[ch14]) + 2 * len(_FILLER)
    assert after[ch7] == "body-7"
    assert after[ch14] == "body-14"
    assert "part1-conclusion" not in after[ch7]
    assert "bib-content" not in after[ch14]
    assert "index-content" not in after[ch14]


def test_scan_fallback_trims_final_chapter_back_matter():
    text = "\n".join(
        [
            "Chapter 1",
            "intro",
            "Chapter 2",
            "middle",
            "Bibliography",
            "refs",
        ]
    )
    segments = split_chapter_contents(text)
    assert segments[-1] == ("Chapter 2", "middle")
