from django.conf import settings
from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.processing.models import ProcessingTask
from apps.processing.serializers import ProcessingTaskSerializer
from rest_framework.views import APIView


class ProcessingTaskDetailView(generics.RetrieveAPIView):
    serializer_class = ProcessingTaskSerializer
    lookup_field = "id"

    def get_queryset(self):
        return ProcessingTask.objects.filter(document__owner=self.request.user).select_related("document")


class PrometheusMetricsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        configured_token = settings.METRICS_AUTH_TOKEN
        if configured_token and request.headers.get("X-Metrics-Token") != configured_token:
            return Response({"detail": "Unauthorized metrics access."}, status=status.HTTP_401_UNAUTHORIZED)
        return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
