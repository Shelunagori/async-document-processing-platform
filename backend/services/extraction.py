from __future__ import annotations

from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document as DocxDocument


class UnsupportedDocumentTypeError(ValueError):
    pass


class DocumentExtractionService:
    @staticmethod
    def extract_text(file_path: str, extension: str) -> str:
        ext = extension.lower()
        if ext == ".pdf":
            return DocumentExtractionService._extract_from_pdf(file_path)
        if ext == ".docx":
            return DocumentExtractionService._extract_from_docx(file_path)
        raise UnsupportedDocumentTypeError(f"Unsupported document type: {ext}")

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        with Path(file_path).open("rb") as pdf_file:
            reader = PdfReader(pdf_file)
            text_chunks = []
            for page in reader.pages:
                text_chunks.append(page.extract_text() or "")
        return "\n".join(text_chunks).strip()

    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        doc = DocxDocument(file_path)
        text_chunks = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
        return "\n".join(text_chunks).strip()
