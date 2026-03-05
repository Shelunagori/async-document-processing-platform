from django.urls import path

from apps.search.views import DocumentSearchView

urlpatterns = [
    path("documents/", DocumentSearchView.as_view(), name="document-search"),
]
