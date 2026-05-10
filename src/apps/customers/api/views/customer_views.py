from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from apps.customers.api.serializers.customer_serailizers import (
    CustomerIdentityInquiryResponseSerializer, CustomerIdentityInquirySerializer, 
    CustomerKycStatusResponseSerializer, CustomerProfileResponseSerializer
)
from apps.customers.selectors.customer_selectors import CustomerSelector
from apps.core.exceptions.open_api import ErrorSerializer
from apps.customers.api.serializers.kyc_doc_serializers import CustomerKycUploadResponseSerializer, CustomerKycUploadSerializer
from apps.customers.api.permissions.customer_permisions import CanUploadKycDocument


class GetCustomerProfile(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get customer's profile",
        tags=['Customers'],
        request=None,
        description="Get customer's profile information such as first name, last name, phone number and national id.",
        responses={
            200: OpenApiResponse(
                response=CustomerProfileResponseSerializer,
                description="Customer profile information retrieved successfully.",
                examples=[
                    OpenApiExample(
                        name="Successful Response Example",
                        value={
                            "message": "Success",
                            "detail": {
                                "first_name": "علی",
                                "last_name": "رضایی",
                                "father_name": "حسین",
                                "gender": "مرد",
                                "phone_number": "09123456789",
                                "national_id": "1234567890",
                                "birthday": "1370/01/01",
                                "is_authenticated": True
                            }
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
                        value={"detail": "Inquiry is currently disabled."}
                    )
                ]
            )
        }
    )

    def get(self, request, *args, **kwargs):
        data = CustomerSelector.get_customer_profile(user=request.user)
        serializer = CustomerProfileResponseSerializer(data)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class GetCustomerKycStatus(APIView):
    
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get user's kyc status",
        tags=['Customers'],
        request=None,
        responses={
            200: OpenApiResponse(
                response=CustomerKycStatusResponseSerializer,
                description="KYC status retrieved successfully.",
                examples=[
                    OpenApiExample(
                        name="Successful Response Example",
                        value={
                            "message": "Success",
                            "detail": {
                                "kyc_level": "verified",
                                "is_authenticated": True
                            }
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
                        value={"detail": "Inquiry is currently disabled."}
                    )
                ]
            )
        }
    )

    def get(self, request, *args, **kwargs):
        data = CustomerSelector.get_kyc_status(user=request.user)
        serilaizer = CustomerKycStatusResponseSerializer(data)
        return Response(
            serilaizer.data,
            status=status.HTTP_200_OK
        )


class CustomerIdentityInquiryApiView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Inquiry customer identity",
        tags=['Customers'],
        request=CustomerIdentityInquirySerializer,
        description="Inquiry customer's phone number and identity",
        responses={
            200: OpenApiResponse(
                response=CustomerIdentityInquiryResponseSerializer,

                examples=[
                    OpenApiExample(
                        name="Action was Successfull",
                        value={
                            "message": "inquiry was succesfull"
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
                        value={"detail": "Inquiry is currently disabled."}
                    )
                ]
            )
        }
    )

    def post(self, request, *args, **kwargs):
        serializer = CustomerIdentityInquirySerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        serializer = CustomerIdentityInquiryResponseSerializer(data)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
    

class CustomerKycUploadDocApiView(APIView):
    permission_classes = [CanUploadKycDocument, IsAuthenticated]

    @extend_schema(
        summary="Upload national card image for Kyc",
        tags=['Customers'],
        description=(
            "In this level user will upload national card image and wait for review"
        ),
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "national_card_image": {
                        "type": "string",
                        "format": "binary",
                        "description": "Natinoal Card Image (jpeg or png)"
                    }
                },
                "required": ["national_card_image"]
            }
        },
        responses={
            200: OpenApiResponse(
                response=CustomerKycUploadResponseSerializer,
                description="The document successlly uploaded and waiting for review.",
                examples=[
                    OpenApiExample(
                        "Successful Upload Example",
                        value={"detail": "The document successlly uploaded and waiting for review."}
                    )
                ]
            ),
        }
    )

    def post(self, request, *args, **kwargs):
        serializer = CustomerKycUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        data = serializer.save()

        serializer = CustomerKycUploadResponseSerializer(data)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )