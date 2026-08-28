<div align="center">

# ⚡ Exchange Platform

### Enterprise-Grade Digital Asset Trading System

[![Django](https://img.shields.io/badge/Django-5.2.11-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16.1-red?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.6.3-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

*A production-ready, modular backend for buying, selling, and settling digital assets — built with clean architecture principles and financial-grade reliability.*

</div>

---

## Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Core Modules](#-core-modules)
- [User & System Flows](#-user--system-flows)
- [API Reference](#-api-reference)
- [Security](#-security)
- [Infrastructure & DevOps](#-infrastructure--devops)
- [Getting Started](#-getting-started)
- [Dependency Management (uv)](#-dependency-management-uv)
- [Tests & Coverage](#-tests--coverage)
- [Environment Variables](#-environment-variables)
- [Background Tasks](#-background-tasks)

---

## 🌐 Overview

**Exchange Platform** is a full-featured fintech backend platform for trading digital assets. It enables users to buy and sell digital assets using two payment methods — direct wallet balance or live payment gateway — with real-time pricing, KYC verification, multi-wallet management, and automated bank settlement.

### What makes it production-ready:

- **Financial-grade atomicity** — all balance changes happen inside `select_for_update()` locked atomic transactions, preventing race conditions and double-spending
- **Idempotent payment processing** — Zarinpal callbacks are safely retried without duplicating credits
- **Fully async settlement** — Celery workers handle post-payment processing, bank withdrawals, and notification delivery without blocking the request cycle
- **Modular, layered codebase** — strict separation between API, service, selector, and model layers enables independent testing and scaling of each domain

---

## 🏗 Architecture

The system follows a **strict 4-layer architecture** per application:

```
┌──────────────────────────────────────────────────────────────┐
│                     Client (Mobile / Web)                    │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS
┌──────────────────────────────▼───────────────────────────────┐
│                    Nginx  (Reverse Proxy)                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                   Django REST Framework                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │    Views    │  │ Serializers  │  │     Permissions      │ │
│  └──────┬──────┘  └──────┬───────┘  └──────────────────────┘ │
│         └────────────────▼                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Service Layer  (Business Logic)           │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐  │
│  │              Selector Layer  (Read Queries)            │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐  │
│  │                  Models  (PostgreSQL)                  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼──────┐  ┌─────────▼──────┐  ┌─────────▼──────┐
│  Celery Worker │  │  Celery  Beat  │  │     Redis      │
│ (Async Tasks)  │  │  (Scheduler)   │  │ (Cache + OTP)  │
└────────────────┘  └────────────────┘  └────────────────┘
```

### Architectural Principles

| Principle | Implementation |
|-----------|----------------|
| **Separation of Concerns** | Each layer has one responsibility — views never touch DB directly |
| **Single Responsibility** | Each service method does one thing; complex flows are composed |
| **Atomic Operations** | All financial mutations use `transaction.atomic()` + `select_for_update()` |
| **Async by Default** | Post-payment and settlement logic always runs in Celery |
| **Idempotency** | Payment callbacks and task retries are safe to run multiple times |
| **Fail-Safe** | Failed tasks log and alert; no silent swallowing of financial errors |

---

## 🛠 Technology Stack

### Core

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | Django | 5.2.11 |
| REST API | Django REST Framework | 3.16.1 |
| Database | PostgreSQL | 16 |
| Cache & OTP Store | Redis | 7 |
| Task Queue | Celery | 5.6.3 |
| Task Scheduler | Celery Beat (DB scheduler) | — |
| Task Monitor | Flower | — |

### Authentication & Security

| Component | Technology |
|-----------|-----------|
| Token Auth | JWT (`djangorestframework_simplejwt`) |
| Two-Factor Auth | TOTP (`pyotp`) + Redis |
| OTP Delivery | SMS.ir |
| Admin 2FA | TOTP + IP Whitelist |

### Integrations

| Integration | Provider | Purpose |
|-------------|----------|---------|
| Payment Gateway | Zarinpal | Accepting card payments |
| Bank Settlement | Vandar | Withdrawing funds to bank accounts (Paya) |
| Identity Verification | NeginHub (Shahkar + Inquiry) | KYC phone-to-ID matching |
| Object Storage | MinIO (S3-compatible) | Storing KYC documents |
| SMS | SMS.ir | OTP + notifications |

### Tooling

| Tool | Purpose |
|------|---------|
| `drf-spectacular` | Auto-generated OpenAPI / Swagger docs |
| `jazzmin` | Enhanced Django admin UI |
| `django-prometheus` | Metrics exposure for Prometheus / Grafana |
| `jdatetime` | Jalali (Shamsi) calendar support |
| `pillow` | Image processing for uploaded documents |
| `python-decouple` | 12-factor env-based configuration |

---

## 📁 Project Structure

```
Django modular/
│
├── docker-compose.yml              # All services: Django, Postgres, Redis, Celery, Flower, Nginx
├── docker/
│   ├── Dockerfile.dev              # Development image
│   └── Dockerfile.prod             # Production image
├── nginx.conf                      # Reverse proxy config
├── pyproject.toml                  # Dependencies (uv) + pytest/coverage config
├── uv.lock                         # Fully resolved dependency tree — committed
│
└── src/
    ├── config/                     # Project-level configuration
    │   ├── settings/
    │   │   ├── base.py             # Shared settings (DB, Redis, JWT, Celery, etc.)
    │   │   ├── dev.py              # Development overrides
    │   │   └── prod.py             # Production overrides
    │   ├── urls.py                 # Root URL routing
    │   ├── celery.py               # Celery app + autodiscover
    │   ├── wsgi.py
    │   └── asgi.py
    │
    └── apps/
        │
        ├── core/                   # ⭐ Shared kernel (imported by all apps)
        │   ├── base_model.py       # Abstract timestamped model
        │   ├── exceptions/         # Shared exception hierarchy
        │   ├── services/           # External clients (Zarinpal, Vandar, MinIO, SMS.ir, NeginHub)
        │   ├── mixins/             # Reusable view / serializer mixins
        │   └── utils/              # Helpers (Jalali, IP extraction, etc.)
        │
        ├── accounts/               # 👤 Auth & User management
        │   ├── models/             # CustomUser
        │   ├── api/                # Login, OTP verify, 2FA setup
        │   ├── services/           # OTP generation, JWT issuance, 2FA toggle
        │   └── selectors/          # User lookup queries
        │
        ├── customers/              # 🧑 Customer profiles, KYC, bank cards
        │   ├── models/
        │   │   ├── customer.py     # Profile, level, referral
        │   │   ├── bank_card.py    # Card + IBAN + ownership verification
        │   │   ├── kyc.py          # KYC state machine
        │   │   └── kyc_document.py # Uploaded ID documents
        │   ├── api/
        │   ├── services/           # KYC flow, card creation, document upload
        │   └── tasks/              # Batch card ownership verification
        │
        ├── exchange/               # ⭐ Core trading engine
        │   ├── models/
        │   │   ├── currency.py         # Asset definition + fee config
        │   │   ├── wallet.py           # User balance entries
        │   │   ├── transaction.py      # Buy/sell record
        │   │   ├── currency_balance.py # System asset inventory
        │   │   ├── price_log.py        # Historical price log
        │   │   └── daily_limit.py      # Singleton daily limit config
        │   ├── api/
        │   │   ├── views/
        │   │   │   ├── buy_sell_views.py
        │   │   │   └── price_views.py
        │   │   └── serializers/
        │   ├── services/
        │   │   ├── exchange_services.py        # buy_asset / sell_asset
        │   │   ├── price_services.py           # Dynamic pricing + fee calculation
        │   │   ├── wallet_service.py           # Balance debit/credit
        │   │   ├── currency_balance_service.py # Inventory management
        │   │   ├── transaction_service.py      # Transaction lifecycle
        │   │   └── daily_limit_services.py     # Daily cap enforcement
        │   ├── selectors/
        │   └── tasks/
        │       ├── exchange_tasks.py   # Post-buy / post-sell async processing
        │       └── price_tasks.py      # Asset price feed polling
        │
        ├── payments/               # 💳 Payment gateway (Zarinpal)
        │   ├── models/             # Invoice
        │   ├── api/                # Deposit initiation + Zarinpal callback
        │   ├── services/           # Invoice creation, gateway link, callback handling
        │   └── tasks/              # process_buy_invoice, process_deposit, stuck invoice retry
        │
        ├── settlements/            # 🏦 Bank withdrawals (Vandar)
        │   ├── models/             # Withdrawal (full Vandar response fields)
        │   ├── api/                # Create + list + detail
        │   ├── services/           # initiate_withdrawal_request (atomic)
        │   └── tasks/              # process_withdrawal_requests, inquiry polling
        │
        ├── notifications/          # 🔔 User notifications
        │   ├── models/             # Template + Notification + ReadStatus
        │   ├── api/
        │   └── services/           # Template-based notification creation
        │
        ├── admins/                 # 👨‍💼 Admin users + IP whitelist
        │   └── models/             # SiteAdmin, TrustedIp
        │
        └── site_setting/           # ⚙️ Global feature flags (singleton)
            └── models/             # SiteSetting (is_buy, is_sell, limits, etc.)
```

---

## 📦 Core Modules

### `accounts` — Authentication

**Flow**: Phone number → OTP via SMS → JWT issued

| Model | Key Fields |
|-------|-----------|
| `CustomUser` | `phone_number`, `national_id`, `is_suspended`, `is_2fa_enabled`, `totp_secret`, `last_ip_address` |

**Services:**
- `login_register()` — Generate 6-digit OTP, cache in Redis (120s TTL), send via SMS.ir
- `login_register_verify()` — Validate OTP, create user if new, issue JWT access + refresh tokens
- `setup_2fa()` — Generate TOTP secret + provisioning URI for Google Authenticator
- `two_fa_change_status()` — Enable/disable 2FA with live TOTP verification

---

### `customers` — Profiles, KYC & Bank Cards

| Model | Key Fields |
|-------|-----------|
| `Customer` | `status`, `level` (bronze/silver/platinum), `referral_code` |
| `BankCard` | `card_number`, `shaba_number`, `is_verified`, `ownership_counter` |
| `Kyc` | Status machine: `NOT_STARTED → SHAHKAR_VERIFIED → PENDING_UPLOAD → PENDING_REVIEW → APPROVED` |
| `KycDocument` | `image_url` (MinIO), `verified` |

**KYC State Machine:**
```
NOT_STARTED
    │  verify_identity() — Shahkar API (phone ↔ national ID)
    ▼
SHAHKAR_VERIFIED
    │  verify_identity() — NeginHub Inquiry (name, father, DOB, alive status)
    ▼
PENDING_UPLOAD
    │  upload_doc() — national card image → MinIO
    ▼
PENDING_REVIEW   ← Admin manually reviews
    │
    ├──▶ APPROVED
    └──▶ REJECTED (with rejection_reason)
```

---

### `exchange` — Trading Engine ⭐

**Currency configuration** controls everything:

```
Currency
  ├── buy_fee_percent / fixed_buy_fee_toman   ← dynamic fee switching
  ├── sell_fee_percent / fixed_sell_fee_toman
  ├── maintance_fee                           ← per-gram maintenance charge
  ├── is_buy / is_sell                        ← per-asset kill switch
  ├── buy_from_wallet / buy_from_gateway      ← allowed payment methods
  └── lowest_amount_buy / lowest_amount_sell  ← minimum order size
```

**Dynamic Fee Calculation (PriceService):**

| Asset Amount | Fee Applied |
|-------------|-------------|
| `< 0.5g` | Fixed fee (`fixed_buy_fee_toman`) |
| `0.5g – 1g` | Linear interpolation between fixed and percentage |
| `≥ 1g` | Percentage fee (`buy_fee_percent`) |

Plus per-gram maintenance fee on top.

**Wallet system** uses append-only ledger entries:
- Each credit/debit creates a new `Wallet` row
- `is_verified` / `is_rejected` flags track processing state
- Current balance = sum of all verified wallet entries per `wallet_type`

**System Inventory** tracked in `CurrencyBalance`:
- `active_balance` — available assets to sell
- `locked_balance` — reserved pending transactions
- All mutations use `select_for_update()` to prevent overselling

---

### `payments` — Zarinpal Gateway

| Model | Key Fields |
|-------|-----------|
| `Invoice` | `status` (pending/paid/failed), `gateway_track_id`, `card_hash`, `card_pan`, `is_processed` |

**Payment lifecycle:**
1. `create_payment_gateway_link()` → POST to Zarinpal → get `authority` + redirect URL
2. User pays on Zarinpal page
3. Zarinpal calls `POST /api/v1/payments/zarinpal/callback`
4. `handle_zarinpal_callback()` → verify with Zarinpal → validate card hash → mark paid → dispatch Celery task
5. `process_buy_invoice_task` (Celery) → create XAU18 wallet entry + transaction record

> **Debug mode**: Zarinpal calls return mocked responses for local testing.

---

### `settlements` — Vandar Bank Withdrawal

| Model | Key Fields |
|-------|-----------|
| `Withdrawal` | `status` (pending → sent_to_bank → completed/failed), `track_id`, `iban`, `wage`, `vandar_status` |

**Settlement lifecycle:**
1. User requests withdrawal → debit IRT wallet atomically → create `Withdrawal` record
2. Celery `process_withdrawal_requests` → KYC check → Vandar `create_settlement()`
3. Vandar responds with `track_id` and settlement ETA
4. Celery `inquiry_processed_withdrawals` polls Vandar for final status
5. On completion → `Withdrawal.status = COMPLETED`

---

## 🔄 User & System Flows

### Full Buy Flow (Payment Gateway)

```
User                    API                   Celery              External
 │                       │                      │                     │
 ├─ POST /exchange/buy/ ─▶│                      │                     │
 │   buy_from_wallet=F   │                      │                     │
 │                       ├─ validate currency   │                     │
 │                       ├─ calculate price     │                     │
 │                       ├─ check daily limit   │                     │
 │                       ├─ create Invoice      │                     │
 │                       ├──────────────────────────────────────────▶ │ Zarinpal
 │                       │                      │                     │ create request
 │◀──── payment_link ────┤                      │                  ◀──┤ authority
 │                       │                      │                     │
 ├─ (user pays on Zarinpal page)                │                     │
 │                       │                      │                  ──▶│ Zarinpal verify
 ├─ Zarinpal callback ──▶│                      │                  ◀──┤ card_hash, ref_id
 │                       ├─ verify card hash    │                     │
 │                       ├─ mark Invoice paid   │                     │
 │                       ├─ dispatch task ─────▶│                     │
 │                       │                      ├─ create Transaction  │
 │                       │                      ├─ credit XAU wallet   │
 │                       │                      └─ send notification   │
 │◀─── success ──────────┤                                            │
```

### Full Sell Flow

```
POST /exchange/sell/
  │
  ├─ validate: is_sell enabled (global + currency)
  ├─ calculate sell price + fees
  ├─ check no pending transaction exists
  ├─ check daily sell limit
  │
  ├─ atomic transaction:
  │   ├─ select_for_update on XAU wallet
  │   ├─ verify sufficient XAU balance
  │   ├─ create Wallet entry (debit XAU)
  │   ├─ create Transaction (status=pending)
  │   └─ update CurrencyBalance.active_balance
  │
  └─ Celery process_sell_transactions:
      ├─ create Wallet entry (credit IRT)
      ├─ update Transaction (status=success)
      ├─ if card_withdraw: initiate Vandar settlement
      └─ send notification
```

### Withdrawal Flow

```
POST /settlements/withdrawals/create/
  │
  ├─ verify IRT wallet balance
  ├─ atomic:
  │   ├─ create Withdrawal (status=pending)
  │   └─ create Wallet entry (debit IRT)
  │
  └─ Celery process_withdrawal_requests:
      ├─ verify KYC = APPROVED
      ├─ run inquiry check (bank account ↔ KYC data)
      ├─ POST to Vandar create_settlement
      ├─ update Withdrawal (status=sent_to_bank, track_id)
      │
      └─ Celery inquiry_processed_withdrawals (polling):
          ├─ GET Vandar settlement status
          └─ update Withdrawal (completed / failed)
```

---

## 📡 API Reference

Base URL: `/api/v1/`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/authentication/login-register/` | Send OTP to phone number |
| `POST` | `/authentication/verify/` | Verify OTP → receive JWT tokens |
| `POST` | `/authentication/token/refresh/` | Refresh access token |
| `GET` | `/authentication/2fa/` | Get TOTP provisioning URI |
| `POST` | `/authentication/2fa/verify/` | Verify TOTP code |
| `POST` | `/authentication/2fa/change/` | Enable / disable 2FA |

### Customers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/customers/profile/` | Get customer profile |
| `GET` | `/customers/kyc/status/` | Get KYC verification status |
| `POST` | `/customers/kyc/verify-identity/` | Run Shahkar + identity inquiry |
| `POST` | `/customers/kyc/upload-doc/` | Upload national card image |
| `GET` | `/customers/card/` | List bank cards |
| `POST` | `/customers/card/create/` | Add bank card |
| `DELETE` | `/customers/card/<id>/` | Remove bank card |

### Exchange

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/exchange/buy-sell-price/` | Real-time buy & sell prices |
| `POST` | `/exchange/price-calculator/` | Calculate price for a given amount |
| `POST` | `/exchange/buy/` | Buy digital asset |
| `POST` | `/exchange/sell/` | Sell digital asset |
| `GET` | `/exchange/balance/` | User wallets (IRT + XAU18) |
| `GET` | `/exchange/transactions/` | Transaction history (paginated) |
| `GET` | `/exchange/invoice-list/` | Invoice list |
| `GET` | `/exchange/chart/` | Price chart data |

### Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/payments/deposit/` | Initiate wallet deposit via gateway |
| `POST` | `/payments/zarinpal/callback/` | Zarinpal payment callback handler |

### Settlements

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/settlements/withdrawals/` | List withdrawals (filterable by status) |
| `POST` | `/settlements/withdrawals/create/` | Request bank withdrawal |
| `GET` | `/settlements/withdrawals/<id>/` | Withdrawal detail |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/notifications/` | List notifications |
| `POST` | `/notifications/read/<id>/` | Mark notification as read |

### Docs

| Endpoint | Description |
|----------|-------------|
| `/api/schema/` | OpenAPI JSON schema |
| `/api/swagger/` | Interactive Swagger UI |
| `/api/redoc/` | ReDoc documentation |

---

## 🔐 Security

### Authentication Layers

```
Layer 1: SMS OTP     — 6-digit code, 120s TTL, Redis-backed
Layer 2: JWT         — 1-day access token, 7-day refresh, rotation enabled
Layer 3: TOTP 2FA    — Optional Google Authenticator integration
Layer 4: IP Tracking — Every transaction records client IP
```

### Admin Security
- Per-admin `TrustedIp` whitelist (M2M)
- OTP enforcement for admin login
- Jazzmin-enhanced admin panel

### Financial Integrity

| Mechanism | Purpose |
|-----------|---------|
| `select_for_update()` | Prevents race conditions on wallet reads |
| `transaction.atomic()` | All-or-nothing financial mutations |
| Idempotency flags (`is_processed`) | Safe Celery task retries |
| Daily transaction limits | System-wide buy/sell caps |
| Inventory locking (`CurrencyBalance`) | Prevents overselling assets |

---

## 🐳 Infrastructure & DevOps

### Docker Services

| Service | Image | Port |
|---------|-------|------|
| `backend` | Custom (Django) | 8000 |
| `db` | postgres:16 | 5432 |
| `redis` | redis:7 | 6379 |
| `celery` | Custom (worker) | — |
| `celery_beat` | Custom (scheduler) | — |
| `flower` | Custom (Celery monitor) | 5520 |
| `nginx` | nginx:mainline-alpine | 80 |

### Monitoring (Ready to Enable)

- **Prometheus** — metrics endpoint exposed via `django-prometheus`
- **Grafana** — dashboards (service defined, ready to activate)
- **Flower** — live Celery task monitor at `:5520`

### Settings Environments

| File | Usage |
|------|-------|
| `settings/base.py` | All shared config (DB, Redis, JWT, Celery, Zarinpal, Vandar...) |
| `settings/dev.py` | Debug=True, mock payment gateway |
| `settings/prod.py` | Debug=False, real gateway, stricter security |

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) 0.8+ (for local development without Docker)
- Git

uv manages both the Python toolchain and the dependencies — you do not need to
install Python 3.12 or create a virtualenv yourself.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "Django modular"
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual values (see Environment Variables section below)
```

### 3. Start All Services

```bash
docker-compose up -d
```

### 4. Run Migrations

```bash
docker-compose exec backend python manage.py migrate
```

### 5. Create Superuser

```bash
docker-compose exec backend python manage.py createsuperuser
```

### 6. Collect Static Files

```bash
docker-compose exec backend python manage.py collectstatic --noinput
```

### 7. Access the Platform

| URL | Description |
|-----|-------------|
| `http://localhost:8000/api/swagger/` | Swagger UI |
| `http://localhost:8000/admin/` | Django Admin |
| `http://localhost:5520/` | Celery Flower Monitor |
| `http://localhost:80/` | Nginx (Production proxy) |

---

## 📦 Dependency Management (uv)

`pyproject.toml` is the source of truth and `uv.lock` pins the entire
transitive tree. Both are committed; `.venv/` is not.

### Everyday commands

```bash
uv sync                    # create/update .venv to match uv.lock (includes dev group)
uv sync --no-dev           # runtime dependencies only — what the prod image installs
uv run pytest              # run the test suite
uv run python manage.py migrate
uv run ruff check src
```

`uv run` resolves the environment before each command, so there is no
virtualenv to activate.

### Dependency groups

| Group | Contents | Installed in |
|-------|----------|--------------|
| *(main)* | Django, DRF, Celery, psycopg2, gunicorn … | dev + production images |
| `dev` | pytest, pytest-django, pytest-mock, pytest-cov, ruff, flower | dev image and CI only |

The production image is built with `uv sync --locked --no-dev`, so test tooling
never ships to production.

### Changing dependencies

```bash
uv add <package>           # runtime dependency
uv add --dev <package>     # dev-only dependency
uv remove <package>
```

Each command updates `pyproject.toml` and `uv.lock` together — commit both.
There is no `requirements.txt` to regenerate: `uv.lock` is the single source of
truth, and every install path (both Dockerfiles and all CI jobs) reads it via
`uv sync --locked`. The `uv-lock` pre-commit hook keeps the lock in sync with
`pyproject.toml`.

### Building behind a restricted network

Both Dockerfiles accept an index override:

```bash
docker build -f docker/Dockerfile.prod \
  --build-arg UV_DEFAULT_INDEX=https://mirror-pypi.runflare.com/simple .
```

`Dockerfile.dev` already defaults to that mirror; `Dockerfile.prod` defaults to
`pypi.org`.

---

## 🧪 Tests & Coverage

```bash
uv run pytest                                   # full suite
uv run pytest --cov=src --cov-report=term-missing   # with coverage
uv run pytest src/apps/exchange -q              # one app
```

Configuration lives in `pyproject.toml` (`[tool.pytest.ini_options]` and
`[tool.coverage.*]`). Tests run against SQLite with migrations disabled, so the
suite needs no database container.

### Current status

| Metric | Value |
|--------|-------|
| Tests | **194 passed**, 1 skipped |
| Overall coverage | **70%** (3,491 statements, 436 branches) |
| Runtime | ~15s |

The skipped test is `TestRealRowLocks`, which needs real `SELECT ... FOR UPDATE`
blocking — SQLite ignores row locks, so it only runs against PostgreSQL.

### Coverage is uneven — read this before trusting the 70%

Coverage is concentrated in the API layer. The background workers that actually
move money and gold are close to untested:

| Module | Coverage |
|--------|----------|
| `payments/services/payments_services.py` | 94% |
| `exchange/api/views/buy_sell_views.py` | 97% |
| `settlements/services/settlement_services.py` | 93% |
| `exchange/services/exchange_services.py` | 79% |
| `exchange/services/price_services.py` | 52% |
| `exchange/services/daily_limit_services.py` | 28% |
| `settlements/tasks/settlement_tasks.py` | 22% |
| `payments/tasks/payment_tasks.py` | 21% |
| `exchange/tasks/price_tasks.py` | 20% |
| **`exchange/tasks/exchange_tasks.py`** | **9%** |
| `customers/tasks/bank_card_tasks.py` | 0% |


---

## ⚙️ Environment Variables

```env
# ─── Django ────────────────────────────────────────
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings.dev

# ─── Database ──────────────────────────────────────
DATABASE_HOST=db
DATABASE_PORT=5432
DATABASE_USER=django_user
DATABASE_PASSWORD=secure_password
DATABASE_NAME=django_db

# ─── Redis ─────────────────────────────────────────
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASS=your-redis-password

# ─── JWT ───────────────────────────────────────────
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_LIFETIME_DAYS=1
REFRESH_TOKEN_LIFETIME_DAYS=7

# ─── Object Storage (MinIO) ────────────────────────
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=kyc-documents
MINIO_SECURE=False

# ─── SMS Provider (SMS.ir) ─────────────────────────
SMS_IR_API_KEY=your-smsir-api-key
SMS_IR_OTP_TEMPLATE_ID=your-template-id

# ─── Payment Gateway (Zarinpal) ────────────────────
ZARINPAL_MERCHANT_ID=your-merchant-id
ZARINPAL_CALLBACK_URL=https://yourdomain.com/api/v1/payments/zarinpal/callback/

# ─── Settlement (Vandar) ───────────────────────────
VANDAR_API_KEY=your-vandar-api-key
VANDAR_BUSINESS_NAME=your-business-name

# ─── KYC / Identity Inquiry (NeginHub) ────────────
NEGINHUB_API_KEY=your-neginhub-api-key
NEGINHUB_BASE_URL=https://api.neginhub.com
```

---

## ⚡ Background Tasks

All async operations run through Celery. The Beat scheduler manages periodic tasks via the database (configurable from Django Admin).

### Task Registry

| Task | Trigger | Description |
|------|---------|-------------|
| `process_buy_invoice_task` | Post-payment callback | Credit XAU wallet after gateway payment |
| `process_deposit_invoice_task` | Post-payment callback | Credit IRT wallet after deposit |
| `process_stuck_invoices` | Periodic (Beat) | Retry invoices stuck in pending state |
| `process_buy_transactions` | Post-buy | Finalize wallet-funded buy orders |
| `process_sell_transactions` | Post-sell | Settle sell proceeds to IRT or bank |
| `process_withdrawal_requests` | Post-request | Send withdrawal to Vandar |
| `inquiry_processed_withdrawals` | Periodic (Beat) | Poll Vandar for settlement status |
| `check_cards_ownership` | Periodic (Beat) | Batch bank card ownership verification |
| `complete_verified_cards_information` | Periodic (Beat) | Enrich verified card data |
| `fetch_asset_price` | Periodic (Beat) | Pull latest XAU18 price from feed |

### Monitor Tasks Live

```bash
# Open Flower dashboard
open http://localhost:5520

# Or tail Celery worker logs
docker-compose logs -f celery
```

---

## 📊 Data Model Overview

```
CustomUser
  ├─── 1:1 ──▶ Customer
  │              ├─── 1:1 ──▶ Kyc ──▶ KycDocument (1:N)
  │              ├─── 1:N ──▶ BankCard
  │              ├─── 1:N ──▶ Wallet        (IRT + XAU18 ledger entries)
  │              ├─── 1:N ──▶ Transaction   (buy/sell history)
  │              ├─── 1:N ──▶ Invoice       (payment records)
  │              └─── 1:N ──▶ Withdrawal    (bank settlement requests)
  │
  └─── 1:1 ──▶ SiteAdmin
                 └─── M:N ──▶ TrustedIp

Currency
  ├─── 1:1 ──▶ CurrencyBalance   (system asset inventory)
  ├─── 1:N ──▶ CurrencyPriceLog  (historical price feed)
  └─── 1:N ──▶ Transaction       (all trades referencing this asset)
```

---

<div align="center">

Built with precision for financial reliability. Every Toman accounted for.

</div>
