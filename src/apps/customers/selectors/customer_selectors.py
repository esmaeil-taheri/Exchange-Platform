from apps.accounts.models.user import CustomUser
from apps.customers.models.customer import Customer


class CustomerSelector:
    @staticmethod
    def get_kyc_status(*, user: CustomUser) -> dict:

        customer = Customer.objects.select_related('kyc').get(user_id=user.id)

        return {
            "message": 'اطلاعات با موفقیت دریافت شد',
            "detail": {
                "kyc_level": customer.kyc.status,
                "is_verified": True if customer.status == Customer.CUSTOMERSTATUS[2][0] else False
            }
        }
