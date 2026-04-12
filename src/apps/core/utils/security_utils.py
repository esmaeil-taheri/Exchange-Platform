import pyotp
import urllib

def get_client_ip(request):
    # returns client ip address

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for: 
        ip = x_forwarded_for.split(',')[0]

    else: 
        ip = request.META.get('REMOTE_ADDR')

    ip = urllib.parse.unquote(ip)
    
    return ip 


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
