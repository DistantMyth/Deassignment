#!/bin/bash
set -e

# =============================================================================
# Deassignment - macOS Installer
# =============================================================================
# This script sets up the Deassignment tool on macOS.
# It checks for required tools, guides you through permissions setup,
# creates a Python virtual environment, and installs dependencies.
# =============================================================================

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Helper Functions ---
print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}=== $1 ===${NC}"
}

print_ok() {
    echo -e "  ${GREEN}✔${NC} $1"
}

print_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

print_fail() {
    echo -e "  ${RED}✘${NC} $1"
}

echo -e "${BOLD}Starting Deassignment macOS Installation...${NC}"

# =============================================================================
# 1. Check macOS Version (minimum macOS 12 Monterey)
# =============================================================================
print_header "Checking macOS Version"

MACOS_VERSION=$(sw_vers -productVersion)
MACOS_MAJOR=$(echo "$MACOS_VERSION" | cut -d. -f1)

if [ "$MACOS_MAJOR" -ge 12 ]; then
    print_ok "macOS $MACOS_VERSION detected (minimum: 12 Monterey)"
else
    print_fail "macOS $MACOS_VERSION detected. Minimum required version is macOS 12 (Monterey)."
    echo "       Please upgrade your macOS before continuing."
    exit 1
fi

# =============================================================================
# 2. Check for Homebrew
# =============================================================================
print_header "Checking for Homebrew"

if command -v brew &>/dev/null; then
    BREW_VER=$(brew --version | head -1)
    print_ok "Homebrew found: $BREW_VER"
else
    print_warn "Homebrew is not installed."
    echo ""
    echo "       Homebrew is recommended for installing optional dependencies."
    echo "       To install Homebrew, run the following command in your terminal:"
    echo ""
    echo -e "       ${BOLD}/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
    echo ""
    echo "       For more info, visit: https://brew.sh"
    echo "       (Continuing without Homebrew...)"
fi

# =============================================================================
# 3. Check Python 3
# =============================================================================
print_header "Checking Python 3"

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_ok "Python $PY_VER found"
else
    print_fail "Python 3 is required but not found."
    echo "       Install Python 3.8+ from https://www.python.org/downloads/ or via Homebrew:"
    echo "       brew install python"
    exit 1
fi

# =============================================================================
# 4. Check for Xcode Command Line Tools
# =============================================================================
print_header "Checking Xcode Command Line Tools"

if xcode-select -p &>/dev/null; then
    print_ok "Xcode Command Line Tools are installed: $(xcode-select -p)"
else
    print_fail "Xcode Command Line Tools are not installed."
    echo "       Install them by running:"
    echo "       xcode-select --install"
    exit 1
fi

# =============================================================================
# 5. Check for VSCode
# =============================================================================
print_header "Checking for Visual Studio Code"

if command -v code &>/dev/null; then
    VSCODE_VER=$(code --version | head -1)
    print_ok "VSCode found: v$VSCODE_VER"
else
    print_warn "VSCode ('code' command) not found in PATH."
    echo "       This tool requires VSCode. Install it from https://code.visualstudio.com/"
    echo "       Then open VSCode, press Cmd+Shift+P, type 'shell command', and install the 'code' command."
fi

# =============================================================================
# 6. Check for DejaVu Sans Mono Font
# =============================================================================
print_header "Checking for Monospace Fonts"

FONT_FOUND=0

# Check system-wide fonts
if ls /Library/Fonts/DejaVu* &>/dev/null 2>&1; then
    print_ok "DejaVu Sans Mono found in /Library/Fonts/"
    FONT_FOUND=1
fi

# Check user fonts
if ls ~/Library/Fonts/DejaVu* &>/dev/null 2>&1; then
    print_ok "DejaVu Sans Mono found in ~/Library/Fonts/"
    FONT_FOUND=1
fi

if [ $FONT_FOUND -eq 0 ]; then
    print_warn "DejaVu Sans Mono not found. Menlo (macOS built-in) will be used as fallback."
    if command -v brew &>/dev/null; then
        echo "       To install DejaVu Sans Mono via Homebrew (optional):"
        echo -e "       ${BOLD}brew install --cask font-dejavu-sans-mono${NC}"
    fi
