# E-commerce API — Interview Cheatsheet

A complete technical reference for the E-commerce API project. Covers concepts, patterns, commands, and likely interview questions.

---

## Resume Blurb (copy-paste)

> **E-commerce API** — Built a containerized RESTful e-commerce backend with FastAPI, PostgreSQL, and Redis. Implemented JWT auth with role-based admin access control, atomic stock management using row-level locking and all-or-nothing transactions, Stripe test-mode payments via PaymentIntents with signature-verified webhooks (including failed-payment restocking), a read-through Redis cache with write-invalidation, verified-purchase product reviews, and async order confirmations via background tasks. Orchestrated API + Postgres + Redis with Docker Compose and added a pytest suite running in GitHub Actions CI.

**Skills line for resume:**
> Python, FastAPI, PostgreSQL, Redis, SQLAlchemy, Alembic, Docker & Docker Compose, Stripe API (PaymentIntents + webhooks), JWT/OAuth2, RBAC, Pydantic v2, pytest, GitHub Actions CI, REST API design, transactions & concurrency control.

---

## 1. Tech Stack & Why

| Tool | Role | Why chosen |
|------|------|-----------|
| **FastAPI** | Web framework | Async-ready, auto-validation, auto Swagger docs, type hints |
| **Uvicorn** | ASGI server | Runs FastAPI apps |
| **SQLAlchemy** | ORM | Python classes + relationships instead of raw SQL |
| **PostgreSQL** | Database | Production-grade, concurrent, supports row locking (`SELECT ... FOR UPDATE`) |
| **Alembic** | Migrations | Version control for DB schema |
| **Redis** | Cache | In-memory store in front of Postgres for hot reads |
| **Stripe** | Payments | Industry-standard; test mode for safe development |
| **Pydantic v2** | Validation | Request/response validation + JSON serialization (handles Decimal/datetime) |
| **python-jose** | JWT | Stateless auth tokens |
| **passlib[bcrypt]** | Hashing | One-way password hashing (`bcrypt==4.0.1` pinned) |
| **Docker Compose** | Orchestration | Runs API + Postgres + Redis together |
| **pytest + httpx** | Testing | Isolated DB fixtures, mocked external services |
| **GitHub Actions** | CI | Runs tests on every push |

---

## 2. Project Structure

```
EcommerceAPI/
├── main.py            # Creates app, includes routers, /health
├── config.py          # Settings from env (pydantic-settings)
├── database.py        # Engine, SessionLocal, Base, get_db
├── models.py          # Users, Products, Order, OrderItem, Review
├── schemas.py         # Pydantic request/response shapes
├── security.py        # Hashing, JWT, get_current_user, require_admin
├── cache.py           # Redis client
├── notifications.py   # Background-task order confirmation
├── routers/           # users, products, orders, reviews, payments
├── alembic/           # Migrations
├── tests/             # conftest fixtures + test suites
├── Dockerfile
└── docker-compose.yml # API + Postgres + Redis
```

---

## 3. Data Model

- **Users** — `id, email (unique), hashed_password, role (default "user"), created_at`; `orders`, `reviews` relationships.
- **Products** — `id, name, description, price Numeric(10,2), stock, created_at`.
- **Order** — `id, user_id FK, status (enum: pending/paid/shipped/cancelled), total_amount Numeric(10,2), payment_intent_id, created_at`; `items` (cascade delete-orphan).
- **OrderItem** — `id, order_id FK, product_id FK, quantity, price_at_purchase Numeric(10,2)` (price **snapshot**).
- **Review** — `id, user_id FK, product_id FK, rating, comment, created_at`; **composite** `UniqueConstraint(user_id, product_id)`.

**Why `price_at_purchase`?** Order history must stay accurate even if the product's current price changes later — snapshot it, never join live to the product price.

**Why `Numeric`/`Decimal` for money?** Floats cause rounding errors; `Numeric(10,2)` / `Decimal` is exact.

---

## 4. Key Concepts (interview ammo)

