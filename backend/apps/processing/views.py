from rest_framework import generics

from apps.processing.models import ProcessingTask
from apps.processing.serializers import ProcessingTaskSerializer


class ProcessingTaskDetailView(generics.RetrieveAPIView):
    serializer_class = ProcessingTaskSerializer
    lookup_field = "id"

    def get_queryset(self):
        return ProcessingTask.objects.filter(document__owner=self.request.user).select_related("document")
