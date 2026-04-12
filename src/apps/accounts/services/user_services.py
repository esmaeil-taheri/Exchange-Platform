import secrets
import string
import pyotp

from django.core.cache import caches
from django.http import request
from django.dispatch import Signal
from django.utils import timezone
from django.db import transaction

from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.accounts.exceptions.user_exceptions import (
    InvalidTwoFactorCode, OtpAlreadySent, FailedToSendOtp, InvalidOtp, 
    TwoFactorAlreadyDisabled, TwoFactorAlreadyEnabled
)
from apps.core.exceptions.base import ActionDisabled
from apps.core.services.sms.sms_ir import SmsIrProvider
from apps.core.utils.security_utils import get_client_ip, generate_totp_secret
from apps.accounts.selectors.user_selectors import UserSelector


user_registered = Signal()


# define cache client
otp_cache = caches['otp']


class UserService:

    otp_provider = SmsIrProvider()

    @staticmethod
    def login_register(*, phone_number: str) -> dict:
        settings = get_site_settings()

        user_exists = CustomUser.objects.filter(phone_number=phone_number).exists()

        otp_type = "login" if user_exists else "register"

        if user_exists and not settings.customer_login:
            raise ActionDisabled("در حال حاضر امکان ورود به حساب وجود ندارد.")

        if not user_exists and not settings.customer_register:
            raise ActionDisabled("در حال حاضر امکان ثبت نام وجود ندارد.")

        cache_key = f"{otp_type}:{phone_number}"

        if otp_cache.get(cache_key):
            raise OtpAlreadySent("کد یکبار مصرف قبلا ارسال شده.")

        otp = "".join(secrets.choice(string.digits) for _ in range(6))
        print(otp)

        otp_cache.set(cache_key, otp, timeout=120)

        provider_response = UserService.otp_provider.send_otp(otp, phone_number)

        if provider_response["code"] != 100:
            otp_cache.delete(cache_key)
            raise FailedToSendOtp("خطا در ارسال رمز یکبار مصرف. لطفا دقایقی دیگر مجددا تلاش کنید.")

        return {
            "message": "کد با موفقیت ارسال شد",
            "data": {
                "phone_number": phone_number[:4] + "*" * (len(phone_number) - 6) + phone_number[-2:]
            }
        }

    @staticmethod
    def login_register_verify(*, phone_number: str, code: str, request: request) -> dict:
        settings = get_site_settings()

        user = CustomUser.objects.filter(phone_number=phone_number).first()

        cache_key = f'login:{phone_number}' if user else f'register:{phone_number}'
        cached_otp = otp_cache.get(cache_key)

        if not cached_otp or cached_otp != code:
                raise InvalidOtp('کد وارد شده صحیح نیست')
        
        first_time_login = True if not user else False
        two_fa_enabled = True if user and user.is_2fa_enabled else False

        with transaction.atomic():
            if not user:
                user = CustomUser.objects.create(
                    username=f'user-{phone_number}',
                    phone_number=phone_number,
                    last_ip_address=get_client_ip(request),
                    totp_secret=generate_totp_secret()
                )

                if settings.send_welcome_sms:
                    user_registered.send(sender=CustomUser, user=user)
            else:
                user.last_login = timezone.now()
                user.last_ip_address = get_client_ip(request)
                user.save(update_fields=['last_login', 'last_ip_address'])

            refresh = RefreshToken.for_user(user)
            
            otp_cache.delete(cache_key)

        return {
            'message': 'ورود با موفقیت انجام شد',
            'detail': {
                'refresh': str(refresh),
                'first_time_login': first_time_login,
                'access': str(refresh.access_token),
                'two_fa_enabled': two_fa_enabled
            }
        }
    
    @staticmethod
    def send_two_factor_otp(*, phone_number: str) -> dict:
        cache_key = f'2fa:{phone_number}'

        otp = "".join(secrets.choice(string.digits) for _ in range(6))
        
        if otp_cache.get(cache_key):
            raise OtpAlreadySent("کد یکبار مصرف قبلا ارسال شده.")

        otp_cache.set(cache_key, otp, timeout=120)
        print(otp)

        return {
            "message": "کد با موفقیت ارسال شد",
            "data": {
                "phone_number": phone_number[:4] + "*" * (len(phone_number) - 6) + phone_number[-2:]
            }
        }
    
    @staticmethod
    def setup_2fa(*, request: request):

        if request.user.is_2fa_enabled:
            raise TwoFactorAlreadyEnabled('تایید دو مرحله ای قبلا فعال شده')

        uri_data = UserSelector.get_user_2fa_uri(user_id=request.user.id)

        return uri_data

    @staticmethod
    @transaction.atomic
    def two_fa_change_status(*, user: CustomUser, code: str, is_2fa: bool, authenticator_code: str) -> dict:
        otp_cache = caches["otp"]
        cache_key = f"2fa:{user.phone_number}"

        stored_code = otp_cache.get(cache_key)

        if not stored_code:
            raise InvalidOtp('کد وارد شده صحیح نیست')

        if stored_code != code:
            raise InvalidOtp('کد وارد شده صحیح نیست')

        totp = pyotp.TOTP(user.totp_secret)

        if not totp.verify(authenticator_code):
            raise InvalidTwoFactorCode('کد دو مرحله ای صحیح نیست')

        if is_2fa:
            if user.is_2fa_enabled:
                raise TwoFactorAlreadyEnabled('تایید دو مرحله ای در حال حاضر فعال است')
            user.is_2fa_enabled = True
        else:
            if not user.is_2fa_enabled:
                raise TwoFactorAlreadyDisabled('تایید دو مرحله ای در حال حاضر غیر فعال است')
            user.is_2fa_enabled = False

        user.save(update_fields=["is_2fa_enabled"])

        otp_cache.delete(cache_key)

        return {
            'message': 'وضعیت با موفقیت تغییر یافت', 
        }