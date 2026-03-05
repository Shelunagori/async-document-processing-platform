from __future__ import annotations

import re

from services.extraction import DocumentExtractionService


class ParsingStage:
    @staticmethod
    def classify(filename: str, extension: str, content_type: str) -> str:
        lowered = filename.lower()
        if "invoice" in lowered or "receipt" in lowered:
            return "FINANCIAL_DOCUMENT"
        if "contract" in lowered or "agreement" in lowered:
            return "LEGAL_DOCUMENT"
        if extension == ".pdf" and "presentation" in lowered:
            return "PRESENTATION"
        if extension == ".docx":
            return "WORD_PROCESSING_DOCUMENT"
        if extension == ".pdf":
            return "PDF_DOCUMENT"
        if content_type.startswith("application/"):
            return "APPLICATION_DOCUMENT"
        return "UNKNOWN_DOCUMENT"

    @staticmethod
    def extract_text(file_path: str, extension: str) -> str:
        return DocumentExtractionService.extract_text(file_path, extension)

    @staticmethod
    def detect_layout(text: str) -> dict:
        lines = [line for line in text.splitlines() if line.strip()]
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0.0
        return {
            "line_count": len(lines),
            "paragraph_count": len(paragraphs),
            "avg_line_length": round(avg_line_length, 2),
            "empty_text": not bool(text.strip()),
        }
