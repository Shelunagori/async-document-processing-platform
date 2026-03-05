from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


class UploadRateLimitMiddleware:
    """Simple cache-backed rate limiter for upload endpoints."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path in {
            "/api/documents/upload/",
            "/api/documents/upload-batch/",
        }:
            identifier = self._get_client_identifier(request)
            key = f"upload-rate:{identifier}"
            limit = settings.UPLOADS_PER_MINUTE
            window_seconds = 60

            if cache.add(key, 1, timeout=window_seconds):
                current_count = 1
            else:
                try:
                    current_count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=window_seconds)
                    current_count = 1

            if current_count > limit:
                return JsonResponse(
                    {
                        "detail": "Upload rate limit exceeded. Please retry in a minute.",
                    },
                    status=429,
                )

        return self.get_response(request)

    @staticmethod
    def _get_client_identifier(request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
