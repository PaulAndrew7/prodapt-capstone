"""Digital-PDF text extraction (pypdf). Scans have no text layer and are rejected with an
actionable error until OCR (F27) exists; nothing is silently indexed as empty."""

import io
from dataclasses import dataclass, field

from pypdf import PdfReader
from pypdf.errors import PdfReadError

PDF_SIGNATURE = b"%PDF-"
MIN_PAGE_CHARS = 20


class IngestionError(Exception):
    """A document cannot be ingested. `category` is stable and safe to show to admins."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


@dataclass
class PageText:
    index: int
    label: str | None
    raw_text: str
    warnings: list[str] = field(default_factory=list)


def extract_pages(data: bytes, *, max_pages: int) -> list[PageText]:
    if not data.startswith(PDF_SIGNATURE):
        raise IngestionError("not_pdf", "The file is not a PDF (missing %PDF- signature).")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise IngestionError("encrypted_pdf", "The PDF is encrypted; upload an unlocked copy.")
        count = len(reader.pages)
        if count > max_pages:
            raise IngestionError(
                "too_many_pages", f"The PDF has {count} pages; the limit is {max_pages}."
            )
        labels = list(reader.page_labels) if count else []
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            warnings = []
            if len(text.strip()) < MIN_PAGE_CHARS:
                warnings.append(
                    f"Page {i + 1} has no extractable text; it may be a scan or an image."
                )
            label = labels[i] if i < len(labels) and labels[i] != str(i + 1) else None
            pages.append(PageText(i, label, text, warnings))
    except IngestionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise IngestionError("corrupt_pdf", f"The PDF could not be read: {exc}") from exc
    if not pages:
        raise IngestionError("empty_pdf", "The PDF has no pages.")
    if all(p.warnings for p in pages):
        raise IngestionError(
            "no_text_layer",
            "No page has extractable text. Scanned documents need OCR, which is not supported "
            "yet; upload a digital PDF.",
        )
    return pages
