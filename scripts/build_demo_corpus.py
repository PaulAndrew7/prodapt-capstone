"""Build the fictional Kestrel Mutual policy PDFs and manifest from authored source text.

    uv run --project services/api python scripts/build_demo_corpus.py

Input:  data/demo/policies/<version_id>.md  (front matter + "# N Section" / "## N.M Clause")
Output: data/demo/pdf/<version_id>.pdf and data/demo/manifest.json

Output is byte-for-byte reproducible (ReportLab invariant mode), so manifest hashes only
change when the text or layout changes. The PDFs are the ingestion input; the Markdown is
the authored, reviewable source. Evaluation answer keys never live in this directory.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

rl_config.invariant = 1  # deterministic IDs/timestamps for stable hashes

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data" / "demo"
ORG = {"id": "org_kestrel", "slug": "kestrel", "name": "Kestrel Mutual", "fictional": True}
NOTICE = (
    "Fictional policy written for a software demonstration. Kestrel Mutual is an invented "
    "organization. This is not real policy, law or regulatory guidance."
)
PROVENANCE = {
    "kind": "synthetic",
    "author": "Clause capstone project",
    "license": "Authored for this project; free to use for demonstration and evaluation.",
    "allowed_use": "Demonstration, testing and evaluation of Clause.",
}

HEADING = re.compile(r"^(#{1,2}) (\d+(?:\.\d+)*) (.+)$")


@dataclass
class Block:
    level: int
    number: str
    heading: str
    body: list[str] = field(default_factory=list)


@dataclass
class Source:
    meta: dict[str, str]
    blocks: list[Block]


def parse_source(path: Path) -> Source:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: missing front matter")
    head, body = text[4:].split("\n---\n", 1)
    meta: dict[str, str] = {}
    for line in head.splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    blocks: list[Block] = []
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        m = HEADING.match(line)
        if m:
            blocks.append(Block(len(m.group(1)), m.group(2), m.group(3)))
        elif blocks:
            blocks[-1].body.append(line)
        else:
            raise ValueError(f"{path.name}: text before the first heading: {line!r}")
    return Source(meta, blocks)


def long_date(value: str) -> str:
    d = date.fromisoformat(value)
    return f"{d.day} {d.strftime('%B %Y')}"


def styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=10.5, leading=15, alignment=TA_LEFT
    )
    return {
        "title": ParagraphStyle(
            "title", parent=base, fontName="Helvetica-Bold", fontSize=22, leading=27
        ),
        "meta": ParagraphStyle(
            "meta", parent=base, fontSize=10, leading=15, textColor=colors.HexColor("#333333")
        ),
        "notice": ParagraphStyle(
            "notice",
            parent=base,
            fontSize=9.5,
            leading=13.5,
            borderColor=colors.black,
            borderWidth=1,
            borderPadding=8,
            backColor=colors.HexColor("#F2F2F2"),
        ),
        "section": ParagraphStyle(
            "section",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            spaceBefore=14,
            spaceAfter=4,
        ),
        "clause": ParagraphStyle(
            "clause",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=15,
            spaceBefore=8,
            spaceAfter=1,
        ),
        "body": base,
    }


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def story_for(src: Source) -> list[object]:
    s = styles()
    m = src.meta
    effective = f"Effective {long_date(m['effective_from'])}"
    if m.get("effective_to"):
        effective += f" to {long_date(m['effective_to'])}"
    story: list[object] = [
        Paragraph(esc(m["title"]), s["title"]),
        Spacer(1, 10),
        Paragraph(
            f"Version {esc(m['version'])} &middot; {effective} &middot; Status: {esc(m['status'])}",
            s["meta"],
        ),
        Paragraph(f"Owner: {esc(m['owner'])} &middot; Category: {esc(m['category'])}", s["meta"]),
        Paragraph(f"Applies to: {esc(m['business_area'])}", s["meta"]),
        Spacer(1, 18),
        Paragraph(esc(NOTICE), s["notice"]),
        PageBreak(),
    ]
    for block in src.blocks:
        heading = Paragraph(
            f"{block.number}&nbsp;&nbsp;{esc(block.heading)}",
            s["section" if block.level == 1 else "clause"],
        )
        body = [Paragraph(esc(p), s["body"]) for p in block.body]
        story.append(KeepTogether([heading, *body[:1]]))
        story.extend(body[1:])
    return story


def numbered_canvas(title: str, label: str) -> type[rl_canvas.Canvas]:
    class NumberedCanvas(rl_canvas.Canvas):
        """Defers page output so the footer can say "Page N of M"."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
            self._pages: list[dict[str, object]] = []

        def showPage(self) -> None:
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total: int) -> None:
            width, height = A4
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#555555"))
            self.drawString(2.2 * cm, height - 1.3 * cm, "KESTREL MUTUAL INTERNAL POLICY")
            self.drawRightString(
                width - 2.2 * cm, height - 1.3 * cm, "Demo corpus: fictional policy"
            )
            self.drawString(2.2 * cm, 1.2 * cm, f"{title} {label}")
            self.drawRightString(width - 2.2 * cm, 1.2 * cm, f"Page {self._pageNumber} of {total}")

    return NumberedCanvas


def build_pdf(src: Source, out: Path) -> int:
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        title=src.meta["title"],
        author="Kestrel Mutual (fictional)",
        subject=NOTICE,
    )
    doc.build(story_for(src), canvasmaker=numbered_canvas(src.meta["title"], src.meta["version"]))
    return int(doc.page)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    pdf_dir = DEMO / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    documents = []
    for md in sorted((DEMO / "policies").glob("*.md")):
        src = parse_source(md)
        m = src.meta
        version_id = f"{m['policy']}_{m['version']}"
        if md.stem != version_id:
            raise ValueError(f"{md.name}: file name must be {version_id}.md")
        out = pdf_dir / f"{version_id}.pdf"
        pages = build_pdf(src, out)
        documents.append(
            {
                "policy_id": m["policy"],
                "version_id": version_id,
                "label": m["version"],
                "title": m["title"],
                "category": m["category"],
                "business_area": m["business_area"],
                "owner": m["owner"],
                "effective_from": m["effective_from"],
                "effective_to": m["effective_to"] or None,
                "status": m["status"],
                "source": md.relative_to(DEMO).as_posix(),
                "source_sha256": sha256(md),
                "pdf": out.relative_to(DEMO).as_posix(),
                "pdf_sha256": sha256(out),
                "pages": pages,
                "sections": sum(1 for b in src.blocks if b.level == 1),
                "clauses": sum(1 for b in src.blocks if b.body),
                "provenance": PROVENANCE,
            }
        )
        print(f"{version_id:7} {pages} pages  {documents[-1]['clauses']:2} clauses  {out.name}")
    manifest = {
        "schema_version": "1.0",
        "organization": ORG,
        "notice": NOTICE,
        "documents": documents,
    }
    (DEMO / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Wrote {len(documents)} documents to data/demo/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