### Admin RBAC
`require_admin` is a dependency that wraps `get_current_user` and raises **403** if `role != "admin"`. Public reads stay open; writes require the admin dependency.

```python
def require_admin(current_user: models.Users = Depends(get_current_user)) -> models.Users:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

### Atomic stock management (the hardest part)
When creating an order with multiple items, stock must be decremented **all-or-nothing** and protected against concurrent buyers:

- `with_for_update()` acquires a **row-level lock** on each product so two simultaneous orders can't oversell.
- Insufficient stock → **409 Conflict**.
- Everything happens in a **single commit**; any error triggers `rollback()` → the whole order fails cleanly (no partial stock decrement).

```python
product = db.query(models.Products).filter(
    models.Products.id == item.product_id
).with_for_update().first()
if product.stock < item.quantity:
    raise HTTPException(409, detail="Insufficient stock")
product.stock -= item.quantity
```

### AuthN vs AuthZ (401 vs 403) + ownership
- **401 Unauthorized** = not authenticated (bad/missing token) — one reused `credentials_exception` with `WWW-Authenticate: Bearer`.
- **403 Forbidden** = authenticated but not allowed.
- **Ownership pattern:** check **404 first** (does it exist?), then **403** (is it yours?); admins bypass the ownership check.

### Redis read-through caching + invalidation
- **Read:** check Redis → hit returns cached JSON; miss queries Postgres, stores with `SETEX` (TTL 300s), returns.
- **Write:** create/update/delete **invalidates** affected keys (`products:{id}` + `products:all`).
- **Serialization:** use Pydantic (`model_dump_json` / `TypeAdapter`) — handles `Decimal` and `datetime` (plain `json.dumps` can't).
- **Fail-open:** all cache calls are wrapped in `try/except` → if Redis is down, the endpoint falls back to Postgres instead of erroring.
- **TTL as backstop:** even if an invalidation is missed, stale data self-heals at expiry.

### Stripe payments — PaymentIntent
- `POST /orders/{id}/pay` creates a `PaymentIntent` for the order.
- **Amount is in integer cents** — `int(total_amount * 100)` ($49.99 → 4999).
- `metadata={"order_id": order.id}` ties the payment back to the order for the webhook.
- Only `pending` orders are payable (guards against double-charging); the returned `client_secret` completes the payment.

### Stripe webhooks — confirmation
- `POST /payments/webhook` has **no JWT** — the security boundary is **signature verification**.
- `stripe.Webhook.construct_event(payload, sig, webhook_secret)` verifies the request is genuinely from Stripe.
- Must read the **raw request body** (`await request.body()`) — verification hashes the exact bytes; reparsing breaks it.
- `payment_intent.succeeded` → order `paid`; `payment_intent.payment_failed` → order `cancelled` **and restock items**.
- **Idempotent:** a `pending`-status guard means a redelivered event won't double-process (no double restock).
- Return **2xx fast** so Stripe doesn't retry.

### Verified-purchase reviews
Before allowing a review, confirm the user actually bought the product — join `OrderItem` to `Order` filtering `user_id`, `status == paid`, and `product_id`. The join (`OrderItem.order_id == Order.id`) is essential; without it the query becomes a cross join and lets anyone review anything. One review per user per product is enforced by a composite DB `UniqueConstraint` (friendly **409** in the router).

### Background tasks
`BackgroundTasks` runs work **after** the response is returned (non-blocking). Used to "send" the order-confirmation after payment succeeds.
**Gotcha:** the `get_db` session closes after the response, so never pass an ORM object/session to the task — capture **primitive values** (email, order id) while the session is open and pass those, or you'll hit `DetachedInstanceError`.

---

## 5. Docker / Compose notes

- **Service-name networking:** the API reaches Postgres at `db:5432` and Redis at `redis:6379` — Compose service names are DNS hostnames. `localhost` inside a container refers to the container itself, not the host.
- **Healthchecks + `depends_on: condition: service_healthy`** make the API wait until Postgres/Redis are ready.
- **Named volume** (`pgdata`) persists Postgres data across restarts; Redis needs no volume (cache is rebuildable).
- **Migrations on startup:** the API service runs `alembic upgrade head && uvicorn ...`.
- **Config precedence:** compose `environment:` overrides `env_file:`, so the Postgres `DATABASE_URL` replaces the local SQLite one while `SECRET_KEY` still loads from `.env`.
- **`PYTHONUNBUFFERED=1`** so `print`/stdout isn't block-buffered in the container; prefer the uvicorn logger for app logs.

---

## 6. Testing & CI

- **Isolated DB:** `get_db` is overridden to a SQLite `test.db`; tables are created/dropped per test for clean isolation.
- **Fixtures:** `client`, `auth_headers` (register + login), `admin_headers` (promote to admin via direct DB write — `get_current_user` re-reads role per request), `db_session` (set up state like a `paid` order).
- **Mock external services:** `monkeypatch` swaps `stripe.PaymentIntent.create` / `stripe.Webhook.construct_event` — no network calls.
- **No Redis needed:** fail-open cache means tests pass without it.
- **CI:** GitHub Actions installs deps and runs `pytest` on every push/PR, with dummy env vars (tests mock Stripe + override the DB).

---

## 7. Common commands

```powershell
# Run the full stack
docker compose up --build

