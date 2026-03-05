from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search.serializers import SearchResultSerializer
from apps.search.services import DocumentSearchService


class DocumentSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        results, cached = DocumentSearchService.search(request.user, query)
        serializer = SearchResultSerializer(results, many=True)
        return Response(
            {
                "query": query,
                "count": len(serializer.data),
                "cached": cached,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
