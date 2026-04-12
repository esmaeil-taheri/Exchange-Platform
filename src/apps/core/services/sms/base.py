class BaseSmsProvider:
    def send_otp(self, code: str, phone_number: str):
        raise NotImplementedError

    def send_message(self, message: str, phone_number: str):
        raise NotImplementedError