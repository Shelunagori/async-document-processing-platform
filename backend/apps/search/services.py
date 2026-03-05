from __future__ import annotations

import hashlib
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from apps.documents.models import Document, DocumentStatus


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
            )
            .only("id", "original_filename", "summary", "extracted_text", "metadata", "processed_at")
            .order_by("-processed_at")
        )

        results = []
        for document in queryset:
            results.append(
                {
                    "id": document.id,
                    "original_filename": document.original_filename,
                    "summary": document.summary,
                    "snippet": cls._build_snippet(document.summary, document.extracted_text, normalized),
                    "metadata": document.metadata,
                    "processed_at": document.processed_at,
                }
            )

        cache.set(cache_key, results, timeout=settings.SEARCH_CACHE_TIMEOUT)
        return results, False
