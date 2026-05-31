from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # pymupdf


@dataclass
class ParsedPdf:
    raw_text: str
    pages: list[str]
    metadata: dict = field(default_factory=dict)


class BasePdfParser(ABC):
    """Abstract PDF parser."""

    @abstractmethod
    def parse(self, path: Path) -> ParsedPdf:
        ...


class PyMuPDFParser(BasePdfParser):
    """PDF parser using PyMuPDF (fitz). Default choice - pure C, no models."""

    def parse(self, path: Path) -> ParsedPdf:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        with fitz.open(path) as doc:
            if not doc.is_pdf:
                raise ValueError(f"File is not a PDF: {path}")
            pages: list[str] = []
            for page in doc:
                pages.append(page.get_text("text"))
            metadata = {
                "page_count": doc.page_count,
                "pdf_metadata": dict(doc.metadata or {}),
            }

        raw_text = "\n\n".join(pages)
        return ParsedPdf(raw_text=raw_text, pages=pages, metadata=metadata)