# Migrations
alembic revision --autogenerate -m "message"
alembic upgrade head

# Tests
pytest -v

# Stripe webhooks locally
stripe listen --events payment_intent.succeeded,payment_intent.payment_failed --forward-to localhost:8000/payments/webhook
stripe payment_intents confirm <intent_id> --payment-method pm_card_visa          # success
stripe payment_intents confirm <intent_id> --payment-method pm_card_chargeDeclined # failure
```

---

## 8. Likely interview questions

**Q: How do you prevent overselling stock under concurrent requests?**
Row-level locking with `SELECT ... FOR UPDATE` (`with_for_update()`) on each product, inside a single transaction. Concurrent orders for the same product serialize on the lock; insufficient stock raises 409 and the transaction rolls back so no partial decrement happens.

**Q: Why use a webhook instead of just checking the payment response?**
Payment completion is asynchronous and happens on Stripe's side (and client-side). The webhook is Stripe's authoritative, server-to-server confirmation — reliable even if the client disconnects. It's verified by signature, not by a logged-in user.

**Q: How do you keep the webhook secure and correct?**
Signature verification with `construct_event` over the raw body (no JWT), idempotent handling via a status guard so redelivered events don't double-process, and a fast 2xx response to avoid retries.

**Q: How does your cache stay consistent with the database?**
Read-through on reads; explicit invalidation of the affected keys on every write (including stock changes from orders and restocks from failed payments); a TTL backstop; and fail-open behavior so Redis never becomes a single point of failure.

**Q: Why store `price_at_purchase` and `payment_intent_id` on the order?**
`price_at_purchase` snapshots the price so historical orders stay accurate when prices change. `payment_intent_id` links the order to Stripe for reconciliation/idempotency.

**Q: What breaks if you pass an ORM object to a background task?**
The DB session is already closed by then, so accessing lazy-loaded attributes raises `DetachedInstanceError`. Pass primitive values captured before the response returns.

---

## 9. Hard-won lessons

- Pin `bcrypt==4.0.1` from the start.
- Pick **one** schema source of truth — never let `create_all` and Alembic both manage schema.
- Money = `Numeric`/`Decimal`, never `Float`.
- Enforce one-review-per-user-per-product with a **composite** unique constraint, not two separate ones.
- Always add the join condition — `db.query(A, B)` without it is a cross join.
- Stripe amounts are **integer cents**; always attach `metadata.order_id`.
- Webhook signature verification needs the **raw** body; catch both `ValueError` (bad payload) and `SignatureVerificationError` (bad signature) → 400.
- In Docker, `print` is block-buffered — use `PYTHONUNBUFFERED=1` or the uvicorn logger.
- Compose service names are the hostnames; `localhost` inside a container is the container.
