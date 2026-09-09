# Backend Learning — Progress & Context Handoff

> **Purpose of this file:** portable record of my backend learning journey so context survives a machine move.
> **On a new machine:** open this folder in VS Code and tell Copilot *"Read LEARNING_PROGRESS.md and continue where I left off."*

---

## Who / Goal
- Knows Python; learning backend from scratch, **1 hour/day**, goal: **job-ready**.
- OS: Windows (PowerShell). Editor: VS Code + GitHub Copilot.
- Learning format: daily **Learn + Build** lessons, one concept per day.
- End goal: **3 deployed portfolio projects** on GitHub with READMEs + interview cheatsheets.

## Project folders (under `Documents\Personal\`)
| Project | Folder | venv | Status |
|---|---|---|---|
| 1. Task Manager API | `Task Manager API` | `taskenv` | ✅ COMPLETE + deployed (Railway) |
| 2. Blog Platform API | `Blog Platform API` | `blogenv` | ✅ COMPLETE + deployed (Railway) |
| 3. E-commerce API | `Ecommerce API` | `shopenv` | 🔧 IN PROGRESS (~Day 44) |

---

## Standard stack (all projects)
FastAPI + uvicorn · SQLAlchemy · Alembic · PostgreSQL (SQLite for local dev) · Pydantic v2 + pydantic-settings · JWT (python-jose) · passlib[bcrypt] with **`bcrypt==4.0.1` pinned** · python-multipart · pytest + httpx · deployed on Railway.

## Established architecture patterns (reused every project)
- `models.py` (SQLAlchemy) vs `schemas.py` (Pydantic) separation.
- `Depends(get_db)` dependency injection (yield/finally close).
- **JWT auth:** `create_access_token(data)` → `OAuth2PasswordBearer(tokenUrl="users/login")` → `get_current_user` decodes JWT, reads `sub`, loads user, one reused 401 `credentials_exception` (with `WWW-Authenticate: Bearer`).
- **RBAC (Project 3):** `require_admin(current_user=Depends(get_current_user))` → 403 if `role != "admin"`.
- **Ownership authZ:** 404 check first, then 403 if `resource.user_id != current_user.id` (admins bypass).
- **PATCH:** `model_dump(exclude_unset=True)` + `setattr` loop.
- **Money:** `Numeric(10,2)` / `Decimal`, **never Float**.
- **Nested response schemas** to hide sensitive fields (e.g. `AuthorResponse` = id+email only).
- **Alembic env.py:** `sys.path` append + `from database import Base` + `import models` (registers tables) + `target_metadata = Base.metadata` + `config.set_main_option("sqlalchemy.url", settings.database_url)`.
- **Deploy:** Procfile `release: alembic upgrade head` + `web: uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Tests:** isolated SQLite `test.db` via `app.dependency_overrides[get_db]`, `client` fixture, `auth_headers` fixture (registers+logs in, returns Bearer header).

---

## PROJECT 1 — Task Manager API ✅
CRUD REST API, SQLAlchemy → PostgreSQL, Alembic, pytest (~12 tests), deployed to Railway. README + INTERVIEW_CHEATSHEET.md done.

## PROJECT 2 — Blog Platform API ✅
JWT auth + bcrypt, User→Posts relationship, ownership authorization (401 vs 403), Alembic, Postgres on Railway, pytest suite (incl. two-user 403 test), deployed. README + INTERVIEW_CHEATSHEET.md done.
- **Note:** Comments feature was built then **intentionally removed** (Day 29) — out of scope, do not restore.

## PROJECT 3 — E-commerce API 🔧 (current)
**Scope (locked Day 33):** Products CRUD (admin), Cart+Orders, stock management with transactions, Stripe test-mode payments, product reviews/ratings, Admin RBAC. Deploy: **local Docker only** for now.

**Model naming quirk:** the user model class is `Users` (plural), product model is `Products` (plural).

### Files so far
- `models.py`: `OrderStatus` enum (pending/paid/shipped/cancelled); `Users` (id, email, hashed_password, `role` default "user", created_at, `orders` rel); `Products` (id, name, description, `price` Numeric(10,2), stock, created_at); `Order` (id, user_id FK, status enum, total_amount Numeric, created_at, `user`+`items` rels, cascade delete-orphan); `OrderItem` (table `orderitems`: id, order_id FK, product_id FK, quantity, price_at_purchase Numeric; `order`+`product` rels).
- `schemas.py`: User/Token, Product (Create/Update/Response), Order (`OrderItemCreate`, `OrderCreate`, `OrderItemResponse`, `OrderResponse`).
- `security.py`: JWT auth ported from P2 + `require_admin`.
- `routers/users.py`: register / login / me (+ temp `/admin-check`).
- `routers/products.py`: public GET list/detail; admin-only POST/PATCH/DELETE.
- `routers/orders.py`: `POST /orders` (auth; validates stock with `with_for_update()` row lock, 409 on insufficient, decrements stock, atomic single-commit with rollback + 500); `GET /orders` (own only); `GET /orders/{id}` (404→403 ownership, admin bypass).
- `alembic/`: initial migration `create users and products tables` exists.

---

## Day-by-day log

### Project 1 (Task Manager API)
- **D1–7:** FastAPI basics, path/query params, HTTPException 404, Pydantic Create/Response/Update models, PUT/DELETE/PATCH full CRUD, TaskStatus Enum, `model_dump(exclude_unset=True)`. Fixed datetime default bug (`Field(default_factory=...)`).
- **D8–10:** SQLAlchemy — database.py + models.py, DBeaver, wired all CRUD to real DB via `Depends(get_db)`, removed fake in-memory store.
- **D11–13:** Alembic init + first migration; added `due_date` column via migration; refactored into schemas.py + routers/tasks.py + thin main.py.
- **D14–16:** pydantic-settings + .env + config.py; switched to PostgreSQL (psycopg2-binary); Railway cloud Postgres.
- **D17–18:** pytest + httpx, isolated SQLite test.db, ~12 tests.
- **D19–21:** requirements.txt + README; Procfile + Railway deploy; **PROJECT 1 COMPLETE**; INTERVIEW_CHEATSHEET.md.

### Project 2 (Blog Platform API)
- **D22:** init; User model; passlib bcrypt hashing; register. *Bugs: 204→409 for duplicate; pinned `bcrypt==4.0.1`.*
- **D23:** JWT login (`OAuth2PasswordRequestForm`, form field must be `username`), `create_access_token`, SECRET_KEY via `secrets.token_hex(32)`.
- **D24:** protected routes — `get_current_user`, `/users/me`.
- **D25:** Posts + User↔Post relationships; nested `AuthorResponse`.
- **D26:** authorization — PATCH/DELETE with 404→403 ownership. authN(401) vs authZ(403).
- **D27:** Comments (later removed D29).
- **D28:** Alembic for P2.
- **D29:** Postgres on Railway; removed comments feature intentionally.
- **D30:** pytest suite + `auth_headers` fixture + two-user 403 test. *Bugs: test_ file naming, `sqlite:///./test.db` slashes, `username` form field, nested same-quote f-string on Py<3.12, author dict assertion, stale response var.*
- **D31:** deploy P2. *Bug: 502 from PowerShell writing UTF-16 requirements.txt — fix via cmd.exe or `[System.IO.File]::WriteAllLines`.*
- **D32:** **PROJECT 2 COMPLETE** — README + INTERVIEW_CHEATSHEET.md.

