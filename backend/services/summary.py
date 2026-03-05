from __future__ import annotations

import re


class DocumentSummaryService:
    @staticmethod
    def generate_summary(text: str, max_sentences: int = 3, max_chars: int = 900) -> str:
        normalized = re.sub(r"\s+", " ", text or "").strip()
        if not normalized:
            return ""

        sentences = re.split(r"(?<=[.!?])\s+", normalized)
        summary = " ".join(sentences[:max_sentences]).strip()

        if len(summary) <= max_chars:
            return summary

        trimmed = summary[:max_chars].rsplit(" ", 1)[0]
        return f"{trimmed}..."
