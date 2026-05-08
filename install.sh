#!/bin/bash
# Claude Usage Bar — one-command installer
# Usage: curl -fsSL https://raw.githubusercontent.com/TTA-Dinesh/claude-usage-bar/main/install.sh | bash

set -e

REPO="https://raw.githubusercontent.com/TTA-Dinesh/claude-usage-bar/main"
INSTALL_DIR="$HOME/claude-usage-bar"
PLIST_PATH="$HOME/Library/LaunchAgents/com.tta.claude-usage-bar.plist"
PYTHON=$(command -v python3 || true)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Claude Usage Bar — Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Check Python 3 ─────────────────────────────────────────────────────────
if [ -z "$PYTHON" ]; then
  echo "❌  Python 3 not found."
  echo "    Install it from https://python.org or via Homebrew: brew install python"
  exit 1
fi
echo "✓  Python 3 found at $PYTHON"

# ── 2. Install Python dependencies ────────────────────────────────────────────
echo "→  Installing Python dependencies…"
$PYTHON -m pip install --quiet --upgrade rumps requests pyobjc-framework-Cocoa
echo "✓  Dependencies installed"

# ── 3. Download app ───────────────────────────────────────────────────────────
echo "→  Downloading app to $INSTALL_DIR…"
mkdir -p "$INSTALL_DIR"
curl -fsSL "$REPO/app.py" -o "$INSTALL_DIR/app.py"

# Create empty config if one doesn't already exist
if [ ! -f "$INSTALL_DIR/config.json" ]; then
  echo '{"session_key": ""}' > "$INSTALL_DIR/config.json"
fi
echo "✓  App downloaded"

# ── 4. Set up LaunchAgent (auto-start on login) ───────────────────────────────
echo "→  Setting up auto-start on login…"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.tta.claude-usage-bar</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$INSTALL_DIR/app.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$INSTALL_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$INSTALL_DIR/output.log</string>
  <key>StandardErrorPath</key>
  <string>$INSTALL_DIR/error.log</string>
</dict>
</plist>
EOF
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "✓  Auto-start configured"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Claude Usage Bar is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  You should see 'Claude —' in your menubar."
echo ""
echo "  Next step: click it → ⚙ Set Session Cookie…"
echo "  Get your cookie from:"
echo "  DevTools → Application → Cookies → claude.ai → sessionKey"
echo ""
