import rumps
import requests
import json
import threading
import subprocess
import sys
import os
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
API_URL = "https://claude.ai/api/organizations/e682e130-7a2e-4833-8553-67c0b0bc0ed0/usage"
REFRESH_INTERVAL = 300  # 5 minutes


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def time_until(iso_str):
    if not iso_str:
        return "—"
    try:
        reset = datetime.fromisoformat(iso_str)
        delta = reset - datetime.now(timezone.utc)
        total = int(delta.total_seconds())
        if total <= 0:
            return "soon"
        h, rem = divmod(total, 3600)
        m = rem // 60
        return f"{h}h {m}m" if h else f"{m}m"
    except Exception:
        return "—"


def pct_bar(pct, width=10):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ── App ───────────────────────────────────────────────────────────────────────
class ClaudeUsageBar(rumps.App):
    def __init__(self):
        super().__init__("Claude")
        config = load_config()
        self.session_key = config.get("session_key", "")
        self.usage_timer = None

        # ── Menu items ────────────────────────────────────────────────────────
        self.item_session     = rumps.MenuItem("Session:  —")
        self.item_session_bar = rumps.MenuItem("")
        self.item_session_rst = rumps.MenuItem("  Resets in: —")
        self.item_weekly      = rumps.MenuItem("Weekly:   —")
        self.item_weekly_bar  = rumps.MenuItem("")
        self.item_weekly_rst  = rumps.MenuItem("  Resets in: —")
        self.item_status      = rumps.MenuItem("—")
        self.item_signin      = rumps.MenuItem("🔐  Sign in to Claude…", callback=self.sign_in)
        self.item_signout     = rumps.MenuItem("Sign Out", callback=self.sign_out)
        self.item_refresh     = rumps.MenuItem("↻  Refresh Now", callback=self.manual_refresh)

        self.menu = [
            self.item_session,
            self.item_session_bar,
            self.item_session_rst,
            None,
            self.item_weekly,
            self.item_weekly_bar,
            self.item_weekly_rst,
            None,
            self.item_status,
            None,
            self.item_refresh,
            self.item_signin,
            self.item_signout,
        ]

        # ── Boot state ────────────────────────────────────────────────────────
        if self.session_key:
            self._start_usage_polling()
        else:
            self._set_signed_out_state()

        # Always poll config.json every 2s to detect login completion
        self.login_watcher = rumps.Timer(self._check_for_login, 2)
        self.login_watcher.start()

    # ── Polling ───────────────────────────────────────────────────────────────
    def _start_usage_polling(self):
        self._fetch()
        if self.usage_timer:
            self.usage_timer.stop()
        self.usage_timer = rumps.Timer(lambda _: self._fetch(), REFRESH_INTERVAL)
        self.usage_timer.start()

    def _fetch(self):
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        if not self.session_key:
            return
        try:
            resp = requests.get(
                API_URL,
                headers={
                    "Cookie": f"sessionKey={self.session_key}",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
                timeout=10,
            )
            if resp.status_code == 401:
                self.session_key = ""
                save_config({"session_key": ""})
                self._set_signed_out_state()
                self.item_status.title = "⚠ Session expired — please sign in again"
                return
            resp.raise_for_status()
            self._update_ui(resp.json())
        except requests.HTTPError as e:
            self.title = "Claude ✗"
            self.item_status.title = f"Error {e.response.status_code}"
        except Exception as e:
            self.title = "Claude ✗"
            self.item_status.title = f"Error: {e}"

    def _update_ui(self, data):
        five  = data.get("five_hour") or {}
        seven = data.get("seven_day") or {}

        s_pct = five.get("utilization", 0) or 0
        w_pct = seven.get("utilization", 0) or 0

        self.title = f"Claude {int(s_pct)}%"

        self.item_session.title     = f"Session:  {int(s_pct)}%"
        self.item_session_bar.title = f"  {pct_bar(s_pct)}"
        self.item_session_rst.title = f"  Resets in {time_until(five.get('resets_at'))}"

        self.item_weekly.title      = f"Weekly:   {int(w_pct)}%"
        self.item_weekly_bar.title  = f"  {pct_bar(w_pct)}"
        self.item_weekly_rst.title  = f"  Resets in {time_until(seven.get('resets_at'))}"

        self.item_status.title = f"Updated {datetime.now().strftime('%H:%M')}"

    # ── Login watcher ─────────────────────────────────────────────────────────
    def _check_for_login(self, _):
        """Detect when login.py writes a new sessionKey to config.json."""
        config = load_config()
        new_key = config.get("session_key", "")
        if new_key and new_key != self.session_key:
            self.session_key = new_key
            self.item_status.title = "Signed in — fetching usage…"
            self._start_usage_polling()

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def sign_in(self, _):
        self.item_status.title = "Opening sign-in window…"
        login_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login.py")
        subprocess.Popen([sys.executable, login_script])

    def sign_out(self, _):
        self.session_key = ""
        save_config({"session_key": ""})
        if self.usage_timer:
            self.usage_timer.stop()
        self._set_signed_out_state()

    def manual_refresh(self, _):
        self.item_status.title = "Refreshing…"
        self._fetch()

    # ── UI states ─────────────────────────────────────────────────────────────
    def _set_signed_out_state(self):
        self.title = "Claude"
        self.item_session.title     = "Session:  —"
        self.item_session_bar.title = ""
        self.item_session_rst.title = "  Resets in: —"
        self.item_weekly.title      = "Weekly:   —"
        self.item_weekly_bar.title  = ""
        self.item_weekly_rst.title  = "  Resets in: —"
        self.item_status.title      = "Sign in to see your usage"


if __name__ == "__main__":
    ClaudeUsageBar().run()
