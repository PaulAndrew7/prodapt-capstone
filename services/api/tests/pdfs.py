"""Tiny PDF builder for ingestion tests: each page is a list of text lines."""

import io

from reportlab import rl_config
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

rl_config.invariant = 1


def make_pdf(pages: list[list[str]], *, footer: str | None = "Test Policy v1") -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _, height = A4
    for n, lines in enumerate(pages, start=1):
        y = height - 72
        for line in lines:
            c.setFont("Helvetica", 11)
            c.drawString(72, y, line)
            y -= 16
        if footer:
            c.setFont("Helvetica", 8)
            c.drawString(72, 40, footer)
            c.drawString(400, 40, f"Page {n} of {len(pages)}")
        c.showPage()
    c.save()
    return buf.getvalue()


def blank_pdf(pages: int = 2) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for _ in range(pages):
        c.rect(72, 72, 200, 200)  # an "image" with no text layer
        c.showPage()
    c.save()
    return buf.getvalue()
