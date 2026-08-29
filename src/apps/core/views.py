from django.db import connection
from django.core.cache import caches
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse


class HealthCheckView(APIView):
    """
    Health check endpoint for container orchestrators, load balancers, and monitoring.
    Verifies database and redis connectivity.
    """
    permission_classes = []
    authentication_classes = []

    @extend_schema(
        summary="Health Check",
        tags=["Health"],
        description="Returns system health status including database and cache connectivity.",
        responses={
            200: OpenApiResponse(description="System is healthy"),
            503: OpenApiResponse(description="System is unhealthy"),
        }
    )
    def get(self, request, *args, **kwargs):
        health_status = {
            "status": "healthy",
            "database": "unknown",
            "redis": "unknown",
        }

        # Check Database
        try:
            connection.ensure_connection()
            health_status["database"] = "ok"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"

        # Check Redis Cache
        try:
            cache = caches["default"]
            cache.set("health_check_ping", "pong", timeout=5)
            if cache.get("health_check_ping") == "pong":
                health_status["redis"] = "ok"
            else:
                health_status["redis"] = "error: cache mismatch"
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["redis"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"

        http_status = (
            status.HTTP_200_OK
            if health_status["status"] == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(health_status, status=http_status)
