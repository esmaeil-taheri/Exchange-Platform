my_project/
├── .env                # متغیرهای محیطی (هرگز نباید در گیت کامیت شوند)
├── .gitignore
├── manage.py           # انتقال به پوشه src یا نگه داشتن در ریشه (بسته به سلیقه)
├── pyproject.toml      # مدیریت وابستگی‌ها (به جای requirements.txt)
├── README.md
├── src/                # تمامی کدهای اپلیکیشن در اینجا قرار می‌گیرد
│   ├── manage.py       # (اختیاری: اگر می‌خواهید کاملاً ایزوله باشد)
│   ├── config/         # فایل‌های تنظیمات جنگو (Settings, WSGI, ASGI)
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── prod.py
│   │   │   └── dev.py
│   │   └── urls.py
│   ├── apps/           # اینجا قلب تپنده پروژه است
│   │   ├── users/      # یک اپلیکیشن مستقل
│   │   ├── billing/    # یک اپلیکیشن مستقل
│   │   └── ...
│   └── common/         # کدهای اشتراکی (Middleware, Utils, Base Classes)
├── tests/              # تست‌های یکپارچه‌سازی و کلان
└── static/             # فایل‌های استاتیک جمع‌آوری شده

my_project/
│
├── .env
├── .gitignore
├── pyproject.toml
├── README.md
├── manage.py
│
├── src/
│   │
│   ├── config/                     # تنظیمات اصلی جنگو
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── wsgi.py
│   │   ├── urls.py
│   │   └── settings/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── dev.py
│   │       └── prod.py
│   │
│   ├── apps/
│   │   │
│   │   ├── core/                   # ابزارهای مشترک پروژه
│   │   │   ├── __init__.py
│   │   │   ├── base_models.py
│   │   │   ├── base_service.py
│   │   │   ├── exceptions/
│   │   │   │   └── custom_exceptions.py
│   │   │   ├── utils/
│   │   │   │   └── helpers.py
│   │   │   └── mixins/
│   │   │       └── timestamp_mixin.py
│   │   │
│   │   ├── users/
│   │   │   │
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── admin.py
│   │   │   ├── urls.py
│   │   │
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── user.py
│   │   │
│   │   │   ├── selectors/          # فقط read query
│   │   │   │   ├── __init__.py
│   │   │   │   └── user_selectors.py
│   │   │
│   │   │   ├── services/           # business logic + write
│   │   │   │   ├── __init__.py
│   │   │   │   └── user_services.py
│   │   │
│   │   │   ├── api/                # لایه API
│   │   │   │   ├── __init__.py
│   │   │   │
│   │   │   │   ├── serializers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── user_serializer.py
│   │   │   │   │
│   │   │   │   ├── views/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── user_views.py
│   │   │   │   │
│   │   │   │   └── permissions/
│   │   │   │       └── user_permissions.py
│   │   │
│   │   │   ├── tasks/              # celery tasks
│   │   │   │   ├── __init__.py
│   │   │   │   └── send_welcome_email.py
│   │   │
│   │   │   ├── signals/
│   │   │   │   └── user_signals.py
│   │   │
│   │   │   └── tests/
│   │   │       ├── __init__.py
│   │   │       ├── test_services.py
│   │   │       └── test_selectors.py
│   │   │
│   │   │
│   │   ├── billing/
│   │   │   │
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── urls.py
│   │   │
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── invoice.py
│   │   │   │   └── payment.py
│   │   │
│   │   │   ├── selectors/
│   │   │   │   ├── invoice_selectors.py
│   │   │   │   └── payment_selectors.py
│   │   │
│   │   │   ├── services/
│   │   │   │   ├── invoice_services.py
│   │   │   │   └── payment_services.py
│   │   │
│   │   │   ├── api/
│   │   │   │   ├── serializers/
│   │   │   │   │   ├── invoice_serializer.py
│   │   │   │   │   └── payment_serializer.py
│   │   │   │   │
│   │   │   │   └── views/
│   │   │   │       ├── invoice_views.py
│   │   │   │       └── payment_views.py
│   │   │
│   │   │   ├── tasks/
│   │   │   │   └── process_payment.py
│   │   │
│   │   │   └── tests/
│   │   │       ├── test_services.py
│   │   │       └── test_selectors.py
│   │   │
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── tests/                           # integration tests
│
├── static/
└── media/
