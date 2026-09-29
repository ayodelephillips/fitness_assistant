#!/usr/bin/env python3
# mypy: ignore-errors
"""Drive real browser visits to Streamlit Community Cloud apps so they stay awake.

Community Cloud serves a *static SPA shell* to plain HTTP clients: the Python process
only starts after the JavaScript bundle runs and opens a websocket to /_stcore/stream.
A curl "ping" therefore never registers as a visit (and without a cookie jar it loops
on Community Cloud's 303 auth redirect). This script drives headless Chromium instead,
clicking Streamlit's "Yes, get this app back up!" button when the sleep page is showing
and then holding the session open long enough to reset the 12-hour hibernation timer.

Playwright is installed only inside .github/workflows/keep-apps-awake.yml (not as a
project dependency), hence the `# mypy: ignore-errors` file directive above.
"""

import argparse
import sys

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

# Modern Streamlit renders the running app under a testid; older versions used
# .stApp / section.main. Try all of them so the check survives Streamlit version bumps.
RUNNING_APP_SELECTORS = (
    "[data-testid='stAppViewContainer']",
    ".stApp",
    "section.main",
)


def visit(page: Page, url: str, *, hold_seconds: int, timeout_ms: int) -> bool:
    """Visit *url*, waking the app if needed, and hold the session open.

    Returns True only once the app reaches its normal running state.
    """
    print(f"Visiting {url} ...")
    page.goto(url, wait_until="load", timeout=120_000)

    woke = False
    for selector in WAKE_BUTTON_SELECTORS:
        button = page.locator(selector).first
        try:
            button.wait_for(state="visible", timeout=3_000)
            print(f"WOKE {url}  (sleep page detected; clicked the wake-up button)")
            button.click()
            woke = True
            break
        except PlaywrightTimeoutError:
            continue

    try:
        page.wait_for_selector(", ".join(RUNNING_APP_SELECTORS), timeout=timeout_ms)
    except PlaywrightTimeoutError:
        print(
            f"FAILED {url}: app did not reach the running state within {timeout_ms} ms"
        )
        return False

    if woke:
        print(f"WOKE+RUNNING {url}  (was asleep, now running)")
    else:
        print(f"RUNNING {url}  (app was already awake)")

    # Keep the websocket session alive briefly so Community Cloud registers the visit
    # before the page is torn down.
    page.wait_for_timeout(hold_seconds * 1000)
    return True


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
        page = context.new_page()
        try:
            for url in args.urls:
                try:
                    ok = visit(
                        page,
                        url,
                        hold_seconds=args.hold_seconds,
                        timeout_ms=args.timeout_ms,
                    )
                except (
                    Exception
                ) as exc:  # isolate failures so one app can't hide the others
                    print(f"FAILED {url}: {type(exc).__name__}: {exc}")
                    ok = False
                if ok:
                    print(f"::notice::{url} is awake and running")
                else:
                    print(
                        f"::error::{url} is NOT running (visit failed or app could not be woken)"
                    )
                    exit_code = 1
        finally:
            context.close()
            browser.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
