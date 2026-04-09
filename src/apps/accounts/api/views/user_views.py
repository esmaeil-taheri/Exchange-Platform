from django.http import Http404

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from apps.accounts.api.serializers.user_serializers import RegisterSerializer, UserDetailSerializer
from apps.accounts.selectors.user_selectors import UserSelector
from apps.accounts.exceptions.user_exceptions import RegistrationDisabled, UsernameAlreadyExists
from apps.core.exceptions.open_api import ErrorSerializer


class RegisterApiView(APIView):
    """Handle user registration."""

    @extend_schema(
        tags=['Accounts'],
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=UserDetailSerializer,
                description="User registered successfully.",
                examples=[
                    OpenApiExample(
                        name="Successful Register",
                        value={
                            "id": 1,
                            "username": "test",
                            "email": "test@email.com"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="RegistrationDisabled",
                        value={"detail": "Registration is currently disabled."}
                    )
                ]
            )
        }
    )

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            serializer.to_representation(user), 
            status=status.HTTP_201_CREATED
        )
        


class ProfileApiView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Accounts'],
        responses={
            200: OpenApiResponse(
                response=UserDetailSerializer,
                description="User Retrieved successfully.",
                examples=[
                    OpenApiExample(
                        name="Successful Retrieve",
                        value={
                            "id": 1,
                            "username": "test",
                            "email": "test@email.com"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="Not Authenticated",
                        value={"detail": "Authentication credentials were not provided."}
                    )
                ]
            )
        }
    )

    def get(self, request, *args, **kwargs):
        user = UserSelector.get_user_by_id(user_id=request.user.id)
        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
