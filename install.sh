#!/bin/bash
# Claude Usage Bar — one-command installer for macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/TTA-Dinesh/claude-usage-bar/main/install.sh | bash

set -e

REPO="https://raw.githubusercontent.com/TTA-Dinesh/claude-usage-bar/main"
INSTALL_DIR="$HOME/claude-usage-bar"
PLIST_PATH="$HOME/Library/LaunchAgents/com.tta.claude-usage-bar.plist"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Claude Usage Bar — Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Find Python 3 ──────────────────────────────────────────────────────────
# Check common locations (Homebrew, system, pyenv)
PYTHON=""
for candidate in python3 /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON=$(command -v "$candidate")
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌  Python 3 not found."
    echo ""
    echo "    Install it with Homebrew:  brew install python"
    echo "    Or download from:          https://python.org/downloads"
    exit 1
fi
echo "✓  Python 3 found ($PYTHON)"

# ── 2. Install Python dependencies ────────────────────────────────────────────
echo "→  Installing dependencies (this may take a minute)…"
"$PYTHON" -m pip install --quiet --upgrade \
    rumps \
    requests \
    pyobjc-framework-Cocoa \
    browser-cookie3
echo "✓  Dependencies ready"

# ── 3. Download app files ─────────────────────────────────────────────────────
echo "→  Downloading app to $INSTALL_DIR…"
mkdir -p "$INSTALL_DIR"
curl -fsSL "$REPO/app.py"   -o "$INSTALL_DIR/app.py"
curl -fsSL "$REPO/login.py" -o "$INSTALL_DIR/login.py"

# Create a fresh empty config if one doesn't already exist
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    echo '{"session_key": ""}' > "$INSTALL_DIR/config.json"
fi
echo "✓  App downloaded"

# ── 4. Set up auto-start on login ─────────────────────────────────────────────
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

# Reload the agent (stop old version if running, start fresh)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load   "$PLIST_PATH"
echo "✓  Auto-start configured"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ✅  Claude Usage Bar is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Your browser will open in a moment."
echo "   Sign in to Claude and the menubar icon"
echo "   will update automatically. That's it!"
echo ""
echo "   If macOS asks 'python3 wants to use"
echo "   Chrome Safe Storage' — click Allow."
echo "   (one-time prompt to read your session)"
echo ""
