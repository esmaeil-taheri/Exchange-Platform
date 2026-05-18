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
from apps.core.exceptions.inquiry_exceptions import KycInquiryFailed

import uuid
import os

from apps.core.utils.logger import get_logger

logger = get_logger(__name__)


class KycService:

    inquiry_service = Inquiry_Service()

    @staticmethod
    def get_customer_identity_inquiry(
        *, user: CustomUser, national_id: str,
        first_name: str, last_name: str, birthday_date: str
    ) -> dict:

        setting = get_site_settings()
        if not setting.check_mobile_ownership:
            logger.warning(f"KYC inquiry blocked — feature disabled | user_id={user.id}")
            raise ActionDisabled('در حال حاضر امکان استعلام وجود ندارد')

        customer = Customer.objects.select_related("kyc").get(user_id=user.id)
        kyc = customer.kyc

        logger.info(
            f"KYC identity inquiry started | user_id={user.id} "
            f"national_id={national_id[:3]}****{national_id[-2:]} kyc_status={kyc.status}"
        )

        if customer.status == Customer.CUSTOMERSTATUS[2][0] or kyc.status not in ['not_started', 'shahkar_verified']:
            logger.warning(
                f"KYC inquiry rejected — already verified | user_id={user.id} kyc_status={kyc.status}"
            )
            raise CustomerAlreadyVerified('کاربر قبلا احراز هویت شده')

        if not kyc.shahkar_check:
            logger.info(f"Shahkar check initiated | user_id={user.id}")
            shahkar_result = KycService.inquiry_service.check_shahkar(
                national_id=national_id,
                phone_number=customer.user.phone_number
            )

            if not shahkar_result:
                logger.warning(
                    f"Shahkar check FAILED — phone/national_id mismatch | user_id={user.id}"
                )
                raise KycInquiryFailed("شماره موبایل با کد ملی مطابقت ندارد")

            with transaction.atomic():
                kyc.shahkar_check = True
                kyc.status = Kyc.Status.SHAHKAR_VERIFIED
                kyc.save(update_fields=['shahkar_check', 'status'])

            logger.info(f"Shahkar check PASSED | user_id={user.id} → status=shahkar_verified")

        logger.info(f"Identity inquiry initiated | user_id={user.id}")
        identity_data = KycService.inquiry_service.check_identity(
            national_id=national_id,
            birthday=birthday_date
        )

        if not identity_data:
            logger.warning(f"Identity inquiry FAILED — no data returned | user_id={user.id}")
            raise KycInquiryFailed("اطلاعات هویتی نادرست است")

        data = identity_data['data']

        if not data['isAlive']:
            logger.warning(
                f"Identity inquiry — user marked as deceased | user_id={user.id}"
            )
            customer.status = Customer.CUSTOMERSTATUS[1][0]
            customer.save(update_fields=['status'])
            raise KycInquiryFailed("RIP")

        with transaction.atomic():
            kyc.status = Kyc.Status.PENDING_UPLOAD
            kyc.save(update_fields=['status'])

            user.first_name = data['firstName']
            user.last_name = data['lastName']
            user.save(update_fields=['first_name', 'last_name'])

            customer.gender = data['gender'].lower()
            customer.father_name = data['fatherName']
            customer.birth_date = birthday_date
            customer.save(update_fields=['gender', 'father_name', 'birth_date'])

        logger.info(
            f"KYC identity inquiry COMPLETED | user_id={user.id} → status=pending_upload"
        )

        return {'message': 'احراز هویت با موفقیت انجام شد'}

    @staticmethod
    def _generate_object_name(user, file):
        ext = os.path.splitext(file.name)[1].lower()  # .jpg .png

        return f"customer_{user.id}/national_card/{uuid.uuid4()}{ext}"

    @staticmethod
    @transaction.atomic
    def submit_customer_kyc_document(*, user, doc):

        customer = user.customer_profile
        kyc = customer.kyc
        kyc_statuses = [Kyc.Status.PENDING_REVIEW, Kyc.Status.APPROVED]

        logger.info(
            f"KYC document upload initiated | user_id={user.id} "
            f"kyc_status={kyc.status} file={doc.name} size={doc.size}b"
        )

        if kyc.status in kyc_statuses:
            logger.warning(
                f"KYC document upload rejected — already submitted | user_id={user.id} kyc_status={kyc.status}"
            )
            raise CustomerAlreadyUploadedDoc('مدرک هویتی قبلا ثبت شده')

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

        kyc.status = Kyc.Status.PENDING_REVIEW
        kyc.submitted_at = timezone.now()

        document = KycDocument.objects.create(
            kyc=kyc,
            doc_type=KycDocument.Type.NATIONAL_CARD,
            image_url=doc_url
        )
        document.save()
        kyc.save(update_fields=["status", "submitted_at"])

        logger.info(
            f"KYC document uploaded | user_id={user.id} "
            f"doc_id={document.id} → status=pending_review"
        )

        return {"message": "مدرک هویتی با موفقیت آپلود شد و در انتظار بررسی است"}
