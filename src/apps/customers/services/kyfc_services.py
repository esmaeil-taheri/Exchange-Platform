from django.db import transaction

from apps.customers.models.customer import Customer
from apps.customers.models.kyc import Kyc
from apps.core.services.inquiry.neginhub import Inquiry_Service
from apps.accounts.models.user import CustomUser
from apps.customers.exceptions.customer_exceptions import CustomerAlreadyVerified
from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.core.exceptions.base import ActionDisabled


class KycSerivce:

    inquiry_service = Inquiry_Service()

    @staticmethod
    def get_customer_identity_inquiry(
        *, user: CustomUser, national_id: str, 
        first_name: str, last_name: str, birthday_date: str
    ):
        setting = get_site_settings()
        if not setting.check_mobile_ownership:
            raise ActionDisabled('در حال حاضر امکان استعلام وجود ندارد')

        customer = Customer.objects.get(user_id=user.id)

        kyc = Kyc.objects.get(customer_id=customer.id)
        if kyc.government_verified:
            raise CustomerAlreadyVerified('کاربر قبلا احراز هویت شده')

        shahkar_result = KycSerivce.inquiry_service.check_shahkar(
            national_id=national_id,
            phone_number=customer.user.phone_number
        )

        # identity_result = KycSerivce.inquiry_service.check_identity(
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
