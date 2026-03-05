from django.urls import path

from apps.processing.views import ProcessingTaskDetailView

urlpatterns = [
    path("tasks/<uuid:id>/", ProcessingTaskDetailView.as_view(), name="processing-task-detail"),
]
