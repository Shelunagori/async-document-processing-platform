from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IngestionContext:
    document_id: str
    filename: str
    extension: str
    content_type: str


class IngestionStage:
    @staticmethod
    def prepare(document) -> IngestionContext:
        extension = Path(document.original_filename).suffix.lower()
        return IngestionContext(
            document_id=str(document.id),
            filename=document.original_filename,
            extension=extension,
            content_type=document.content_type,
        )