fi

# =============================================================================
# 7. Guide Accessibility Permissions
# =============================================================================
print_header "Accessibility Permissions"

echo -e "  ${YELLOW}ACTION REQUIRED:${NC} Your terminal app must have Accessibility permissions"
echo "  for keyboard simulation and desktop automation to work."
echo ""
echo "  To grant Accessibility access:"
echo "    1. Open ${BOLD}System Settings${NC} (or System Preferences on older macOS)"
echo "    2. Go to ${BOLD}Privacy & Security → Accessibility${NC}"
echo "    3. Click the ${BOLD}+${NC} button (or the lock icon to unlock first)"
echo "    4. Add your terminal app (${BOLD}Terminal${NC}, ${BOLD}iTerm2${NC}, etc.)"
echo "    5. Make sure the toggle is ${BOLD}ON${NC}"
echo ""
echo "  Without this, AppleScript keyboard simulation will fail."

# =============================================================================
# 8. Guide Spaces (Mission Control) Setup
# =============================================================================
print_header "Mission Control / Spaces Setup"

echo "  Deassignment uses virtual desktops (Spaces) to switch between"
echo "  your browser and VSCode during automation."
echo ""
echo "  To enable Ctrl+Arrow keyboard shortcuts for desktop switching:"
echo "    1. Open ${BOLD}System Settings${NC}"
echo "    2. Go to ${BOLD}Desktop & Dock → Mission Control${NC}"
echo "    3. Ensure ${BOLD}\"Displays have separate Spaces\"${NC} is checked"
echo "    4. Click ${BOLD}Keyboard Shortcuts...${NC} (or go to Keyboard → Keyboard Shortcuts → Mission Control)"
echo "    5. Enable and set:"
echo "       • ${BOLD}Move left a space${NC}  → Ctrl+Left Arrow  (⌃←)"
echo "       • ${BOLD}Move right a space${NC} → Ctrl+Right Arrow (⌃→)"
echo ""
echo "  Make sure you have at least 2 Spaces/Desktops configured."

# =============================================================================
# 9. Create Python venv and Install Dependencies
# =============================================================================
print_header "Setting up Python Virtual Environment"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 -m venv "$SCRIPT_DIR/venv"
print_ok "Virtual environment created at $SCRIPT_DIR/venv"

echo "  Installing Python dependencies..."
"$SCRIPT_DIR/venv/bin/pip" install --upgrade pip
"$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
print_ok "Python dependencies installed"

# =============================================================================
# 10. AppleScript Smoke Test
# =============================================================================
print_header "Running AppleScript Smoke Test"

echo "  Testing if we can communicate with System Events via AppleScript..."
if RESULT=$(osascript -e 'tell application "System Events" to return name of first process' 2>&1); then
    print_ok "AppleScript test passed. System Events responded: \"$RESULT\""
else
    print_warn "AppleScript test failed: $RESULT"
    echo "       This likely means Accessibility permissions have not been granted."
    echo "       Please follow the Accessibility Permissions instructions above."
fi

# =============================================================================
# 11. Completion Summary
# =============================================================================
echo ""
echo -e "${GREEN}${BOLD}=============================================${NC}"
echo -e "${GREEN}${BOLD}  macOS Installation Complete!${NC}"
echo -e "${GREEN}${BOLD}=============================================${NC}"
echo ""
echo "  Before you start, make sure you have:"
echo "    ✔ Granted Accessibility permissions to your terminal app"
echo "    ✔ Set up Mission Control keyboard shortcuts (Ctrl+Arrow)"
echo "    ✔ VSCode installed with the 'code' command in your PATH"
echo "    ✔ At least 2 virtual desktops (Spaces) configured"
echo ""
echo "  To start the application, run:"
echo -e "    ${BOLD}$SCRIPT_DIR/venv/bin/python app.py${NC}"
echo ""
echo "  Then open your browser to: ${BOLD}http://127.0.0.1:5000${NC}"
echo ""
