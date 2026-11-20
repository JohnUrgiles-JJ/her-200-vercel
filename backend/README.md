# ConnectHER backend

ConnectHER connects women and girls breaking into STEM with mentors who've lived the same path. A student asks a question, AI matches it to the 3 best mentors, and they're notified live (WebSocket) and by email.
This is the Django REST + Channels backend: token auth, mentor profiles, AI matching with a keyword fallback, a mentor inbox and answers.

Stack: Django 6.1, Django REST Framework, Channels + Daphne (ASGI), SQLite locally / Postgres on Railway, Anthropic or OpenAI for matching.

---

## Setup

Python 3.12. All commands run from `backend/`.

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed
python manage.py runserver
```
If PowerShell blocks `activate`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**macOS / Linux / Git Bash**
```bash
python3 -m venv venv
source venv/bin/activate          # Git Bash on Windows: source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed
python manage.py runserver
```

The server runs at http://127.0.0.1:8000. `runserver` uses **Daphne (ASGI)**, so HTTP and WebSockets share port 8000. The first lines it prints say how matching will work, e.g.:
```
WARNING core.matching: No LLM key set: LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty. Using keyword fallback for matching.
```

- Interactive API docs: http://127.0.0.1:8000/api/docs/ (click **Authorize** and enter `Token <key>`).
- Health check: http://127.0.0.1:8000/api/health/ returns `{"status": "ok", "db": true}`.
- Admin: http://127.0.0.1:8000/admin/. Create a user with `python manage.py createsuperuser`.

### Useful commands
| Command | What it does |
|---|---|
| `python manage.py seed` | Creates or updates the 14 demo users. Safe to re-run; tokens are kept. Prints a table of logins and tokens. |
| `python manage.py seed --reset` | Deletes **all** questions, matches and answers first, then seeds. Run it right before a demo. |
| `python scripts/demo_check.py` | End-to-end check of the demo flow against the running server (see [Demo check](#demo-check)). |
| `python scripts/ws_listen.py <token>` | Prints every WebSocket event a user receives. |
| `python manage.py test_email you@example.com` | Sends one sample mentor email to check the email setup. |
| `python manage.py test core` | Runs the test suite (no network or API keys needed). |

---

## Demo accounts

Created by `python manage.py seed`. The password is **`demo1234`** for every account. All are fictional.

| Login email | Name | Role | Headline @ Company |
|---|---|---|---|
| student1@demo.com | Maria Lopez | mentee | — |
| student2@demo.com | Aisha Rahman | mentee | — |
| maya@demo.com | Maya Chen | mentor | UX Designer @ Figma |
| priya@demo.com | Priya Nair | mentor | Data Scientist @ Spotify |
| sofia@demo.com | Sofia Martinez | mentor | Software Engineer @ Microsoft |
| amara@demo.com | Amara Okafor | mentor | Cybersecurity Analyst @ JPMorgan Chase |
| elena@demo.com | Elena Rossi | mentor | Product Manager @ Etsy |
| jasmine@demo.com | Jasmine Lee | mentor | Front-End Engineer @ Squarespace |
| fatima@demo.com | Fatima Hassan | mentor | AI/ML Engineer @ IBM |
| grace@demo.com | Grace Kim | mentor | Health Tech Analyst @ Mount Sinai |
| valeria@demo.com | Valeria Cruz | mentor | Cloud Engineer @ Amazon Web Services |
| nadia@demo.com | Nadia Brooks | mentor | Quality Engineer @ Bloomberg |
| rosa@demo.com | Rosa Delgado | mentor | IT Support Specialist @ NYC Health + Hospitals |
| hannah@demo.com | Hannah Wright | mentor | Technology Strategy Associate @ BNY |

**Demo flow:** log in as `student1@demo.com` and ask *"How do I break into UX design without a design degree?"*. **Maya** is matched #1. Log in as `maya@demo.com` in an incognito window: the question appears in her inbox live. Her answer appears live for student1.

---

## API

Base URL `http://localhost:8000/api` (production: `https://<name>.up.railway.app/api`).
Every endpoint except signup and login needs the header **`Authorization: Token <key>`**. The word is `Token`, not `Bearer`.
Errors under `/api/` are always JSON, 404s and 500s included: `{"detail": "Human readable message"}`, or DRF's `{"field": ["message"]}` for some 400 validation errors.

| # | Method | Path | Who | Body | Success |
|---|---|---|---|---|---|
| 1 | POST | `/signup/` | anyone | `{email, password, full_name, role}` | **201** `{token, user}` |
| 2 | POST | `/login/` | anyone | `{email, password}` | **200** `{token, user}` |
| 3 | GET | `/me/` | any user | — | **200** `User` |
| 4 | GET | `/mentor-profile/` | mentor | — | **200** `MentorProfile` or **404** |
| 5 | POST / PUT | `/mentor-profile/` | mentor | `MentorProfile` | **200** `MentorProfile` (create or update) |
| 6 | GET | `/mentors/` | any user | — | **200** `[{mentor_id, name, ...MentorProfile}]` |
| 7 | POST | `/questions/` | mentee | `{text}` | **201** `Question` with 3 matches |
| 8 | GET | `/questions/mine/` | mentee | — | **200** `Question[]`, newest first |
| 9 | GET | `/inbox/` | mentor | — (optional `?status=sent\|answered`) | **200** `InboxItem[]`, newest first |
| 10 | POST | `/matches/<match_id>/answer/` | mentor who owns the match | `{text}` | **201** `Answer` |