### Project 3 (E-commerce API)
- **D33:** scope locked; 25-day schedule drafted.
- **D34:** init — folder, `shopenv`, full stack (bcrypt pinned), auth ported from P2, fresh SECRET_KEY.
- **D35:** admin role + RBAC — `role` column (default "user"), `require_admin` dependency, manual SQL admin promotion.
- **D36:** Product model (`Numeric(10,2)` price, not Float) + schemas.
- **D37:** Products router (admin write, public read).
- **D38:** Alembic init + first migration (users+products).
- **D39:** design day — many-to-many via association object; decided Enum status + denormalized total_amount + `price_at_purchase` snapshot.
- **D40:** built `Order` + `OrderItem` models + relationships.
- **D41:** Order schemas + `POST /orders` (happy path). *Note: temporarily re-enabled `create_all` for testing → caused schema drift, fixed D44.*
- **D42:** stock validation + atomic transaction (hardest day) — `with_for_update()` row lock, 409 on insufficient stock, decrement, single-commit all-or-nothing, try/except rollback + 500.
- **D43:** `GET /orders` (own only) + `GET /orders/{id}` (404→403 ownership, admin bypass).
- **D44 (in progress):** fix schema drift — comment out `create_all`, delete shop.db, `alembic upgrade head`, autogenerate migration for orders+orderitems, upgrade, retest full flow.

---

## Remaining Project 3 schedule (Days 45–57)
- **D45:** Review model (user + product + rating + comment)
- **D46:** Reviews router (POST, GET product reviews, one-per-user rule)
- **D47:** learn Docker, write Dockerfile for API
- **D48:** docker-compose.yml (API + Postgres)
- **D49:** add Redis to compose
- **D50:** cache product catalog (Redis read-through + invalidate on write)
- **D51:** learn Stripe test mode, keys + config
- **D52:** `POST /orders/{id}/pay` → Stripe PaymentIntent (test mode)
- **D53:** payment confirmation → mark order paid
- **D54:** background tasks — async order confirmation (FastAPI BackgroundTasks)
- **D55:** pytest suite (products/orders/reviews, mock Stripe)
- **D56:** GitHub Actions — run tests on push
- **D57:** CI/CD polish + README + INTERVIEW_CHEATSHEET → **PROJECT 3 COMPLETE**
- (buffer days expected for debugging)

---

## Hard-won lessons (don't repeat these)
- **Pin `bcrypt==4.0.1`** from project start (else "password cannot be longer than 72 bytes").
- **PowerShell writes UTF-16** for `pip freeze > requirements.txt` → breaks Linux deploys. Use `cmd.exe` or `[System.IO.File]::WriteAllLines(...)`. VS Code hides this (auto-decodes for display).
- **OAuth2PasswordRequestForm** login form field must be literally `username`, not `email`.
- **HTTP 204** must not return a body (don't use it for error responses).
- **Nested same-quote f-strings** only work on Python 3.12+.
- **`sqlite:///./name.db`** needs the `./` (three slashes + dot).
- **Schema drift:** never let `create_all` and Alembic both manage schema — pick one source of truth.
- **Money = `Numeric`/`Decimal`**, never Float.
- Snapshot `price_at_purchase` on orders — don't join live to current product price (history must stay accurate).

---

## Setup on a new machine (per project)
```powershell
git clone <repo-url>
cd "<project folder>"
python -m venv <envname>          # taskenv / blogenv / shopenv
.\<envname>\Scripts\Activate
pip install -r requirements.txt
# recreate .env from .env.example (SECRET_KEY, DATABASE_URL)
alembic upgrade head
uvicorn main:app --reload
```
> `.env`, `*.db`, and the venv are gitignored — recreate them locally. If `Ecommerce API` has no `requirements.txt` yet, generate one via cmd.exe: `pip freeze > requirements.txt`.

---

## Open follow-up
- Confirm the exposed Railway Postgres password (Day 21, Project 1) was rotated on the Railway dashboard.
