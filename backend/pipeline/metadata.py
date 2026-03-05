from __future__ import annotations


class MetadataStage:
    @staticmethod
    def build(
        extracted_text: str,
        summary: str,
        classification: str,
        layout: dict,
        chunks: list[str],
        stage_durations: dict,
    ) -> dict:
        return {
            "classification": classification,
            "layout": layout,
            "word_count": len(extracted_text.split()),
            "character_count": len(extracted_text),
            "summary_length": len(summary),
            "chunk_count": len(chunks),
            "pipeline_stages": stage_durations,
        }
