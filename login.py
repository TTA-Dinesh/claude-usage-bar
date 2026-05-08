"""
login.py — Claude Usage Bar login helper

Opens claude.ai in the user's default browser, then polls every 2 seconds
until the sessionKey cookie appears in Chrome, Safari, Firefox, or Brave.
Once found, saves it to config.json and exits silently.
The main app detects the change and starts showing live usage.

Note: macOS may ask "python3 wants to use Chrome Safe Storage" — click Allow.
This is a one-time prompt so we can securely read your session cookie.
"""

import webbrowser
import time
import os
import json
import sys

CONFIG_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
TIMEOUT_SECS   = 600   # Give up after 10 minutes
POLL_INTERVAL  = 2     # Check every 2 seconds


def ensure_deps():
    """Install browser-cookie3 if missing (shouldn't happen after install.sh)."""
    try:
        import browser_cookie3
        return browser_cookie3
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "browser-cookie3"], check=True)
        import browser_cookie3
        return browser_cookie3


def find_session_key(browser_cookie3):
    """
    Check Chrome, Safari, Firefox, and Brave for a claude.ai sessionKey cookie.
    Returns the value string, or None if not found yet.
    """
    browsers = [
        ("Chrome",  browser_cookie3.chrome),
        ("Safari",  browser_cookie3.safari),
        ("Firefox", browser_cookie3.firefox),
        ("Brave",   browser_cookie3.brave),
    ]

    for name, loader in browsers:
        try:
            jar = loader(domain_name="claude.ai")
            for cookie in jar:
                if cookie.name == "sessionKey" and cookie.value:
                    return cookie.value
        except Exception:
            pass  # Browser not installed or not accessible — skip silently

    return None


def save_session_key(value):
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except Exception:
        config = {}
    config["session_key"] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


if __name__ == "__main__":
    bc3 = ensure_deps()

    # Open claude.ai in the user's default browser
    webbrowser.open("https://claude.ai/login")

    # Poll until we see the sessionKey cookie
    deadline = time.time() + TIMEOUT_SECS
    while time.time() < deadline:
        key = find_session_key(bc3)
        if key:
            save_session_key(key)
            sys.exit(0)
        time.sleep(POLL_INTERVAL)

    # Timed out — exit silently (app will keep showing "Sign in" button)
    sys.exit(1)
