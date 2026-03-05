from django.urls import path

from apps.documents.views import DocumentDetailView, DocumentListView, DocumentUploadView

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("<uuid:id>/", DocumentDetailView.as_view(), name="document-detail"),
]
