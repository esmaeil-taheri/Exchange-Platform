from apps.accounts.models.user import CustomUser
from apps.customers.models.customer import Customer
from apps.accounts.models.user import CustomUser

class CustomerSelector:
    @staticmethod
    def get_kyc_status(*, user: CustomUser) -> dict:

        customer = Customer.objects.select_related('kyc').get(user_id=user.id)

        return {
            "message": 'Success',
            "detail": {
                "kyc_level": customer.kyc.status,
                "is_authenticated": True if customer.status == Customer.CUSTOMERSTATUS[2][0] else False
            }
        }

    @staticmethod
    def get_customer_profile(*, user: CustomUser) -> dict:
        user = CustomUser.objects.select_related('customer_profile').get(id=user.id)

        return {
            "message": 'Success',
            "detail": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "father_name": user.customer_profile.father_name,
                "gender": user.customer_profile.gender,
                "phone_number": user.phone_number,
                "national_id": user.national_id,
                "birthday": user.customer_profile.birth_date,
                "is_authenticated": True if user.customer_profile.status == Customer.CUSTOMERSTATUS[2][0] else False
            }
        }
