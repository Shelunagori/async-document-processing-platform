from __future__ import annotations

import hashlib
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q

from apps.documents.models import Document, DocumentChunk, DocumentStatus


class DocumentSearchService:
    @staticmethod
    def _cache_key(user_id: int, query: str) -> str:
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        return f"doc-search:{user_id}:{digest}"

    @staticmethod
    def _build_snippet(summary: str, extracted_text: str, query: str) -> str:
        source = summary or extracted_text
        if not source:
            return ""
        lower_source = source.lower()
        lower_query = query.lower()
        idx = lower_source.find(lower_query)
        if idx == -1:
            return source[:280]

        start = max(0, idx - 90)
        end = min(len(source), idx + len(query) + 90)
        snippet = source[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(source):
            snippet = snippet + "..."
        return snippet

    @staticmethod
    def _build_chunk_snippet(chunk_text: str, query: str) -> str:
        if not chunk_text:
            return ""
        lower_source = chunk_text.lower()
        lower_query = query.lower()
        idx = lower_source.find(lower_query)
        if idx == -1:
            return chunk_text[:280]
        start = max(0, idx - 90)
        end = min(len(chunk_text), idx + len(query) + 90)
        snippet = chunk_text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(chunk_text):
            snippet = snippet + "..."
        return snippet

    @classmethod
    def search(cls, user, query: str) -> tuple[list[dict[str, Any]], bool]:
        normalized = query.strip()
        cache_key = cls._cache_key(user.id, normalized)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached, True

        queryset = (
            Document.objects.filter(owner=user, status=DocumentStatus.PROCESSED)
            .filter(
                Q(original_filename__icontains=normalized)
                | Q(summary__icontains=normalized)
                | Q(extracted_text__icontains=normalized)
                | Q(chunks__content__icontains=normalized)
            )
            .annotate(chunk_count=Count("chunks"))
            .only("id", "original_filename", "summary", "extracted_text", "metadata", "processed_at")
            .distinct()
            .order_by("-processed_at")
        )

        matching_chunks = (
            DocumentChunk.objects.filter(
                document__owner=user,
                document__status=DocumentStatus.PROCESSED,
                content__icontains=normalized,
            )
            .select_related("document")
            .only("document_id", "content", "chunk_index")
            .order_by("document_id", "chunk_index")
        )
        chunk_snippets: dict[Any, str] = {}
        for chunk in matching_chunks:
            if chunk.document_id in chunk_snippets:
                continue
            chunk_snippets[chunk.document_id] = cls._build_chunk_snippet(chunk.content, normalized)

        results = []
        for document in queryset:
            chunk_snippet = chunk_snippets.get(document.id)
            results.append(
                {
                    "id": document.id,
                    "original_filename": document.original_filename,
                    "summary": document.summary,
                    "snippet": chunk_snippet
                    or cls._build_snippet(document.summary, document.extracted_text, normalized),
                    "match_source": "chunk" if chunk_snippet else "document",
                    "chunk_count": getattr(document, "chunk_count", 0),
                    "metadata": document.metadata,
                    "processed_at": document.processed_at,
                }
            )

        cache.set(cache_key, results, timeout=settings.SEARCH_CACHE_TIMEOUT)
        return results, False
