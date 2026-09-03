# ⚡ Comprehensive System Analysis & Financial Flow Breakdown Report
### Online Trading Platform & Digital Asset Settlement (Gold Trading & Settlement Platform)

---

## 📑 Table of Contents
1. [System Overview and Architecture](#1-system-overview-and-architecture)
2. [Layered Architecture and Module Standards](#2-layered-architecture-and-module-standards)
3. [Authentication and Two-Factor Login Flow](#3-authentication-and-two-factor-login-flow)
4. [Customer KYC State Machine & Flow](#4-customer-kyc-state-machine--flow)
5. [Bank Card Verification Flow](#5-bank-card-verification-flow)
6. [Buy Gold from Wallet Flow](#6-buy-gold-from-wallet-flow)
7. [Buy Gold via Zarinpal Payment Gateway Flow](#7-buy-gold-via-zarinpal-payment-gateway-flow)
8. [Direct Rial Wallet Deposit Flow](#8-direct-rial-wallet-deposit-flow)
9. [Sell Gold and Settle to Wallet Flow](#9-sell-gold-and-settle-to-wallet-flow)
10. [Sell Gold with Direct Settlement to Bank Card Flow](#10-sell-gold-with-direct-settlement-to-bank-card-flow)
11. [Complete Withdrawal and Vandar Paya Settlement Flow](#11-complete-withdrawal-and-vandar-paya-settlement-flow)
12. [Idempotency and Concurrency Engine](#12-idempotency-and-concurrency-engine)
13. [Safety Nets and Periodic Reconciliation Workers](#13-safety-nets-and-periodic-reconciliation-workers)
14. [Test Status and Software Quality](#14-test-status-and-software-quality)
15. [Final Assessment and Project Technical Rating](#15-final-assessment-and-project-technical-rating)

---

## 1. System Overview and Architecture

The project is designed based on a **Clean / Layered Architecture** on top of Django 5.2 and DRF. None of the layers have direct access to the database, and responsibilities are precisely divided among the API layer, services (business logic), selectors (read queries), and models.

```mermaid
graph TD
    Client["Client (Mobile App / Web UI)"] -->|HTTPS| Nginx["Nginx Reverse Proxy"]
    Nginx -->|Gunicorn / WSGI| DRF["Django REST Framework Layer"]

    subgraph "Application Core (src/apps)"
        Views["API Views & Permissions"] --> Services["Service Layer (Business Logic & Transactions)"]
        Services --> Selectors["Selector Layer (Optimized Read Queries)"]
        Services --> Models["PostgreSQL Models (Ledger & States)"]
        Selectors --> Models
    end

    DRF --> Views

    subgraph "Background & Data Processing"
        Services --> CeleryW["Celery Workers (Async Settlement & Payouts)"]
        CeleryW --> Redis["Redis 7 (Broker / Cache / OTP / RateLimiter)"]
        CeleryBeat["Celery Beat (Cron Schedulers)"] --> CeleryW
        CeleryW --> DB[(PostgreSQL 16 Database)]
        Models --> DB
    end

    subgraph "External Providers (Third-Party APIs)"
        Services -.->|Payment Gateway| Zarinpal["Zarinpal PSP"]
        CeleryW -.->|Bank Payout / Paya| Vandar["Vandar Banking API"]
        Services -.->|Shahkar & Identity| NeginHub["NeginHub Government Inquiry"]
        Services -.->|OTP SMS| SMS["SMS.ir Provider"]
        Services -.->|Document Storage| MinIO["MinIO S3 Object Storage"]
    end
```

---

## 2. Layered Architecture and Module Standards

The folder structure across all modules (`accounts`, `customers`, `exchange`, `payments`, `settlements`, `notifications`, `site_setting`) follows the pattern below:

```
src/apps/<module_name>/
├── api/
│   ├── views/          # HTTP controllers and input validation
│   ├── serializers/    # DRF input and output serializers
│   └── permissions/    # User role permissions and guards
├── services/           # Operational logic, database changes, and atomic transactions (CUD)
├── selectors/          # Read-only data retrieval functions and queries with no side effects
├── models/             # Database table structures and indexes
├── tasks/              # Asynchronous Celery tasks
├── exceptions/         # Domain-specific exceptions
├── signals/            # Internal system signals
└── tests/              # Unit, integration, and concurrency tests
```

---

## 3. Authentication and Two-Factor Login Flow

Login is based on mobile phone number and a one-time password (OTP) with a 120-second time limit in Redis. If 2FA is enabled, the TOTP token is also verified.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Accounts API
    participant Cache as Redis (Cache / OTP)
    participant SMS as SMS.ir
    participant DB as PostgreSQL (User Table)

    User->>API: 1. POST /api/v1/authentication/login-register/ {phone_number}
    API->>Cache: Check that no active OTP exists (Rate-Limit)
    API->>Cache: Store 6-digit OTP with TTL = 120s
    API->>SMS: Send one-time password SMS
    SMS-->>User: Receive OTP SMS

    User->>API: 2. POST /api/v1/authentication/verify/ {phone_number, code}
    API->>Cache: Check and match the code against Redis

    alt Code was correct
        API->>DB: Create or update user
        API->>Cache: Remove consumed code from Redis
        API-->>User: Issue JWT Tokens (Access + Refresh)
    else Code invalid or expired
        API-->>User: InvalidOtp error (400)
    end

    opt Enable two-factor login (Google Authenticator)
        User->>API: POST /api/v1/authentication/2fa/setup/
        API-->>User: Return Secret Key + Provisioning URI (QR)
        User->>API: POST /api/v1/authentication/2fa/change-status/ {otp_code, totp_code}
        API->>API: Verify SMS code and TOTP code simultaneously
        API->>DB: Store is_2fa_enabled = True
    end
```

---

## 4. Customer KYC State Machine & Flow

The KYC process is carried out in 5 strict stages to verify the account holder's identity:

```mermaid
stateDiagram-v2
    [*] --> NOT_STARTED: Initial user registration

    NOT_STARTED --> SHAHKAR_VERIFIED: Shahkar inquiry (matching national ID with phone number)

    SHAHKAR_VERIFIED --> PENDING_UPLOAD: Civil registry identity inquiry (name, father's name, date of birth, alive status)

    PENDING_UPLOAD --> PENDING_REVIEW: Upload national ID card image to MinIO S3

    PENDING_REVIEW --> APPROVED: Manual approval by admin in the management panel
    PENDING_REVIEW --> REJECTED: Rejected by admin (with rejection reason noted)

    REJECTED --> PENDING_UPLOAD: User re-uploads document
    APPROVED --> [*]: User authorized for all trades and settlements
```

---

## 5. Bank Card Verification Flow

Customer bank cards must be automatically matched against their national ID, and the IBAN (Sheba) number and bank name must be retrieved:

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant API as Customers API
    participant DB as PostgreSQL (BankCard)
    participant Worker as Celery Worker (Card Tasks)
    participant Inquiry as NeginHub Inquiry API

    Customer->>API: Register bank card number
    API->>DB: Save card with is_verified=None and card_ownership=False

    loop Periodic job check_cards_ownership
        Worker->>DB: Fetch unverified cards (Batch Size 10)
        Worker->>Inquiry: Inquire matching of card number with user's national ID
        alt Ownership confirmed
            Worker->>DB: Update card_ownership=True
        else Ownership mismatch
            Worker->>DB: Record is_verified=False + rejection reason
        end
    end

    loop Periodic job complete_verified_cards_information
        Worker->>DB: Fetch cards with card_ownership=True
        Worker->>Inquiry: Retrieve additional information (Sheba number and bank name)
        Worker->>DB: Store Shaba_number, bank_name, and is_verified=True
    end
```

---

## 6. Buy Gold from Wallet Flow

In this method, the user purchases gold (XAU18) using the balance of their rial (IRT) wallet:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Exchange Service
    participant Guard as Idempotency Engine
    participant DB as PostgreSQL Ledger
    participant Worker as Celery Worker (process_buy_transactions)

    User->>API: POST /api/v1/exchange/buy/ {asset: "XAU18", amount, buy_from_wallet: True}
    API->>Guard: Register and lock Idempotency key

    rect rgb(240, 248, 255)
        Note over API,DB: Start atomic transaction (Database Transaction)
        API->>DB: Customer.objects.select_for_update() (lock user row)
        API->>DB: Check for no prior Pending transaction
        API->>DB: Calculate tiered fee and holding fee (PriceService)
        API->>DB: Check daily purchase limit
        API->>DB: Check system's sellable gold balance (CurrencyBalance)
        API->>DB: Check user's rial balance (Sum of Verified Wallet Entries)
        API->>DB: Record rial deduction row (Wallet Entry with negative amount)
        API->>DB: Create new Transaction (Status: PENDING, Type: BUY)
        API->>Guard: Mark idempotency as completed
    end

    API-->>User: 200 response (request registered successfully)

    rect rgb(255, 250, 240)
        Note over Worker,DB: Asynchronous settlement processing (Celery Task)
        Worker->>DB: Fetch transaction with select_for_update(skip_locked=True)
        Worker->>DB: Check market price fluctuation tolerance (max 1%)
        alt Price was valid
            Worker->>DB: Record gold deposit row (Wallet Entry with +XAU amount)
            Worker->>DB: Change Transaction status to SUCCESS
            Worker->>DB: Emit transaction completion signal (transaction_processed)
        else Severe fluctuation or mismatch
            Worker->>DB: Change Transaction status to REJECTED
            Worker->>DB: Fully refund the rial amount to the user's wallet (Refund Wallet Entry)
        end
    end
```

---

## 7. Buy Gold via Zarinpal Payment Gateway Flow

In this method, the user connects directly to the Zarinpal payment gateway without having a rial balance:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Payment Service
    participant Gate as Zarinpal Gateway
    participant DB as PostgreSQL
    participant Worker as Celery Worker (process_buy_invoice_task)

    User->>API: 1. POST /api/v1/exchange/buy/ {buy_from_wallet: False}
    API->>DB: Check user's verified bank card
    API->>DB: Create Invoice with pending status (type buy)
    API->>Gate: Create payment Authority ID (outside the database lock)
    API->>DB: Save authority on invoice
    API-->>User: Return gateway payment link

    User->>Gate: 2. Pay at the bank gateway
    Gate-->>API: 3. Zarinpal Callback invocation {Authority, Status}

    API->>Gate: Inquire and Verify transaction against invoice amount
    API->>API: Verify hash of payer's card against buyer's registered cards

    rect rgb(240, 248, 255)
        Note over API,DB: Lock and update invoice
        API->>DB: Invoice.objects.select_for_update()
        alt Card matched and payment confirmed
            API->>DB: Invoice status = PAID and is_paid = True
            API->>Worker: Dispatch process_buy_invoice_task asynchronously
        else Card was invalid
            API->>DB: Invoice status = REJECTED
        end
    end

    API-->>User: Display transaction result message

    rect rgb(255, 250, 240)
        Note over Worker,DB: Gold purchase settlement in the worker
        Worker->>DB: Calculate gold amount with ROUND_HALF_UP precision based on invoice-time price
        Worker->>DB: Create Transaction record with deposit_method = GATEWAY
        Worker->>DB: Mark Invoice.is_processed = True
        Worker->>DB: Forward to final gold settlement queue (process_buy_transactions)
    end
```

---

## 8. Direct Rial Wallet Deposit Flow

The user first tops up their rial wallet via the gateway in order to trade later:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Payments API
    participant Gate as Zarinpal Gateway
    participant DB as PostgreSQL
    participant Worker as Celery (process_deposit_invoice_task)

    User->>API: 1. POST /api/v1/payments/deposit/ {amount}
    API->>DB: Create Invoice with type deposit and status pending
    API->>Gate: Get payment link
    API-->>User: Redirect to payment gateway

    User->>Gate: 2. Pay the amount
    Gate-->>API: 3. Return to Callback
    API->>Gate: Verify payment
    API->>API: Check payer's bank card
    API->>DB: Mark invoice as PAID
    API->>Worker: Dispatch process_deposit_invoice_task(invoice_id) task
    API-->>User: Display success message

    Worker->>DB: Lock invoice row (select_for_update)
    Worker->>DB: Record rial deposit row (Wallet Entry with +amount)
    Worker->>DB: Mark is_processed = True
```

---

## 9. Sell Gold and Settle to Wallet Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Exchange Service
    participant DB as PostgreSQL Ledger
    participant Worker as Celery (process_sell_transactions)

    User->>API: POST /api/v1/exchange/sell/ {asset: "XAU18", amount, card_withdaraw: False}

    rect rgb(240, 248, 255)
        Note over API,DB: Atomic API transaction
        API->>DB: Customer.objects.select_for_update()
        API->>DB: Check daily sell limit and whether selling is enabled
        API->>DB: Check user's gold balance (XAU Balance)
        API->>DB: Deduct gold from user's wallet (Wallet Entry with -XAU amount)
        API->>DB: Create Transaction (Status: PENDING, Type: SELL, Method: WALLET)
    end
    API-->>User: Confirm sell request registration

    rect rgb(255, 250, 240)
        Note over Worker,DB: Settlement in background worker
        Worker->>DB: Lock transaction with select_for_update(skip_locked=True)
        Worker->>DB: Check for no unauthorized market price fluctuation
        Worker->>DB: Deposit equivalent rial amount to wallet (Wallet Entry with +IRT amount)
        Worker->>DB: Transaction status = SUCCESS
        Worker->>DB: Send signal and notification
    end
```

---

## 10. Sell Gold with Direct Settlement to Bank Card Flow

In this case, the user sells their gold and requests that the amount be settled (Paya) directly to their bank account:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Exchange Service
    participant DB as PostgreSQL
    participant WorkerSell as Celery (process_sell_transactions)
    participant WorkerWithdraw as Celery (process_withdrawal_requests)

    User->>API: POST /api/v1/exchange/sell/ {card_withdaraw: True, bank_card_id}
    API->>DB: Deduct user's gold + create Transaction of type SELL with withdraw_method=BANK
    API-->>User: Confirm sell order registration

    WorkerSell->>DB: Lock and process the sell transaction
    WorkerSell->>DB: Create a Withdrawal record for bank settlement
    WorkerSell->>DB: Transaction status = SUCCESS
    WorkerSell->>WorkerWithdraw: Asynchronously invoke process_withdrawal_requests(withdrawal.id)

    Note over WorkerWithdraw: Continue the process in the Vandar Paya settlement cycle
```

---

## 11. Complete Withdrawal and Vandar Paya Settlement Flow

Bank settlement requires managing complex banking states (success, failure, network error, Paya cycle delay):

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Settlement Service
    participant DB as PostgreSQL (Withdrawal / Wallet)
    participant Worker as Celery (process_withdrawal_requests)
    participant InquiryWorker as Celery (inquiry_processed_withdrawals)
    participant Vandar as Vandar Settlement API

    User->>API: 1. POST /api/v1/settlements/withdrawals/create/ {amount, card_id}
    rect rgb(240, 248, 255)
        Note over API,DB: Lock customer and deduct rial
        API->>DB: Customer.objects.select_for_update()
        API->>DB: Check rial balance
        API->>DB: Create Withdrawal record with status PENDING
        API->>DB: Deduct rial from wallet (Wallet Entry with negative amount)
    end
    API->>Worker: Queue task with countdown=10s
    API-->>User: Confirm withdrawal request registration

    rect rgb(255, 250, 240)
        Note over Worker,DB: Step 1: Claim and lock the settlement record
        Worker->>DB: Withdrawal.objects.select_for_update(skip_locked=True)
        Worker->>DB: Change status to PROCESSING and assign track_id

        Note over Worker,Vandar: Step 2: Call the Paya web service (outside the DB lock)
        Worker->>Vandar: POST /api/v3/business/{name}/settlement/store

        alt Definitive gateway error (invalid card / national ID mismatch)
            Worker->>DB: Status = FAILED + immediate refund of rial to wallet (Refund)
        else Network error / gateway timeout (unknown status)
            Worker->>DB: Status = SENT_TO_BANK (no early fund refund!)
        else Successful
            Worker->>DB: Status = SENT_TO_BANK + store bank transaction number
        end
    end

    rect rgb(245, 245, 245)
        Note over InquiryWorker,Vandar: Step 3: Reconciliation Polling
        InquiryWorker->>DB: Fetch SENT_TO_BANK rows based on least-recently-inquired
        InquiryWorker->>Vandar: Inquire settlement status (inquiry_settlement)

        alt Vandar response = DONE (funds settled in account)
            InquiryWorker->>DB: Status = COMPLETED and confirmed_at = Now
        else Vandar response = FAILED / CANCELED
            InquiryWorker->>DB: Status = FAILED + full refund of funds to user's wallet
        else Persistent 404 response for over 3 hours
            InquiryWorker->>DB: Confirm it was never sent to the bank + safely refund rial to wallet
        end
    end
```

---

## 12. Idempotency and Concurrency Engine

To ensure that no financial request is executed twice under network retry conditions or double-clicks, the idempotency core (`IdempotencyService`) has been designed:

```mermaid
flowchart TD
    Req[Incoming financial request with Idempotency-Key header] --> Lock[Start Savepoint and attempt INSERT into IdempotencyRecord]

    Lock -->|Success: key is new| Exec[Execute business logic and financial calculations]
    Exec --> Complete[Store output response and status COMPLETED]
    Complete --> Res[Return response to user]

    Lock -->|Uniqueness error: key already recorded| CheckState{What is the status of the existing record?}

    CheckState -->|COMPLETED| Replay[Instantly replay the stored response without re-executing logic]
    CheckState -->|IN_PROGRESS and still valid| Reject[Reject request with 409 error - Request In Progress]
    CheckState -->|IN_PROGRESS but expired Stale| Claim[Reclaim the expired record and execute the work]

    Replay --> Res
    Reject --> Err[Error to user]
    Claim --> Exec
```

---

## 13. Safety Nets and Periodic Reconciliation Workers

The system is equipped with scheduled Celery Beat jobs to contain exceptions and unexpected infrastructure errors:

```mermaid
graph LR
    subgraph "Safety Nets & Periodic Workers"
        J1["process_stuck_invoices"] -->|Check paid but unprocessed invoices| T1["Re-queue buy/deposit tasks"]
        J2["process_stuck_withdrawals"] -->|Check withdrawals stuck due to broker outage| T2["Re-queue process_withdrawal_requests"]
        J3["inquiry_processed_withdrawals"] -->|Periodic inquiry of Paya settlements| T3["Reconciliation with Vandar"]
        J4["check_cards_ownership"] -->|Batch inquiry of bank cards| T4["Batch Inquiry via NeginHub"]
        J5["update_currency_prices"] -->|Fetch real-time gold price and log| T5["CurrencyPriceLog updates"]
    end
```
