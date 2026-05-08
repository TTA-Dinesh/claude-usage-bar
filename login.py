"""
login.py — Claude Usage Bar login helper

Opens a native WebView with claude.ai, waits for the user to sign in,
then automatically captures the sessionKey cookie, saves it to config.json,
and exits. The main app (app.py) detects the saved cookie and starts showing usage.
"""

import webview
import json
import time
import os
import sys

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_session_key(value):
    config = load_config()
    config["session_key"] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def watch_for_cookie(window):
    """
    Runs inside the WebView thread.
    Polls cookies every 1.5s until sessionKey appears,
    then saves it and closes the window.
    """
    time.sleep(2)  # Give the page time to load initially

    while True:
        try:
            cookies = window.get_cookies()
            for c in cookies:
                # pywebview may return dicts or objects depending on version
                if isinstance(c, dict):
                    name  = c.get("name", "")
                    value = c.get("value", "")
                else:
                    name  = getattr(c, "name", "")
                    value = getattr(c, "value", "")

                if name == "sessionKey" and value:
                    save_session_key(value)
                    window.destroy()
                    sys.exit(0)
        except Exception:
            pass

        time.sleep(1.5)


if __name__ == "__main__":
    window = webview.create_window(
        title="Sign in to Claude",
        url="https://claude.ai/login",
        width=960,
        height=720,
        on_top=True,
    )
    webview.start(watch_for_cookie, window)
