# AI PR Reviewer

Production-grade full-stack app that reviews GitHub pull requests with an LLM. When a PR is opened
or updated, the system fetches the diff, sends it to a configured LLM provider, posts inline review
comments on the PR, and records the review in a dashboard.

## Stack

| Layer       | Tech                                                                        |
| ----------- | --------------------------------------------------------------------------- |
| Frontend    | Next.js 14 (App Router), TypeScript, Tailwind CSS, NextAuth (GitHub OAuth)  |
| Backend     | FastAPI, Pydantic v2, httpx (async), ARQ (Redis queue)                      |
| LLM         | OpenRouter (default model: `qwen/qwen-2.5-coder-32b-instruct:free`) or mock |
| Database    | PostgreSQL via Prisma ORM (TS + Python clients from one schema)             |
| Cache/Queue | Redis                                                                       |
| Infra       | Docker Compose, GitHub Actions (CI + auto-deploy)                           |
| Deploy      | Vercel (frontend) + Railway (backend/worker) + Neon (Postgres) + Upstash (Redis) |

## Architecture

```
┌────────────┐  OAuth  ┌────────────────────┐
│ GitHub     │◄───────►│ Next.js (Vercel)   │
└────┬───────┘         │ - /dashboard       │
     │ webhook         │ - /reviews/[id]    │
     ▼                 │ - /settings        │
┌────────────────────┐ └────────┬───────────┘
│ FastAPI (Railway)  │          │ proxy
│ POST /webhooks/..  │◄─────────┘
│  1. verify HMAC    │
│  2. enqueue job    │          ┌───────────────┐
│  3. return 200     │────────► │ Redis (ARQ)   │
└────────────────────┘          └──────┬────────┘
                                       │ consume
                                       ▼
                        ┌────────────────────────────┐
                        │ ARQ worker (same image)    │
                        │  - fetch diff (httpx)      │
                        │  - truncate to 32k chars   │
                        │  - call ReviewProvider     │
                        │      • MockProvider        │
                        │      • OpenRouterProvider  │
                        │  - post inline review      │
                        │  - persist to Postgres     │
                        └────────────────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │ Postgres (Neon)  │
                              └──────────────────┘
```

The **webhook handler returns 200 immediately** after HMAC verification and enqueue — all heavy
work runs in the ARQ worker. Diffs over `DIFF_MAX_CHARS` (default 32 000) are truncated before
being sent to the LLM. LLM JSON parse failures are retried up to `LLM_MAX_RETRIES` times with a
strict-output reminder appended.

## Repository layout

```
pr-reviewer/
├── prisma/schema.prisma          # single source of truth for DB (TS + Python clients)
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app factory + lifespan
│   │   ├── config.py             # Pydantic Settings
│   │   ├── db.py                 # Prisma client lifecycle
│   │   ├── routers/              # webhooks / reviews / repositories / users
│   │   ├── services/
│   │   │   ├── github.py         # async httpx GitHub client
│   │   │   └── review/
│   │   │       ├── base.py       # ReviewProvider ABC + prompt
│   │   │       ├── mock.py       # offline deterministic provider
│   │   │       ├── openrouter.py # OpenRouter provider (retry + JSON extraction)
│   │   │       └── schema.py     # Pydantic output schema
│   │   ├── queue/                # ARQ settings + process_pr_event task
│   │   └── utils/                # HMAC verify + diff truncation
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/auth/[...nextauth]/    # NextAuth handler
│   │   │   ├── api/repositories/[id]/...  # proxy routes to backend
│   │   │   ├── dashboard/page.tsx         # list + filters
│   │   │   ├── reviews/[id]/page.tsx      # full review detail
│   │   │   └── settings/page.tsx          # connect/disconnect repos
│   │   ├── components/                     # ScoreBadge, AssessmentBadge, SeverityBadge, Nav
│   │   └── lib/                            # auth.ts, api.ts, prisma.ts, cn.ts
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── .github/workflows/              # ci.yml + deploy.yml
```

## Local setup

### 1. Prereqs

- Docker + Docker Compose
- Node 20+ and Python 3.12+ (only for running outside Docker)
- A GitHub OAuth App (Settings → Developer settings → OAuth Apps → New)
  - Homepage URL: `http://localhost:3000`
  - Callback URL: `http://localhost:3000/api/auth/callback/github`
