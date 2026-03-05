from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor


class IndexingStage:
    @staticmethod
    def _embed_text(text: str, dimensions: int = 16) -> list[float]:
        base_hash = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for i in range(dimensions):
            value = base_hash[i] / 255.0
            values.append(round(value, 6))
        return values

    @classmethod
    def build_chunk_records(cls, chunks: list[str], max_workers: int = 4) -> list[dict]:
        if not chunks:
            return []

        worker_count = max(1, min(max_workers, len(chunks)))

        def build_record(index: int, chunk_text: str) -> dict:
            return {
                "chunk_index": index,
                "content": chunk_text,
                "embedding": cls._embed_text(chunk_text),
                "metadata": {
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                },
            }

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            records = list(executor.map(lambda item: build_record(item[0], item[1]), enumerate(chunks)))

        return records
