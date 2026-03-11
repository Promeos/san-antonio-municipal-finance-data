from __future__ import annotations

from collections.abc import Iterator
import shutil
import subprocess

from pdfminer.pdfpage import PDFPage
from pdfplumber.page import Page


def iter_pdf_pages(pdf) -> Iterator[tuple[int, Page]]:
    """Yield 0-based page indexes and pdfplumber Page objects lazily."""
    doctop = 0
    for index, page_obj in enumerate(PDFPage.create_pages(pdf.doc)):
        page = Page(pdf, page_obj, page_number=index + 1, initial_doctop=doctop)
        doctop += page.height
        yield index, page


def load_pages(pdf, indexes: list[int]) -> list[Page]:
    """Load only the requested 0-based pages without building pdf.pages eagerly."""
    targets = set(indexes)
    if not targets:
        return []

    page_map: dict[int, Page] = {}
    for index, page in iter_pdf_pages(pdf):
        if index in targets:
            page_map[index] = page
            if len(page_map) == len(targets):
                break

    return [page_map[index] for index in indexes if index in page_map]


def get_page_texts(pdf) -> list[str]:
    """Return page texts, preferring a cached pdftotext extraction when available."""
    if hasattr(pdf, "_cached_page_texts"):
        return pdf._cached_page_texts

    stream = getattr(pdf, "stream", None)
    path = getattr(stream, "name", None)
    pdftotext = shutil.which("pdftotext")
    if path and pdftotext:
        try:
            result = subprocess.run(
                [pdftotext, "-layout", path, "-"],
                check=True,
                capture_output=True,
                text=True,
            )
            pages = result.stdout.split("\f")
            if pages and not pages[-1].strip():
                pages.pop()
            pdf._cached_page_texts = pages
            return pages
        except (OSError, subprocess.SubprocessError):
            pass

    pages = [(page.extract_text() or "") for _, page in iter_pdf_pages(pdf)]
    pdf._cached_page_texts = pages
    return pages


def iter_page_texts(pdf) -> Iterator[tuple[int, str]]:
    """Yield 0-based page indexes and text, using the cached fast path when possible."""
    for index, text in enumerate(get_page_texts(pdf)):
        yield index, text
