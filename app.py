import rumps
import requests
import json
import threading
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"
API_URL = "https://claude.ai/api/organizations/e682e130-7a2e-4833-8553-67c0b0bc0ed0/usage"
REFRESH_INTERVAL = 300  # seconds (5 minutes)


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
    """Return human-readable time until a UTC ISO timestamp."""
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
    """Simple ASCII progress bar, e.g. ████░░░░░░"""
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ── App ───────────────────────────────────────────────────────────────────────
class ClaudeUsageBar(rumps.App):
    def __init__(self):
        super().__init__("Claude —")
        config = load_config()
        self.session_key = config.get("session_key", "")

        # Build menu items (keep references so we can update titles)
        self.item_session     = rumps.MenuItem("Session:  —")
        self.item_session_bar = rumps.MenuItem("")
        self.item_session_rst = rumps.MenuItem("Resets in: —")
        self.item_weekly      = rumps.MenuItem("Weekly:   —")
        self.item_weekly_bar  = rumps.MenuItem("")
        self.item_weekly_rst  = rumps.MenuItem("Weekly resets: —")
        self.item_status      = rumps.MenuItem("Last updated: —")

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
            rumps.MenuItem("↻ Refresh Now", callback=self.manual_refresh),
            rumps.MenuItem("⚙ Set Session Cookie…", callback=self.set_cookie),
        ]

        # Kick off first fetch, then repeat on timer
        self._fetch()
        self.timer = rumps.Timer(lambda _: self._fetch(), REFRESH_INTERVAL)
        self.timer.start()

    # ── Data fetching ──────────────────────────────────────────────────────────
    def _fetch(self):
        """Fetch usage in a background thread to avoid blocking the UI."""
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        if not self.session_key:
            self.title = "Claude ⚠"
            self.item_status.title = "⚠ No session cookie set"
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
            resp.raise_for_status()
            self._update_ui(resp.json())
        except requests.HTTPError as e:
            self.title = "Claude ✗"
            self.item_status.title = f"Error: {e.response.status_code}"
        except Exception as e:
            self.title = "Claude ✗"
            self.item_status.title = f"Error: {e}"

    def _update_ui(self, data):
        five  = data.get("five_hour") or {}
        seven = data.get("seven_day") or {}

        s_pct = five.get("utilization", 0) or 0
        w_pct = seven.get("utilization", 0) or 0

        # Menubar title
        self.title = f"Claude {int(s_pct)}%"

        # Session block
        self.item_session.title     = f"Session:  {int(s_pct)}%"
        self.item_session_bar.title = f"  {pct_bar(s_pct)}"
        self.item_session_rst.title = f"  Resets in {time_until(five.get('resets_at'))}"

        # Weekly block
        self.item_weekly.title      = f"Weekly:   {int(w_pct)}%"
        self.item_weekly_bar.title  = f"  {pct_bar(w_pct)}"
        self.item_weekly_rst.title  = f"  Resets in {time_until(seven.get('resets_at'))}"

        # Footer
        now = datetime.now().strftime("%H:%M")
        self.item_status.title = f"Updated {now}"

    # ── Callbacks ──────────────────────────────────────────────────────────────
    def manual_refresh(self, _):
        self.item_status.title = "Refreshing…"
        self._fetch()

    def set_cookie(self, _):
        win = rumps.Window(
            title="Session Cookie",
            message=(
                "Paste your sessionKey cookie value.\n\n"
                "Get it from: DevTools → Application → Cookies → claude.ai → sessionKey"
            ),
            default_text=self.session_key,
            ok="Save",
            cancel="Cancel",
            dimensions=(420, 60),
        )
        response = win.run()
        if response.clicked:
            self.session_key = response.text.strip()
            save_config({"session_key": self.session_key})
            self._fetch()


if __name__ == "__main__":
    ClaudeUsageBar().run()