Not in the contract, but available: `GET /health/` (public, for Railway).

### Shapes
```jsonc
// User
{ "id": 1, "email": "maria@demo.com", "full_name": "Maria Lopez", "role": "mentee", "has_mentor_profile": false }

// MentorProfile  (fields and open_to are comma-separated strings; a list of strings is also accepted on input)
{ "headline": "UX Designer", "company": "Figma", "fields": "UX, Figma, user research",
  "open_to": "career switching, portfolios", "bio": "Switched from teaching to UX...", "experience_years": 6 }

// Answer
{ "id": 1, "text": "Start with 3 case studies...", "created_at": "2026-11-20T14:05:00Z" }

// Match (inside a Question; ordered by rank; mentor_id is the mentor's User id; status "sent" | "answered")
{ "match_id": 12, "mentor_id": 3, "name": "Maya Chen", "headline": "UX Designer", "company": "Figma",
  "reason": "Switched into UX from a non-design background", "rank": 1, "status": "sent", "answers": [] }

// Question
{ "id": 5, "text": "How do I break into UX design without a design degree?",
  "created_at": "2026-11-20T14:02:00Z", "matches": [ /* Match */ ] }

// InboxItem (mentor view; mentee_name = first name + last initial; created_at = the question's)
{ "match_id": 12, "question_id": 5, "question_text": "How do I break into UX...", "mentee_name": "Maria L.",
  "reason": "Switched into UX from a non-design background", "status": "sent",
  "created_at": "2026-11-20T14:02:00Z", "answers": [] }
```

### Validation and errors
| Case | Response |
|---|---|
| `role` not `mentor`/`mentee`, password under 6 characters, bad email | 400 `{"field": ["..."]}` |
| Email already registered (case-insensitive) | 400 `{"detail": "An account with this email already exists."}` |
| Wrong email or password | 400 `{"detail": "Invalid email or password."}` |
| Question text not 10–1000 characters after trimming | 400 `{"detail": "Question must be between 10 and 1000 characters."}` |
| Answer text empty after trimming / over 3000 characters | 400 `{"detail": "Answer text is required."}` / `{"detail": "Answer must be at most 3000 characters."}` |
| Missing or bad token | 401 `{"detail": "..."}` |
| Wrong role (e.g. a mentor asking) | 403 `{"detail": "Only mentees can ask questions."}` / `{"detail": "Only mentors can do this."}` |
| Answering another mentor's match, or a match that doesn't exist | 404 `{"detail": "Not found."}` |
| Unknown `/api/` URL | 404 `{"detail": "Not found."}` |
| Any server bug | 500 `{"detail": "Something went wrong on our side. Please try again."}` (traceback in the server log) |

Trailing slashes are optional: `POST /api/questions` works the same as `POST /api/questions/`.

---

## WebSocket (live notifications)

```
ws://localhost:8000/ws/notifications/?token=<key>             # local
wss://<name>.up.railway.app/ws/notifications/?token=<key>     # production (wss, not ws)
```
- `<key>` is the same token as the REST API (from `/login/`, `/signup/`, or the `seed` table). Browsers can't set headers on WebSockets, so it goes in the URL.
- A missing or invalid token: the server accepts, then **closes with code `4401`**. Don't auto-reconnect on 4401; send the user to log in.
- The server only sends. It ignores client messages except `{"event": "ping"}`, which gets `{"event": "pong"}` back.
- Connections are accepted from any origin (the token is the check), so the Vite dev server and the deployed frontend both work.
- Events sent while a client is disconnected are **not** replayed. After a reconnect, refetch `/inbox/` or `/questions/mine/`.

**Events**
```jsonc
// to each matched mentor, right after a question is asked
{ "event": "new_question", "match_id": 12, "question_id": 5,
  "question": "How do I break into UX...", "reason": "Switched into UX...", "mentee_name": "Maria L." }

// to the mentee, right after a mentor answers
{ "event": "new_answer", "question_id": 5, "match_id": 12,
  "mentor_name": "Maya Chen", "text": "Start with 3 case studies..." }
```

---

## Configuration (`.env`)

`.env` is git-ignored. `.env.example` lists every variable. Restart the server after editing `.env`.

### Switching the LLM provider
```
LLM_PROVIDER=anthropic              # anthropic | openai | none
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-5-5    # default if blank
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini            # default if blank
```
- `none`, or a provider with an empty key, means **keyword fallback only**. It works offline and ranks Maya #1 for the UX demo question.
- The LLM call has a **10 s timeout** and no retries. On any error (timeout, bad key, network, unparseable output) the server logs a warning and uses the keyword fallback, so asking a question never fails because of the LLM.
- The startup log line says which mode is active.

