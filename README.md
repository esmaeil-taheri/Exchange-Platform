# Django Modular - Digital Currency Exchange & Trading System

## 📋 Table of Contents
- [About the Project](#about-the-project)
- [System Architecture](#system-architecture)
- [Technologies Used](#technologies-used)
- [Installation & Setup](#installation--setup)
- [Project Structure](#project-structure)
- [Main Applications](#main-applications)
- [API Documentation](#api-documentation)
- [Project Status](#project-status)

---

## 📱 About the Project

**Django Modular** is a digital currency e-commerce platform for buying and selling digital assets (especially XAU18 cryptocurrency gold) built with a highly **modular** and scalable architecture.

### Key Features:
- ✅ Digital asset buying and selling system
- ✅ Precise multi-wallet management
- ✅ Daily transaction limit system
- ✅ Two-Factor Authentication (2FA) with OTP
- ✅ Real-time price chart and automated calculations
- ✅ Monitoring and surveillance system (Prometheus)
- ✅ Asynchronous task queues (Celery)
- ✅ Auto-generated API documentation (Swagger/OpenAPI)
- ✅ Advanced admin panel (Jazzmin)

---

## 🏗️ System Architecture

The project is built on **Domain-Driven Design (DDD)** and **Layered Architecture**:

```
┌─────────────────────────────────────────┐
│         API Layer (REST Endpoints)      │ ← HTTP Requests
├─────────────────────────────────────────┤
│  Views & Serializers & Permissions      │ ← Validation & Authorization
├─────────────────────────────────────────┤
│         Service Layer (Business Logic)  │ ← Core Business Rules
├─────────────────────────────────────────┤
│  Selector Layer (Read-only Queries)     │ ← Database Access (Read)
├─────────────────────────────────────────┤
│           Models & Database             │ ← PostgreSQL
├─────────────────────────────────────────┤
│   Async Tasks (Celery) & Signals        │ ← Background Operations
└─────────────────────────────────────────┘
```

### Architecture Principles:
1. **Separation of Concerns**: Each layer has a specific responsibility
2. **Reusability**: Shared code in the `core` module
3. **Testability**: Each component can be tested independently
4. **Scalability**: Structure ready for growth and increased load

---

## 🛠️ Technologies Used

### Backend Stack:
| Component | Version | Description |
|-----------|---------|-------------|
| **Django** | 5.2.11 | Web Framework |
| **DRF** | 3.16.1 | REST API Development |
| **PostgreSQL** | 16 | Database |
| **Redis** | 7 | Caching & OTP Storage |
| **Celery** | 5.6.3 | Async Task Queue |

### Libraries:
| **Module** | **Purpose** |
|-----------|-----------|
| `djangorestframework_simplejwt` | JWT Authentication |
| `drf-spectacular` | OpenAPI/Swagger Documentation |
| `django-cors-headers` | CORS Configuration |
| `django-redis` | Redis Cache Backend |
| `pyotp` | Two-Factor Authentication (OTP) |
| `django-celery-beat` | Scheduled Tasks |
| `django-prometheus` | Metrics & Monitoring |
| `minio` | Object Storage |
| `pillow` | Image Processing |
| `jdatetime` | Jalali Calendar Support |
| `jazzmin` | Admin UI |

### Infrastructure:
- **Docker & Docker Compose**: Container orchestration
- **Nginx**: Reverse Proxy
- **Prometheus**: Metrics Collection

---

## 🚀 Installation & Setup

### Prerequisites:
- Python 3.12+
- Docker & Docker Compose
- Git

### Installation Steps:

#### 1️⃣ Clone and Setup Environment:
```bash
git clone <repository-url>
cd Django\ modular

# Create .env file
cp .env.example .env  # Edit environment variables

# Start Docker
docker-compose up -d
```

#### 2️⃣ Database Migration:
```bash
docker-compose exec web python manage.py migrate
```

#### 3️⃣ Create Super User:
```bash
docker-compose exec web python manage.py createsuperuser
```

#### 4️⃣ Collect Static Files:
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

#### Environment Variables (.env):
```env
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_HOST=db
DATABASE_PORT=5432
DATABASE_USER=django_user
DATABASE_PASSWORD=secure_password
DATABASE_NAME=django_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASS=

# App Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

---

## 📁 Project Structure

```
Django modular/
├── docker-compose.yml          # Docker services definition
├── docker/
│   ├── Dockerfile.dev          # Development image
│   └── Dockerfile.prod         # Production image
├── nginx.conf                  # Nginx configuration
├── manage.py                   # Django management
├── pyproject.toml              # Project metadata
├── requirements.txt            # Dependencies
│
├── src/
│   ├── config/                 # Main Django settings
│   │   ├── settings/
│   │   │   ├── base.py         # Base settings (shared)
│   │   │   ├── dev.py          # Development settings
│   │   │   └── prod.py         # Production settings
│   │   ├── urls.py             # URL routing
│   │   ├── wsgi.py
│   │   ├── asgi.py
│   │   └── celery.py
│   │
│   ├── apps/
│   │   │
│   │   ├── core/               # ⭐ Shared library
│   │   │   ├── base_model.py
│   │   │   ├── base_service.py
│   │   │   ├── pagination.py
│   │   │   ├── exceptions/     # Custom Exceptions
│   │   │   ├── mixins/         # Reusable Mixins
│   │   │   ├── services/       # Shared Services
│   │   │   └── utils/          # Utility Functions
│   │   │
│   │   ├── accounts/           # 👤 Authentication & Users
│   │   │   ├── models/         # CustomUser
│   │   │   ├── api/            # Login, Logout, Register
│   │   │   ├── services/       # Auth Services
│   │   │   ├── selectors/      # User Queries
│   │   │   ├── tasks/          # Async Tasks
│   │   │   └── tests/
│   │   │
│   │   ├── customers/          # 🧑‍💼 Customer Information
│   │   │   ├── models/
│   │   │   │   ├── customer.py
│   │   │   │   ├── bank_card.py
│   │   │   │   ├── kyc.py      # Know Your Customer
│   │   │   │   └── kyc_document.py
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   └── selectors/
│   │   │
│   │   ├── exchange/           # ⭐ Core System - Buy & Sell
│   │   │   ├── models/
│   │   │   │   ├── currency.py      # Currency definitions
│   │   │   │   ├── wallet.py        # User wallets
│   │   │   │   ├── transaction.py   # Transactions
│   │   │   │   ├── price_log.py     # Price logs
│   │   │   │   ├── order.py
│   │   │   │   ├── currency_balance.py
│   │   │   │   └── daily_transaction_limit.py
│   │   │   ├── api/
│   │   │   │   ├── views/
│   │   │   │   │   ├── buy_sell_views.py
│   │   │   │   │   └── price_views.py
│   │   │   │   └── serializers/
│   │   │   ├── services/
│   │   │   │   ├── exchange_services.py  # Buy/Sell Logic
│   │   │   │   ├── currency_balance_service.py
│   │   │   │   ├── daily_limit_services.py
│   │   │   │   ├── price_services.py
│   │   │   │   ├── transaction_service.py
│   │   │   │   └── wallet_service.py
│   │   │   ├── selectors/
│   │   │   │   ├── currency_selectors.py
│   │   │   │   └── wallet_selectors.py
│   │   │   ├── exceptions/
│   │   │   ├── tasks/
│   │   │   └── tests/
│   │   │
│   │   ├── notifications/      # 🔔 Notifications
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   └── services/
│   │   │
│   │   ├── admins/             # 👨‍💼 Site Management
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   └── services/
│   │   │
│   │   └── site_setting/       # ⚙️ System Settings
│   │       ├── models/
│   │       ├── selectors/
│   │       └── services/
│   │
│   └── static/                 # Static Files
│       ├── admin/
│       ├── drf_spectacular/
│       ├── jazzmin/
│       └── rest_framework/
│
├── tests/                      # 🧪 Integration Tests
│   └── integration/
│
└── docs/
    └── archecture.md           # Architecture Documentation
```

---

## 📦 Main Applications

### 1️⃣ **Accounts App** - Authentication & Users
**Models:**
- `CustomUser` - Custom user with 2FA support

**API Endpoints:**
```
POST   /api/v1/authentication/login/      - Login
POST   /api/v1/authentication/register/   - Register
POST   /api/v1/authentication/logout/     - Logout
POST   /api/v1/authentication/refresh/    - Refresh Token
POST   /api/v1/authentication/2fa/verify/ - Verify 2FA
```

---

### 2️⃣ **Exchange App** - Buy & Sell System (⭐ Most Important)

#### **Data Models:**

**Currency** (Assets):
```python
- symbol          # Currency symbol (XAU18, BTC)
- fa_title / en_title
- logo_url
- lowest_amount_buy/sell
- buy_fee_percent / fixed_buy_fee_toman
- sell_fee_percent / fixed_sell_fee_toman
- is_buy / is_sell
- buy_from_wallet / buy_from_gateway
```

**Wallet** (User Wallets):
```python
- customer        # Wallet owner
- wallet_type     # Type: 'irt' (Toman) or 'xau' (Gold)
- amount          # Balance
- is_verified     # Verified status
- created_at      # Creation timestamp
```

**Transaction** (Transactions):
```python
- customer
- currency        # Transacted currency
- wallet          # Related wallet
- amount          # Asset amount
- fee_amount
- fee_irt / unit_price_irt / total_price_irt
- status          # pending, success, rejected
- type            # buy, sell
- ip              # User IP
```

#### **API Endpoints:**
```
GET    /api/v1/exchange/buy-sell-price/       - Real-time buy/sell price
POST   /api/v1/exchange/price-calculator/     - Calculate price for amount
POST   /api/v1/exchange/buy/                  - Buy asset
POST   /api/v1/exchange/sell/                 - Sell asset
GET    /api/v1/exchange/balance/              - User balance
GET    /api/v1/exchange/transactions/         - Transaction history
GET    /api/v1/exchange/invoice-list/         - Invoice list
GET    /api/v1/exchange/chart/                - Price chart
```

#### **Business Logic (Services):**

**ExchangeService.buy_asset()**
- ✅ Verify buy is enabled (organization & currency)
- ✅ Calculate real-time price
- ✅ Check daily limit
- ✅ Settle from wallet or payment gateway
- ✅ Record transaction
- ✅ Send notifications

**ExchangeService.sell_asset()**
- ✅ Check user balance
- ✅ Recalculate price
- ✅ Deduct fees and commissions
- ✅ Record transaction

---

### 3️⃣ **Customers App** - Customer Information
**Models:**
- `Customer` - Customer profile
- `BankCard` - Bank cards
- `KYC` - Identity verification (Know Your Customer)
- `KYCDocument` - KYC documents

---

### 4️⃣ **Notifications App** - Notification System
System for sending messages, emails, or SMS for important events

---

### 5️⃣ **Site Settings** - System Settings
**Configurable Values:**
- `is_buy` - Enable/disable global buying
- `is_sell` - Enable/disable global selling
- Various commissions
- Daily limits

---

## 🌐 API Documentation

The project has auto-generated **Swagger/OpenAPI** documentation:

```
GET /api/schema/              - OpenAPI Schema
GET /api/swagger/             - Swagger UI
GET /api/redoc/               - ReDoc (Alternative UI)
```

**Example buy request:**
```bash
# 1. Login and get token
curl -X POST http://localhost:8000/api/v1/authentication/login/ \
  -d '{"username":"user","password":"pass"}'
# Response: {"access": "eyJ...", "refresh": "eyJ..."}

# 2. Buy asset
curl -X POST http://localhost:8000/api/v1/exchange/buy/ \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{
    "asset": "XAU18",
    "amount": 10,
    "buy_from_wallet": true
  }'
```

---

## 🔐 Security Features

### Authentication:
- ✅ JWT (JSON Web Tokens) - `djangorestframework_simplejwt`
- ✅ 2FA/OTP - `pyotp` + Redis
- ✅ User Suspension Support

### Authorization:
- ✅ Permission Classes (Under development)
- ✅ Role-Based Access Control (Ready)

### Data Protection:
- ✅ CORS Security
- ✅ IP Tracking
- ✅ Request/Response Logging
- ✅ Timestamp Validation

---

## 📊 Monitoring & Logging

### Prometheus Metrics:
- ✅ Request Count & Duration
- ✅ Error Rates
- ✅ Database Connection Pool
- ✅ Cache Hit/Miss Rates

### Logging:
- ✅ Request Logging (Middleware)
- ✅ Error Tracking
- ✅ Audit Trail (Who did what, when, and from where)

---

## ⚙️ Celery Tasks

### Async Operations:
```python
# Examples
- send_transaction_notification()
- calculate_daily_limits()
- update_price_feeds()
- cleanup_old_logs()
```

### Scheduler (Django Celery Beat):
Tasks that run automatically at specified times

---

## 🧪 Testing

### Framework: pytest + pytest-django

```bash
# Run all tests
pytest

# Run specific tests
pytest src/apps/exchange/tests/

# With Coverage Report
pytest --cov=src
```

### Current Status:
- ❌ Unit Tests: Not written (Framework is ready)
- ❌ Integration Tests: Not written
- ✅ Framework and Configuration ready


</div>

