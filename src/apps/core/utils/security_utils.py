import ipaddress
import pyotp


def get_client_ip(request):
    # returns client ip address
    ip = (
        request.META.get('HTTP_X_REAL_IP')
        or (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[-1].strip()
        or request.META.get('REMOTE_ADDR', '')
    )
    try:
        return str(ipaddress.ip_address(ip.strip()))
    except ValueError:
        return '0.0.0.0' 


def generate_totp_secret():
    return pyotp.random_base32()


def get_totp_uri(secret, identifier, issuer="EsiGold"):
    return pyotp.TOTP(secret).provisioning_uri(
        name=identifier,
        issuer_name=issuer
    )


def verify_totp(secret, code):
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