- (Optional) An [OpenRouter](https://openrouter.ai/keys) API key. Without one, the app runs with
  `REVIEW_PROVIDER=mock` and returns deterministic placeholder reviews.

### 2. Env

```bash
cp .env.example .env
# Fill in: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, NEXTAUTH_SECRET (openssl rand -base64 32),
#         GITHUB_WEBHOOK_SECRET (any random string), OPENROUTER_API_KEY (optional)
```

### 3. Run with Docker

```bash
docker compose up --build
# postgres :5432   redis :6379   backend :8000   worker (no port)   frontend :3000
```

First run: apply Prisma migrations.

```bash
# From host (node required)
cd frontend
npx prisma migrate deploy --schema=../prisma/schema.prisma
```

Visit `http://localhost:3000`.

### 4. Exposing the webhook locally

GitHub needs a public HTTPS URL to deliver webhooks. Use ngrok:

```bash
ngrok http 8000
# copy https://<id>.ngrok-free.app and set in .env:
# PUBLIC_WEBHOOK_URL=https://<id>.ngrok-free.app/webhooks/github
# restart backend so it uses the new URL when registering hooks
```

In the app's Settings page, click **Connect** on a repo — the backend registers a webhook pointing
at `PUBLIC_WEBHOOK_URL` with `GITHUB_WEBHOOK_SECRET` as the HMAC secret.

## Environment variables

| Variable                 | Required     | Notes                                                     |
| ------------------------ | ------------ | --------------------------------------------------------- |
| `ANTHROPIC_API_KEY`      | no           | reserved; not used today (provider is OpenRouter or mock) |
| `REVIEW_PROVIDER`        | yes          | `mock` (default) or `openrouter`                          |
| `OPENROUTER_API_KEY`     | if provider  | needed when `REVIEW_PROVIDER=openrouter`                  |
| `OPENROUTER_MODEL`       | no           | default `qwen/qwen-2.5-coder-32b-instruct:free`           |
| `OPENROUTER_BASE_URL`    | no           | default `https://openrouter.ai/api/v1`                    |
| `GITHUB_CLIENT_ID`       | yes          | OAuth app                                                 |
| `GITHUB_CLIENT_SECRET`   | yes          | OAuth app                                                 |
| `GITHUB_WEBHOOK_SECRET`  | yes          | HMAC secret for webhook signature                         |
| `DATABASE_URL`           | yes          | Postgres URL                                              |
| `REDIS_URL`              | yes          | Redis URL                                                 |
| `NEXTAUTH_SECRET`        | yes          | `openssl rand -base64 32`                                 |
| `NEXTAUTH_URL`           | yes          | e.g. `http://localhost:3000`                              |
| `BACKEND_URL`            | yes (FE)     | Next.js → FastAPI                                         |
| `PUBLIC_WEBHOOK_URL`     | yes          | GitHub-reachable URL of `/webhooks/github`                |
| `DIFF_MAX_CHARS`         | no           | default 32 000                                            |

## Deployment

Connect your GitHub repo to:

- **Vercel** → import the `frontend/` directory. Set env vars (`BACKEND_URL`, `NEXTAUTH_SECRET`,
  `GITHUB_CLIENT_ID/SECRET`, `DATABASE_URL`, `NEXTAUTH_URL`). Vercel auto-deploys on push to `main`.
- **Railway** → new project from repo. Add services:
  - `backend` — uses `backend/Dockerfile`, command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - `worker` — same image, command `arq app.queue.settings.WorkerSettings`
  - Attach Neon or Railway Postgres + Upstash or Railway Redis plugins. Inject `DATABASE_URL` and
    `REDIS_URL`.
- Set `PUBLIC_WEBHOOK_URL` to `https://<backend>.up.railway.app/webhooks/github`.
- Update your GitHub OAuth callback URL to the Vercel domain.

### GitHub Actions

- **`ci.yml`** — runs on every push/PR to `main`. Backend lint+tests, frontend lint+typecheck+build.
- **`deploy.yml`** — runs on push to `main`. Enabled by setting repo variables
  `ENABLE_VERCEL_DEPLOY=true` and/or `ENABLE_RAILWAY_DEPLOY=true`, plus secrets `VERCEL_TOKEN` and
  `RAILWAY_TOKEN`. Vercel and Railway also auto-deploy via their native GitHub integrations — the
  workflow is included for reproducibility.

## How reviews work

1. Developer opens PR. GitHub sends `pull_request` webhook.
2. FastAPI verifies `X-Hub-Signature-256` HMAC, enqueues an ARQ job keyed by
   `pr:<repo>:<pr>:<sha>` (idempotent per commit), returns 200.
3. Worker fetches the diff (`Accept: application/vnd.github.v3.diff`), truncates to
   `DIFF_MAX_CHARS`, calls the configured `ReviewProvider`.
4. Provider returns JSON validated against `ReviewOutput`:
   - `summary`, `overall_assessment` (`approve` / `request_changes` / `comment`), `score` (1–10)
   - `inline_comments[]` (file_path, line_number, severity, comment, suggestion)
   - `security_issues[]`, `performance_issues[]`, `positive_highlights[]`
5. Worker maps assessment → GitHub review event (`APPROVE` / `REQUEST_CHANGES` / `COMMENT`), posts
   a single review with inline `comments`, stores the full JSON in Postgres.
6. Dashboard reads from Postgres via FastAPI `/reviews`. Detail page renders everything.

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest            # HMAC + diff truncation + mock provider

cd ../frontend
npm install
npm run lint
npm run typecheck
```

## Security notes

- Webhook HMAC is verified with `hmac.compare_digest` (constant-time).
- GitHub OAuth access tokens are stored server-side only (never exposed to the browser).
- Settings page mutates via Next.js server route handlers that re-attach the authenticated user ID;
  the backend does not trust client-supplied `user_id` blindly on connect/disconnect — it checks
  repo ownership.
- CORS on the backend is restricted to `FRONTEND_ORIGIN`.

## License

MIT
