from __future__ import annotations


class ChunkingStage:
    @staticmethod
    def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        normalized = " ".join((text or "").split())
        if not normalized:
            return []

        if chunk_size <= 0:
            return [normalized]

        safe_overlap = max(0, min(overlap, max(0, chunk_size - 1)))

        chunks: list[str] = []
        start = 0
        text_length = len(normalized)

        while start < text_length:
            end = min(text_length, start + chunk_size)
            boundary = normalized.rfind(" ", start, end)
            if boundary > start + int(chunk_size * 0.5):
                end = boundary

            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            start = end - safe_overlap
            if start < 0:
                start = 0

        return chunks