### Enabling Gmail
Emails print in the server terminal by default (the console backend). To send real email:
1. On the Google account that will send (a team Gmail is best), turn on **2-Step Verification** (Google Account → Security).
2. Create an **App Password**: Google Account → Security → *App passwords* (https://myaccount.google.com/apppasswords). Copy the 16 letters.
3. In `.env`:
   ```
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST_USER=yourteam@gmail.com
   EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop     # the App Password; spaces are fine
   ```
4. Restart and check: `python manage.py test_email you@example.com`. It prints the reason and a hint if anything is wrong.
5. Optional, for the demo: send Maya's notifications to a teammate's real inbox. Login stays `maya@demo.com`:
   ```powershell
   $env:SEED_REAL_EMAILS = "maya@demo.com=teammate@gmail.com"; python manage.py seed
   ```

Emails go out on a background thread, so they never slow down `POST /questions/`.

---

## Demo check

With the server running in another terminal:
```powershell
python scripts/demo_check.py
```
It runs `seed --reset`, logs in as student1 and Maya, opens both WebSockets with the frontend's `Origin`, asks the UX question, and checks: 3 matches with Maya among them, Maya's `new_question` within 5 s, Maya's answer, student1's `new_answer` within 5 s, and the answer in `/questions/mine/`. Each step prints PASS / FAIL / WARN, and the run ends with `READY FOR THE DEMO` or `NOT READY` (exit code 1).
- `--no-reset` keeps existing data.
- `--url https://<name>.up.railway.app` checks production. It never resets a remote server.
- `--origin https://your-frontend.app` sets the Origin for the CORS and WebSocket checks.

The check leaves one answered question behind, so run `python manage.py seed --reset` once more right before the pitch.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Browser: *"blocked by CORS policy"* | The frontend origin isn't allowed | `http://localhost:5173` and `http://127.0.0.1:5173` are allowed by default. For another origin, set `FRONTEND_URL` (scheme + host, no path) or add it to `EXTRA_CORS_ORIGINS`, then restart. Check with `curl -i -X OPTIONS http://127.0.0.1:8000/api/questions/ -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: POST"`, which should show `Access-Control-Allow-Origin`. |
| CORS error only when something fails | It's usually a real error, not CORS | Look at the server log. Error responses carry CORS headers too, so the browser should show the real status. |
| **401** on every request | Wrong header | It must be exactly `Authorization: Token <key>`: the word `Token`, a space, the key. Not `Bearer`. Re-login if the DB was recreated (tokens change). |
| 403 "Only mentees can ask questions." | Logged in as the wrong role | Ask as `student1@demo.com`; answer as a mentor. |
| WebSocket closes right away with **4401** | Missing or invalid `?token=` | Use the token from `/login/`. Tokens change if `db.sqlite3` was deleted. |
| WebSocket fails to connect / HTTP 404 or 500 on the handshake | Not running under ASGI, or wrong path | Use `python manage.py runserver` (it prints *"Starting ASGI/Daphne ... server"*) or `daphne connecther.asgi:application`. **gunicorn / WSGI can't do WebSockets.** The path is `/ws/notifications/`, on the same port as the API. In production use `wss://`. |
| Live events stop after editing code | `runserver` reloaded and dropped every socket | The frontend should reconnect. Don't edit backend code during the demo. |
| Live events never arrive, but REST works | **More than one server process.** `InMemoryChannelLayer` only works inside one process | Run exactly one `runserver` (or one Daphne). On Railway, Replicas = 1. Check you don't have a second server on the same port. |
| Emails not arriving | Console backend, or a Gmail setup problem | With the default console backend, emails only **print in the server terminal**. For Gmail: an App Password (not your normal password), 2-Step Verification on, `EMAIL_BACKEND=...smtp.EmailBackend`, then `python manage.py test_email you@example.com`. Check spam. Seeded mentors have `@demo.com` addresses; use `SEED_REAL_EMAILS`. |
| Matches look keyword-based ("Experience in ...") | No LLM key, or the LLM call failed | Check the startup line and look for `LLM matching failed` in the log. Set the key in `.env` and restart. |
| Asking a question takes ~10 s | The LLM is slow or unreachable | It falls back after 10 s. For an offline demo, set `LLM_PROVIDER=none`. |
| `no such table` errors | Migrations not applied | `python manage.py migrate`, then `python manage.py seed`. |
| Login fails for demo accounts | Not seeded | `python manage.py seed` (resets every demo password to `demo1234`). |

---

## Deploying (Railway)

The `Procfile` runs migrate, collectstatic, seed and ensure_superuser, then starts Daphne. Set `DATABASE_URL=${{Postgres.DATABASE_URL}}`, `DEBUG=false`, `DJANGO_SECRET_KEY`, `FRONTEND_URL`, and the LLM/email variables in the service's Variables tab. Health check path: `/api/health/`. Keep **Replicas = 1** (in-memory channel layer) and Serverless **off**. Then run `python scripts/demo_check.py --url https://<name>.up.railway.app --origin <frontend origin>`.
