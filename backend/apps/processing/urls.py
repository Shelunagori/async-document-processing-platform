from django.urls import path

from apps.processing.views import ProcessingTaskDetailView, PrometheusMetricsView

urlpatterns = [
    path("tasks/<uuid:id>/", ProcessingTaskDetailView.as_view(), name="processing-task-detail"),
    path("metrics/", PrometheusMetricsView.as_view(), name="processing-metrics"),
]
