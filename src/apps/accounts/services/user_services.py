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
from apps.core.utils.logger import get_logger

logger = get_logger(__name__)

user_registered = Signal()
login_detected = Signal()

# define cache client
otp_cache = caches['otp']


class UserService:

    otp_provider = SmsIrProvider()

    @staticmethod
    def login_register(*, phone_number: str) -> dict:
        settings = get_site_settings()

        user_exists = CustomUser.objects.filter(phone_number=phone_number).exists()
        otp_type = "login" if user_exists else "register"

        logger.info(
            f"OTP request received | type={otp_type} phone={phone_number[:4]}****{phone_number[-2:]}"
        )

        if user_exists and not settings.customer_login:
            logger.warning(
                f"Login blocked — login disabled globally | phone={phone_number[:4]}****{phone_number[-2:]}"
            )
            raise ActionDisabled("در حال حاضر امکان ورود به حساب وجود ندارد.")

        if not user_exists and not settings.customer_register:
            logger.warning(
                f"Register blocked — registration disabled globally | phone={phone_number[:4]}****{phone_number[-2:]}"
            )
            raise ActionDisabled("در حال حاضر امکان ثبت نام وجود ندارد.")

        cache_key = f"{otp_type}:{phone_number}"

        if otp_cache.get(cache_key):
            logger.warning(
                f"OTP already active — rate limit triggered | type={otp_type} phone={phone_number[:4]}****{phone_number[-2:]}"
            )
            raise OtpAlreadySent("کد یکبار مصرف قبلا ارسال شده.")

        otp = "".join(secrets.choice(string.digits) for _ in range(6))
        otp_cache.set(cache_key, otp, timeout=120)

        provider_response = UserService.otp_provider.send_otp(otp, phone_number)

        if provider_response["code"] != 100:
            otp_cache.delete(cache_key)
            logger.error(
                f"SMS provider failed | type={otp_type} phone={phone_number[:4]}****{phone_number[-2:]} "
                f"provider_code={provider_response.get('code')}"
            )
            raise FailedToSendOtp("خطا در ارسال رمز یکبار مصرف. لطفا دقایقی دیگر مجددا تلاش کنید.")

        logger.info(
            f"OTP sent successfully | type={otp_type} phone={phone_number[:4]}****{phone_number[-2:]}"
        )

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
            logger.warning(
                f"Invalid OTP attempt | phone={phone_number[:4]}****{phone_number[-2:]} "
                f"ip={get_client_ip(request)}"
            )
            raise InvalidOtp('کد وارد شده صحیح نیست')

        first_time_login = not bool(user)
        two_fa_enabled = bool(user and user.is_2fa_enabled)

        with transaction.atomic():
            if not user:
                user = CustomUser.objects.create(
                    username=f'user-{phone_number}',
                    phone_number=phone_number,
                    last_ip_address=get_client_ip(request),
                    totp_secret=generate_totp_secret()
                )
                logger.info(
                    f"New user registered | user_id={user.id} "
                    f"phone={phone_number[:4]}****{phone_number[-2:]} ip={get_client_ip(request)}"
                )
                if settings.send_welcome_sms:
                    user_registered.send(sender=CustomUser, user=user)
            else:
                user.last_login = timezone.now()
                user.last_ip_address = get_client_ip(request)
                user.save(update_fields=['last_login', 'last_ip_address'])
                login_detected.send(sender=CustomUser, user=user)
                logger.info(
                    f"User logged in | user_id={user.id} "
                    f"phone={phone_number[:4]}****{phone_number[-2:]} ip={get_client_ip(request)} "
                    f"2fa={two_fa_enabled}"
                )

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

        if otp_cache.get(cache_key):
            logger.warning(
                f"2FA OTP already active — rate limit | phone={phone_number[:4]}****{phone_number[-2:]}"
            )
            raise OtpAlreadySent("کد یکبار مصرف قبلا ارسال شده.")

        otp = "".join(secrets.choice(string.digits) for _ in range(6))
        otp_cache.set(cache_key, otp, timeout=120)

        provider_response = UserService.otp_provider.send_otp(otp, phone_number)

        if provider_response["code"] != 100:
            otp_cache.delete(cache_key)
            logger.error(
                f"2FA OTP — SMS provider failed | phone={phone_number[:4]}****{phone_number[-2:]} "
                f"provider_code={provider_response.get('code')}"
            )
            raise FailedToSendOtp("خطا در ارسال رمز یکبار مصرف. لطفا دقایقی دیگر مجددا تلاش کنید.")

        logger.info(
            f"2FA OTP sent | phone={phone_number[:4]}****{phone_number[-2:]}"
        )

        return {
            "message": "کد با موفقیت ارسال شد",
            "data": {
                "phone_number": phone_number[:4] + "*" * (len(phone_number) - 6) + phone_number[-2:]
            }
        }

    @staticmethod
    def setup_2fa(*, request: request):
        if request.user.is_2fa_enabled:
            logger.warning(
                f"2FA setup rejected — already enabled | user_id={request.user.id}"
            )
            raise TwoFactorAlreadyEnabled('تایید دو مرحله ای قبلا فعال شده')

        logger.info(f"2FA setup URI requested | user_id={request.user.id}")
        uri_data = UserSelector.get_user_2fa_uri(user_id=request.user.id)
        return uri_data

    @staticmethod
    @transaction.atomic
    def two_fa_change_status(*, user: CustomUser, code: str, is_2fa: bool, authenticator_code: str) -> dict:
        otp_cache = caches["otp"]
        cache_key = f"2fa:{user.phone_number}"

        stored_code = otp_cache.get(cache_key)

        if not stored_code:
            logger.warning(f"2FA change failed — OTP expired | user_id={user.id}")
            raise InvalidOtp('کد وارد شده صحیح نیست')

        if stored_code != code:
            logger.warning(f"2FA change failed — invalid OTP | user_id={user.id}")
            raise InvalidOtp('کد وارد شده صحیح نیست')

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(authenticator_code):
            logger.warning(
                f"2FA change failed — invalid TOTP code | user_id={user.id}"
            )
            raise InvalidTwoFactorCode('کد دو مرحله ای صحیح نیست')

        if is_2fa:
            if user.is_2fa_enabled:
                raise TwoFactorAlreadyEnabled('تایید دو مرحله ای در حال حاضر فعال است')
            user.is_2fa_enabled = True
            logger.info(f"2FA enabled | user_id={user.id}")
        else:
            if not user.is_2fa_enabled:
                raise TwoFactorAlreadyDisabled('تایید دو مرحله ای در حال حاضر غیر فعال است')
            user.is_2fa_enabled = False
            logger.info(f"2FA disabled | user_id={user.id}")

        user.save(update_fields=["is_2fa_enabled"])
        otp_cache.delete(cache_key)

        return {'message': 'وضعیت با موفقیت تغییر یافت'}
