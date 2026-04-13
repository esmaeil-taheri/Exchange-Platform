from django.db import transaction
from django.utils import timezone

from apps.customers.models.customer import Customer
from apps.customers.models.kyc import Kyc
from apps.customers.models.kyc_document import KycDocument
from apps.core.services.inquiry.neginhub import Inquiry_Service
from apps.accounts.models.user import CustomUser
from apps.customers.exceptions.customer_exceptions import CustomerAlreadyUploadedDoc, CustomerAlreadyVerified
from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.core.exceptions.base import ActionDisabled
from apps.core.services.storage.minio_client import MinioClient

import uuid
import os



class KycService:

    inquiry_service = Inquiry_Service()

    @staticmethod
    def get_customer_identity_inquiry(
        *, user: CustomUser, national_id: str, 
        first_name: str, last_name: str, birthday_date: str
    ) -> dict:
        setting = get_site_settings()
        if not setting.check_mobile_ownership:
            raise ActionDisabled('در حال حاضر امکان استعلام وجود ندارد')

        customer = Customer.objects.get(user_id=user.id)

        kyc = Kyc.objects.get(customer_id=customer.id)
        if kyc.government_verified:
            raise CustomerAlreadyVerified('کاربر قبلا احراز هویت شده')

        shahkar_result = KycService.inquiry_service.check_shahkar(
            national_id=national_id,
            phone_number=customer.user.phone_number
        )

        # identity_result = KycService.inquiry_service.check_identity(
        #     national_id=national_id,
        #     birthday=birthday_date
        # )

        if shahkar_result:
            with transaction.atomic():

                kyc.government_verified = True
                kyc.status = Kyc.Status.GOV_VERIFIED
                kyc.save(update_fields=['government_verified', 'status'])

                user.first_name = first_name
                user.last_name = last_name
                user.save(update_fields=['first_name', 'last_name'])

                customer.birth_date = birthday_date
                customer.save(update_fields=['birth_date'])

                return {
                    'message': 'احراز هویت با موفقیت انجام شد'
                }
                
        else:
            return {
                'message': 'اطلاعات هویتی نادرست است'
            }
        
    @staticmethod
    def _generate_object_name(user, file):
        ext = os.path.splitext(file.name)[1].lower()  # .jpg .png

        return f"customer_{user.id}/national_card/{uuid.uuid4()}{ext}"

    @staticmethod
    @transaction.atomic
    def submit_customer_kyc_document(*, user, doc):

        customer = user.customer_profile

        # 2. get related kyc
        kyc = customer.kyc
        kyc_statuses = [Kyc.Status.DOCUMENT_UPLOADED, Kyc.Status.APPROVED]
        if kyc.status in kyc_statuses:
            raise CustomerAlreadyUploadedDoc('احراز هویت قبلا انجام شده')

        # 3. generate storage path
        object_name = KycService._generate_object_name(user, doc)

        minio = MinioClient(bucket_name='kyc-documents')
        minio.upload_file(
            file_obj=doc,
            object_name=object_name,
            content_type=doc.content_type
        )
        doc_url = minio.generate_url(
            object_name=object_name
        )

        kyc.status = Kyc.Status.DOCUMENT_UPLOADED
        kyc.submitted_at = timezone.now()
        
        document = KycDocument.objects.create(
            kyc=kyc,
            doc_type=KycDocument.Type.NATIONAL_CARD,
            image_url=doc_url
        )

        document.save()

        kyc.save(update_fields=["status", "submitted_at"])

        return {
            "message": "مدرک با موفقیت آپلود شد و در انتظار بررسی است"
        }