"""Split extracted page text into numbered clauses while keeping exact source offsets.

Input is the raw per-page text from `extract_pages`. Output clauses carry:
- `text`: the clause body with line wraps joined (the citation-quotable form), and
- `pieces`: for every source line, where it sits in the raw page text and in `text`,
  so any substring of `text` can be traced back to a page and character range.

Heading detection is deliberately conservative. A line counts as a heading only when its
number is a plausible successor of the previous heading (1 → 2, 2 → 2.1, 2.1 → 2.2 ...),
its title starts with a capital and does not end like a sentence. That stops wrapped body
lines such as "14 days." from being read as headings.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.domain.contracts import ClauseKind
from app.ingestion.pdf import PageText

HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(\S.*)$")
LIST_ITEM_RE = re.compile(r"^(\([a-z0-9]{1,3}\)|[a-z]\)|[•▪\-–] )")
CROSS_REF_RE = re.compile(r"\bclauses? (\d+(?:\.\d+)+)")
MAX_HEADING_WORDS = 12
MAX_NUMBER_GAP = 3

REQUIREMENT_RE = re.compile(
    r"\b(must|must not|shall|requires?|required|may only|may be \w+ only|only if|"
    r"are not permitted|is not permitted|not allowed)\b",
    re.IGNORECASE,
)
DEFINITION_RE = re.compile(r"^[“\"‘'][^”\"’']{2,60}[”\"’'] (means|is|are)\b")


@dataclass
class Line:
    page_index: int
    start: int  # offset of the first non-space character in the page's raw text
    end: int
    text: str  # whitespace-normalized


@dataclass
class Piece:
    page_index: int
    char_start: int
    char_end: int
    text_start: int
    text_end: int


@dataclass
class SegmentedClause:
    key: str
    section_path: list[str]
    section_headings: list[str]
    heading: str
    kind: ClauseKind
    text: str
    pieces: list[Piece]
    references: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def page_start(self) -> int:
        return self.pieces[0].page_index

    @property
    def page_end(self) -> int:
        return self.pieces[-1].page_index


@dataclass
class Segmentation:
    clauses: list[SegmentedClause]
    running_lines: list[str]
    warnings: list[str]


def _normalize(text: str) -> str:
    return " ".join(text.replace(" ", " ").split())


def page_lines(page: PageText) -> list[Line]:
    lines = []
    offset = 0
    for raw in page.raw_text.split("\n"):
        stripped = raw.strip()
        if stripped:
            start = offset + raw.index(stripped[0])
            lines.append(Line(page.index, start, start + len(stripped), _normalize(stripped)))
        offset += len(raw) + 1
    return lines


def _signature(text: str) -> str:
    return re.sub(r"\d+", "#", text.lower())


def find_running_lines(pages: list[list[Line]], head: int = 3, tail: int = 5) -> set[str]:
    """Signatures of lines repeated at the top or bottom of most pages (headers/footers)."""
    if len(pages) < 2:
        return set()
    counts: Counter[str] = Counter()
    for lines in pages:
        edge = lines[:head] + lines[-tail:] if len(lines) > head + tail else lines
        counts.update({_signature(line.text) for line in edge})
    threshold = max(2, math.ceil(0.6 * len(pages)))
    return {sig for sig, n in counts.items() if n >= threshold}


def _is_successor(parts: list[int], stack: list[int]) -> bool:
    depth = len(parts)
    if not stack:
        return parts == [1]
    if depth > len(stack) + 1:
        return False
    if depth == len(stack) + 1:  # first child of the current heading
        return parts[:-1] == stack and 1 <= parts[-1] <= 1 + MAX_NUMBER_GAP
    prev = stack[depth - 1]
    return parts[:-1] == stack[: depth - 1] and prev < parts[-1] <= prev + MAX_NUMBER_GAP


def _as_heading(line: Line, stack: list[int]) -> tuple[list[int], str] | None:
    m = HEADING_RE.match(line.text)
    if not m:
        return None
    number, title = m.group(1), m.group(2).strip()
    first = title[0]
    if not (first.isupper() or first in "“\"'‘"):
        return None
    if title[-1] in ".,;:" or len(title.split()) > MAX_HEADING_WORDS:
        return None
    parts = [int(p) for p in number.split(".")]
    if not _is_successor(parts, stack):
        return None
    return parts, title


def classify(heading: str, text: str) -> ClauseKind:
    h = heading.lower()
    if h.startswith("definition") or DEFINITION_RE.match(text):
        return ClauseKind.DEFINITION
    if "exception" in h or re.search(r"\binstead of (clause|the)\b", text, re.IGNORECASE):
        return ClauseKind.EXCEPTION
    if REQUIREMENT_RE.search(text):
        return ClauseKind.REQUIREMENT
    return ClauseKind.GENERAL


def segment(pages: list[PageText]) -> Segmentation:
    per_page = [page_lines(p) for p in pages]
    running = find_running_lines(per_page)
    warnings: list[str] = []

    stack: list[int] = []
    headings: dict[int, str] = {}  # depth -> title of the current heading at that depth
    clauses: list[SegmentedClause] = []
    current: SegmentedClause | None = None
    content_pages: set[int] = set()

    def finish() -> None:
        nonlocal current
        if current is not None and current.pieces:
            current.kind = classify(current.heading, current.text)
            current.references = sorted(
                {r for r in CROSS_REF_RE.findall(current.text) if r != current.key}
            )
            clauses.append(current)
        current = None

    for lines in per_page:
        for line in lines:
            if _signature(line.text) in running:
                continue
            heading = _as_heading(line, stack)
            if heading is not None:
                finish()
                parts, title = heading
                stack = parts
                depth = len(parts)
                headings = {d: t for d, t in headings.items() if d < depth}
                headings[depth] = title
                key = ".".join(str(p) for p in parts)
                path = [".".join(str(p) for p in parts[: i + 1]) for i in range(depth)]
                current = SegmentedClause(
                    key=key,
                    section_path=path,
                    section_headings=[headings[d] for d in range(1, depth + 1)],
                    heading=title,
                    kind=ClauseKind.GENERAL,
                    text="",
                    pieces=[],
                )
                content_pages.add(line.page_index)
                continue
            if current is None:
                continue  # preamble: title block, document control, cover page
            sep = ""
            if current.text:
                if LIST_ITEM_RE.match(line.text):
                    sep = "\n"
                elif not current.text.endswith("-"):
                    sep = " "
            text_start = len(current.text) + len(sep)
            current.text += sep + line.text
            current.pieces.append(
                Piece(line.page_index, line.start, line.end, text_start, len(current.text))
            )
            content_pages.add(line.page_index)
            if "�" in line.text:
                current.warnings.append("Contains characters that could not be decoded.")
    finish()

    for page in pages:
        warnings.extend(page.warnings)
    if not clauses:
        warnings.append("No numbered clauses were found; check the document structure.")
    elif stack and len(clauses) < 2:
        warnings.append("Only one clause was found; numbering may not have been recognised.")
    for page in pages[1:]:
        if page.index not in content_pages and not page.warnings:
            warnings.append(
                f"Page {page.index + 1} has text but no clause content was found on it."
            )
    return Segmentation(clauses, sorted(running), warnings)


def merge_spans(pieces: list[Piece]) -> list[Piece]:
    """Collapse consecutive line pieces on the same page into one span per page run."""
    spans: list[Piece] = []
    for p in pieces:
        last = spans[-1] if spans else None
        if last is not None and last.page_index == p.page_index:
            spans[-1] = Piece(
                p.page_index, last.char_start, p.char_end, last.text_start, p.text_end
            )
        else:
            spans.append(Piece(p.page_index, p.char_start, p.char_end, p.text_start, p.text_end))
    return spans
