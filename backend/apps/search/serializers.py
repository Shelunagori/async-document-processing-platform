from rest_framework import serializers


class SearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    original_filename = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    snippet = serializers.CharField(allow_blank=True)
    match_source = serializers.CharField(required=False, default="document")
    chunk_count = serializers.IntegerField(required=False, default=0)
    metadata = serializers.JSONField()
    processed_at = serializers.DateTimeField(allow_null=True)
