"""Demo-day end-to-end check: runs the exact pitch flow against a LIVE server and prints PASS/FAIL per step.

Usage (from backend/, venv active, server running in another terminal):
    python scripts/demo_check.py                         # local: runs `seed --reset` first, then checks
    python scripts/demo_check.py --no-reset              # keep existing questions/answers
    python scripts/demo_check.py --url https://<name>.up.railway.app   # production (never resets)

Flow: seed --reset -> health -> CORS preflight -> login student1 + maya -> open both sockets (with the
frontend's Origin) -> student1 asks the UX question -> 3 matches, Maya among them -> Maya's socket gets
new_question within 5 s -> Maya answers -> student1's socket gets new_answer within 5 s ->
GET /questions/mine/ shows the answer.

Exit code 0 = every step passed (warnings allowed), 1 = something failed. Uses only the standard library
plus `websockets` (already in requirements.txt).

NOTE: the local run deletes ALL questions, matches and answers (that's what `seed --reset` does) and leaves
exactly one answered demo question behind. Run `python manage.py seed --reset` again right before the pitch
if you want Maya's inbox empty.
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlparse

try:
    from websockets.asyncio.client import connect
except ImportError:  # pragma: no cover
    sys.exit("The `websockets` package is missing. Activate the venv and run: pip install -r requirements.txt")

QUESTION = "How do I break into UX design without a design degree?"
ANSWER = "Start with 3 case studies from problems you solved as a teacher. Happy to review them!"
PASSWORD = "demo1234"
EVENT_TIMEOUT = 5.0
BACKEND_DIR = Path(__file__).resolve().parent.parent

USE_COLOR = sys.stdout.isatty()


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


class Report:
    def __init__(self):
        self.passed = self.failed = self.warned = 0
        self.step = 0

    def _line(self, tag, text, detail=""):
        print(f"{tag} {text}" + (f"\n       {detail}" if detail else ""), flush=True)

    def ok(self, text, detail=""):
        self.passed += 1
        self._line(_c("32", "PASS"), text, detail)

    def fail(self, text, detail=""):
        self.failed += 1
        self._line(_c("31", "FAIL"), text, detail)

    def warn(self, text, detail=""):
        self.warned += 1
        self._line(_c("33", "WARN"), text, detail)

    def info(self, text):
        self._line("    ", text)

    def check(self, condition, text, detail_if_fail=""):
        (self.ok if condition else self.fail)(text, "" if condition else detail_if_fail)
        return condition

    def header(self, title):
        self.step += 1
        print(f"\n[{self.step}] {title}", flush=True)


R = Report()


class Abort(Exception):
    """A step failed in a way that makes the rest of the flow meaningless."""


# --- HTTP ----------------------------------------------------------------------------------------------


def http(method, url, body=None, token=None, headers=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Token {token}")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            status, raw, hdrs = res.status, res.read(), res.headers
    except urllib.error.HTTPError as err:
        status, raw, hdrs = err.code, err.read(), err.headers
    try:
        payload = json.loads(raw) if raw else None
    except ValueError:
        payload = {"_raw": raw[:200].decode(errors="replace")}
    return status, payload, hdrs


async def ahttp(*args, **kwargs):
    return await asyncio.to_thread(http, *args, **kwargs)


# --- WebSocket listener --------------------------------------------------------------------------------


class Listener:
    """One open notification socket; every message it receives goes into a queue."""

    def __init__(self, name, ws_url, token, origin):
        self.name, self.url, self.origin = name, f"{ws_url}?{urlencode({'token': token})}", origin
        self.queue = asyncio.Queue()
        self.ws = None
        self.task = None

    async def open(self):
        self.ws = await connect(self.url, origin=self.origin, open_timeout=10)
        self.task = asyncio.create_task(self._pump())
        await self.ws.send(json.dumps({"event": "ping"}))
        return await self.wait_for("pong", timeout=EVENT_TIMEOUT)

    async def _pump(self):
        try:
            async for raw in self.ws:
                try:
                    await self.queue.put(json.loads(raw))
                except ValueError:
                    pass
        except Exception:
            pass

    async def wait_for(self, event, timeout):
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                msg = await asyncio.wait_for(self.queue.get(), remaining)
            except asyncio.TimeoutError:
                return None
            if isinstance(msg, dict) and msg.get("event") == event:
                return msg

    async def close(self):
        if self.task:
            self.task.cancel()
        if self.ws:
            await self.ws.close()


# --- Steps ---------------------------------------------------------------------------------------------


def run_seed_reset():
    R.header("Reset demo data (python manage.py seed --reset)")
    cmd = [sys.executable, str(BACKEND_DIR / "manage.py"), "seed", "--reset"]
    try:
        out = subprocess.run(cmd, cwd=BACKEND_DIR, capture_output=True, text=True, timeout=120)
    except Exception as exc:
        R.fail("seed --reset could not run", repr(exc))
        raise Abort
    summary = [line for line in out.stdout.splitlines() if "deleted" in line.lower() or "seeded" in line.lower()]
    if out.returncode != 0:
        R.fail("seed --reset exited with an error", (out.stderr or out.stdout).strip()[-500:])
        raise Abort
    R.ok("seed --reset")
    for line in summary:
        R.info(line)


async def login(api, email):
    status, data, _ = await ahttp("POST", f"{api}/login/", {"email": email, "password": PASSWORD})
    if not R.check(status == 200 and data and "token" in data, f"login {email} -> 200",
                   f"got {status} {data}. Did you run `python manage.py seed`?"):
        raise Abort
    return data["token"], data["user"]


async def main(args):
    base = args.url.rstrip("/")
    api = f"{base}/api"
    parsed = urlparse(base)
    ws_url = f"{'wss' if parsed.scheme == 'https' else 'ws'}://{parsed.netloc}/ws/notifications/"
    local = parsed.hostname in ("127.0.0.1", "localhost", "::1")
    print(f"ConnectHER demo check against {base}  (frontend origin {args.origin})")

    if args.no_reset:
        print("\n(skipping seed --reset: --no-reset)")
    elif not local:
        print("\n(skipping seed --reset: not a local server. For Railway run `railway run python manage.py seed --reset`.)")
    else:
        run_seed_reset()

    R.header("Server reachable")
    try:
        status, data, _ = await ahttp("GET", f"{api}/health/", timeout=10)
    except Exception as exc:
        R.fail(f"GET {api}/health/", f"{exc!r}. Is the server running? `python manage.py runserver`")
        raise Abort
    R.check(status == 200 and data and data.get("db") is True, "GET /api/health/ -> 200, db true", f"{status} {data}")

    R.header("CORS from the frontend origin")
    status, _, hdrs = await ahttp("OPTIONS", f"{api}/questions/", headers={
        "Origin": args.origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"})
    allow = hdrs.get("Access-Control-Allow-Origin")
    R.check(status == 200 and allow == args.origin, f"preflight OPTIONS /api/questions/ allows {args.origin}",
            f"status {status}, Access-Control-Allow-Origin={allow!r}. Set FRONTEND_URL / EXTRA_CORS_ORIGINS.")

    R.header("Log in as student1 (mentee) and maya (mentor)")
    s_token, s_user = await login(api, "student1@demo.com")
    m_token, m_user = await login(api, "maya@demo.com")
    R.check(s_user.get("role") == "mentee" and m_user.get("role") == "mentor", "roles: student1=mentee, maya=mentor",
            f"{s_user.get('role')} / {m_user.get('role')}")

    R.header("Open WebSockets for maya and student1")
    maya_ws = Listener("maya", ws_url, m_token, args.origin)
    student_ws = Listener("student1", ws_url, s_token, args.origin)
    try:
        for listener in (maya_ws, student_ws):
            try:
                pong = await listener.open()
            except Exception as exc:
                R.fail(f"{listener.name}'s socket opened", f"{exc!r}. Is the server running under ASGI (Daphne)?")
                raise Abort
            if not R.check(pong is not None, f"{listener.name}'s socket open (ping -> pong)",
                           f"no pong; close code {listener.ws.close_code} (4401 = bad token)"):
                raise Abort
        await run_flow(api, s_token, m_token, maya_ws, student_ws)
    finally:
        await maya_ws.close()
        await student_ws.close()


async def run_flow(api, s_token, m_token, maya_ws, student_ws):
    R.header(f'student1 asks: "{QUESTION}"')
    started = time.monotonic()
    status, question, _ = await ahttp("POST", f"{api}/questions/", {"text": QUESTION}, token=s_token)
    took = time.monotonic() - started
    if not R.check(status == 201 and question and "matches" in question, f"POST /api/questions/ -> 201 ({took:.1f}s)",
                   f"{status} {question}"):
        raise Abort
    matches = question["matches"]
    for m in matches:
        R.info(f"#{m['rank']} {m['name']} ({m['headline']} @ {m['company']}): {m['reason']}")
    R.check(len(matches) == 3, "exactly 3 matches", f"got {len(matches)}")
    if took > 8:
        R.warn(f"asking took {took:.1f}s", "The LLM is slow. Fine, but expect a pause on stage (fallback after 10 s).")
    maya_match = next((m for m in matches if m["name"] == "Maya Chen"), None)
    if maya_match is None:
        R.warn("Maya is NOT among the matches",
               "The pitch shows Maya's inbox. Try `LLM_PROVIDER=none` (the keyword fallback ranks Maya #1) "
               "or rehearse with the mentor who was matched.")
        R.info("Skipping the Maya steps (socket event, answer) since she wasn't matched.")
        return
    R.ok(f"Maya is matched (rank {maya_match['rank']}, match_id {maya_match['match_id']})")

    R.header(f"Maya's socket gets new_question (within {EVENT_TIMEOUT:g}s)")
    event = await maya_ws.wait_for("new_question", EVENT_TIMEOUT)
    if R.check(event is not None, "new_question received",
               "nothing arrived. One server process only (InMemoryChannelLayer); don't run two servers."):
        R.info(json.dumps(event, ensure_ascii=False))
        R.check(event.get("match_id") == maya_match["match_id"] and event.get("question_id") == question["id"]
                and event.get("question") == QUESTION and event.get("mentee_name") == "Maria L.",
                "payload has Maya's match_id, the question and mentee_name 'Maria L.'", json.dumps(event))

    R.header("Maya answers")
    status, answer, _ = await ahttp("POST", f"{api}/matches/{maya_match['match_id']}/answer/", {"text": ANSWER}, token=m_token)
    if not R.check(status == 201 and answer and answer.get("text") == ANSWER, "POST /api/matches/<id>/answer/ -> 201",
                   f"{status} {answer}"):
        raise Abort

    R.header(f"student1's socket gets new_answer (within {EVENT_TIMEOUT:g}s)")
    event = await student_ws.wait_for("new_answer", EVENT_TIMEOUT)
    if R.check(event is not None, "new_answer received", "nothing arrived on student1's socket"):
        R.info(json.dumps(event, ensure_ascii=False))
        R.check(event.get("match_id") == maya_match["match_id"] and event.get("mentor_name") == "Maya Chen"
                and event.get("text") == ANSWER, "payload has Maya's match_id, mentor_name and the answer text",
                json.dumps(event))

    R.header("GET /api/questions/mine/ shows the answer")
    status, mine, _ = await ahttp("GET", f"{api}/questions/mine/", token=s_token)
    mine_q = next((q for q in (mine or []) if q.get("id") == question["id"]), None) if status == 200 else None
    mine_m = next((m for m in mine_q["matches"] if m["match_id"] == maya_match["match_id"]), None) if mine_q else None
    R.check(mine_m is not None and mine_m["status"] == "answered" and any(a["text"] == ANSWER for a in mine_m["answers"]),
            "Maya's match is 'answered' with the answer text", f"{status} {json.dumps(mine_m)[:300]}")


def cli():
    parser = argparse.ArgumentParser(description="ConnectHER demo-day end-to-end check (needs a running server).")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="server base URL (default http://127.0.0.1:8000)")
    parser.add_argument("--origin", default="http://localhost:5173", help="frontend origin for CORS/WebSocket checks")
    parser.add_argument("--no-reset", action="store_true", help="don't run `manage.py seed --reset` first")
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except Abort:
        print("\nStopped early: the steps after this depend on the one that failed.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    print(f"\nRESULT: {R.passed} passed, {R.failed} failed, {R.warned} warnings  ->  "
          + (_c("32", "READY FOR THE DEMO") if R.failed == 0 and R.warned == 0
             else _c("33", "PASSED WITH WARNINGS") if R.failed == 0 else _c("31", "NOT READY")))
    sys.exit(1 if R.failed else 0)


if __name__ == "__main__":
    cli()
