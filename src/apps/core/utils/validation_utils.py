IRANIAN_BANKS = [
    {"card_no": 627381, "bank_name": "ansar", "bank_title": "بانک انصار"},
    {"card_no": 502938, "bank_name": "dey", "bank_title": "بانک دی"},
    {"card_no": 627412, "bank_name": "eghtesad_novin", "bank_title": "بانک اقتصادنوین"},
    {"card_no": 628157, "bank_name": "etebari_tosee", "bank_title": "موسسه اعتباری توسعه"},
    {"card_no": 505416, "bank_name": "gardeshgari", "bank_title": "بانک گردشگری"},
    {"card_no": 639599, "bank_name": "ghavvamin", "bank_title": "بانک قوامین"},
    {"card_no": 627488, "bank_name": "kar_afarin", "bank_title": "بانک کارآفرین"},
    {"card_no": 502910, "bank_name": "kar_afarin", "bank_title": "بانک کارآفرین"},
    {"card_no": 603770, "bank_name": "keshavarzi", "bank_title": "بانک کشاورزی"},
    {"card_no": 639217, "bank_name": "keshavarzi", "bank_title": "بانک کشاورزی"},
    {"card_no": 628023, "bank_name": "maskan", "bank_title": "بانک مسکن"},
    {"card_no": 639370, "bank_name": "mehr_e_eghtesad", "bank_title": "بانک مهر اقتصاد"},
    {"card_no": 606373, "bank_name": "mehr_e_iranian", "bank_title": "بانک قرض الحسنه مهر ایرانیان"},
    {"card_no": 603799, "bank_name": "meli", "bank_title": "بانک ملی ایران"},
    {"card_no": 610433, "bank_name": "mellat", "bank_title": "بانک ملت"},
    {"card_no": 991975, "bank_name": "mellat", "bank_title": "بانک ملت"},
    {"card_no": 622106, "bank_name": "parsian", "bank_title": "بانک پارسیان"},
    {"card_no": 502229, "bank_name": "pasargad", "bank_title": "بانک پاسارگاد"},
    {"card_no": 639347, "bank_name": "pasargad", "bank_title": "بانک پاسارگاد"},
    {"card_no": 627760, "bank_name": "post_bank", "bank_title": "پست بانک ایران"},
    {"card_no": 589463, "bank_name": "refah", "bank_title": "بانک رفاه"},
    {"card_no": 627961, "bank_name": "saanat_va_maadan", "bank_title": "بانک صنعت و معدن"},
    {"card_no": 603769, "bank_name": "saderat", "bank_title": "بانک صادرات"},
    {"card_no": 621986, "bank_name": "saman", "bank_title": "بانک سامان"},
    {"card_no": 639607, "bank_name": "sarmayeh", "bank_title": "بانک سرمایه"},
    {"card_no": 589210, "bank_name": "sepah", "bank_title": "بانک سپه"},
    {"card_no": 504706, "bank_name": "shahr", "bank_title": "بانک شهر"},
    {"card_no": 502806, "bank_name": "shahr", "bank_title": "بانک شهر"},
    {"card_no": 639346, "bank_name": "sina", "bank_title": "بانک سینا"},
    {"card_no": 627353, "bank_name": "tejarat", "bank_title": "بانک تجارت"},
    {"card_no": 585983, "bank_name": "tejarat", "bank_title": "بانک تجارت"},
    {"card_no": 636949, "bank_name": "hekmat", "bank_title": "بانک حکمت"},
    {"card_no": 627648, "bank_name": "tosee_saderat", "bank_title": "بانک توسعه صادرات"},
    {"card_no": 502908, "bank_name": "tosee_taavon", "bank_title": "بانک توسعه تعاون"},
]


def detect_bank(card_number: str) -> dict | None:
    # Remove all non-digit characters
    card_number = ''.join(filter(str.isdigit, str(card_number)))
    
    # Check minimum length
    if len(card_number) < 6:
        return None
    
    # Extract first 6 digits
    card_prefix = int(card_number[:6])
    
    # Find matching bank
    for bank in IRANIAN_BANKS:
        if bank["card_no"] == card_prefix:
            return bank
    
    return None


def validate_iranian_card_number(card_number: str) -> bool:
    return detect_bank(card_number) is not None

