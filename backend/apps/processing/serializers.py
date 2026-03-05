from celery.result import AsyncResult
from rest_framework import serializers

from apps.processing.models import ProcessingTask


class ProcessingTaskSerializer(serializers.ModelSerializer):
    celery_state = serializers.SerializerMethodField()

    class Meta:
        model = ProcessingTask
        fields = (
            "id",
            "document",
            "status",
            "celery_task_id",
            "celery_state",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )

    def get_celery_state(self, obj):
        if not obj.celery_task_id:
            return obj.status
        try:
            return AsyncResult(obj.celery_task_id).state
        except Exception:
            return obj.status
