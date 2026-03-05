from rest_framework import serializers


class SearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    original_filename = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    snippet = serializers.CharField(allow_blank=True)
    metadata = serializers.JSONField()
    processed_at = serializers.DateTimeField(allow_null=True)
