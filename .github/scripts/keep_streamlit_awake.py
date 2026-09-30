#!/usr/bin/env python3
# mypy: ignore-errors
"""Drive real browser visits to Streamlit Community Cloud apps so they stay awake.

Community Cloud only counts a *browser session* as a visit: the shell must run its
JavaScript and open the websocket to /_stcore/stream before the 12-hour hibernation
timer resets. A curl "ping" therefore never counts (and without a cookie jar curl loops
on Community Cloud's 303 auth redirect). HTTP status codes cannot distinguish awake from
asleep either: /_stcore/health and / both return the same ~9.8 KB static SPA shell
whether the app is running or hibernating (verified 2026-09-29).

This script drives headless Chromium instead: it loads each app, clicks Streamlit's
"Yes, get this app back up!" button when the sleep page is showing, then waits for the
running app shell and holds the session open so the visit registers.

Playwright is installed only inside .github/workflows/keep-apps-awake.yml (not as a
project dependency), hence the `# mypy: ignore-errors` file directive above.
"""

import argparse
import sys
import time

from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

# A real desktop user agent avoids Playwright's default "HeadlessChrome" banner.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# The sleep page's wake buttons use per-session data-testids
# ("wakeup-button-owner" / "wakeup-button-viewer"), so match on the stable prefix and
# fall back to the button text.
WAKE_BUTTON_SELECTORS = (
    '[data-testid^="wakeup-button"]',
    "button:has-text('get this app back up')",
)

# Running-app markers. Community Cloud's current shell renders the app inside
# <div id="root"><div><div class="_streamlitAppContainer_<hash>">...<iframe>, so the only
# stable part of that class name is the CSS-module local name; the hash suffix changes
# on every Streamlit deploy. `stAppViewContainer`/`.stApp` are kept for older Streamlit
# builds, which the 2026-09 build no longer uses.
RUNNING_APP_SELECTORS = (
    "[class*='streamlitAppContainer']",
    "[data-testid='stAppViewContainer']",
    ".stApp",
)
RUNNING_APP_SELECTOR = ", ".join(RUNNING_APP_SELECTORS)

# Opened by the app's Python process once the session starts - the very signal
# Streamlit counts as traffic.
STREAM_PATH = "/_stcore/stream"


def visit(page: Page, url: str, *, hold_seconds: int, timeout_ms: int) -> bool:
    """Visit *url*, waking the app if needed, and hold the session open.

    Returns True only once the app reaches its normal running state.
    """
    stream_opened = False

    def on_websocket(ws) -> None:
        nonlocal stream_opened
        if STREAM_PATH in ws.url:
            stream_opened = True

    page.on("websocket", on_websocket)

    print(f"Visiting {url} ...", flush=True)
    page.goto(url, wait_until="load", timeout=120_000)

    wake_button = page.locator(", ".join(WAKE_BUTTON_SELECTORS))

    woke = False
    for selector in WAKE_BUTTON_SELECTORS:
        button = page.locator(selector).first
        try:
            button.wait_for(state="visible", timeout=3_000)
            print(
                f"WOKE {url}  (sleep page detected; clicking the wake-up button)",
                flush=True,
            )
            button.click()
            woke = True
            break
        except PlaywrightTimeoutError:
            continue

    # Wait for the running shell. The sleep page shows the wake button, so require that
    # to be gone before trusting either marker.
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if wake_button.count() == 0 and (
            stream_opened or page.locator(RUNNING_APP_SELECTOR).count() > 0
        ):
            if woke:
                print(f"WOKE+RUNNING {url}  (was asleep, now running)", flush=True)
            else:
                print(f"RUNNING {url}  (app was already awake)", flush=True)
            # Keep the session (websocket) alive briefly so Community Cloud registers the
            # visit before the page is torn down.
            page.wait_for_timeout(hold_seconds * 1000)
            return True
        page.wait_for_timeout(2_000)

    print(
        f"FAILED {url}: app did not reach the running state within {timeout_ms} ms "
        f"({page.title()!r})",
        flush=True,
    )
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visit Streamlit Community Cloud apps with a real browser to keep them awake."
    )
    parser.add_argument(
        "urls", nargs="+", help="Streamlit Community Cloud app URLs to visit"
    )
    parser.add_argument(
        "--hold-seconds", type=int, default=60, help="Seconds to keep each session open"
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=180_000,
        help="How long to wait for an app to reach its running state, in ms",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exit_code = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
        )
        try:
            for url in args.urls:
                if not url.startswith(("http://", "https://")):
                    print(
                        f"FAILED {url!r}: not an http(s) URL; refusing to visit it",
                        flush=True,
                    )
                    print(f"::error::{url!r} is not a valid app URL", flush=True)
                    exit_code = 1
                    continue

                page = context.new_page()
                try:
                    ok = visit(
                        page,
                        url,
                        hold_seconds=args.hold_seconds,
                        timeout_ms=args.timeout_ms,
                    )
                # Isolate failures: one bad app must not hide the others' verdicts.
                except Exception as exc:
                    print(f"FAILED {url}: {type(exc).__name__}: {exc}", flush=True)
                    ok = False
                finally:
                    page.close()
                if ok:
                    print(f"::notice::{url} is awake and running", flush=True)
                else:
                    print(
                        f"::error::{url} is NOT running (visit failed or app could not be woken)",
                        flush=True,
                    )
                    exit_code = 1
        finally:
            context.close()
            browser.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
