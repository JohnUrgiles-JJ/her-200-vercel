"""Print every message the ConnectHER notification socket sends. For manual testing and demo rehearsal.

Usage (from backend/, with the venv active):
    python scripts/ws_listen.py <token>
    python scripts/ws_listen.py <token> --url wss://<name>.up.railway.app/ws/notifications/

On connect it sends {"event": "ping"}, so a {"event": "pong"} line proves the round trip works.
Ctrl+C to stop. Exit code 2 means the server rejected the token (close code 4401).
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from urllib.parse import urlencode

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake

DEFAULT_URL = "ws://127.0.0.1:8000/ws/notifications/"


def log(text):
    print(f"[{datetime.now():%H:%M:%S}] {text}", flush=True)


async def listen(url, token):
    full_url = f"{url}?{urlencode({'token': token})}"
    log(f"connecting to {url}?token={token[:6]}...")
    async with connect(full_url, open_timeout=10) as ws:
        log("connected")
        try:
            # A rejected token is accepted and then closed with 4401 right away, so this send can fail.
            await ws.send(json.dumps({"event": "ping"}))
            async for raw in ws:
                try:
                    message = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
                except ValueError:
                    message = repr(raw)
                log(f"message:\n{message}")
        except ConnectionClosed:
            pass
        code, reason = ws.close_code, ws.close_reason
    log(f"closed by server: code={code} reason={reason!r}")
    if code == 4401:
        log("4401 = missing or invalid token. Get a fresh one from POST /api/login/ or `python manage.py seed`.")
        return 2
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("token", help="DRF token key (from /api/login/ or `python manage.py seed`)")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"socket URL without ?token (default {DEFAULT_URL})")
    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")  # Windows consoles can't print every character
    try:
        sys.exit(asyncio.run(listen(args.url, args.token)))
    except KeyboardInterrupt:
        log("stopped")
    except InvalidHandshake as exc:  # e.g. HTTP 500 for a wrong path (the router has no such route)
        log(f"handshake failed: {exc}. Check the URL; it should end in /ws/notifications/")
        sys.exit(1)
    except (OSError, TimeoutError) as exc:
        log(f"could not connect: {exc!r}. Is `python manage.py runserver` running?")
        sys.exit(1)


if __name__ == "__main__":
    main()
