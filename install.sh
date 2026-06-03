#!/bin/bash
set -e

# Detect macOS and redirect to macOS-specific installer
if [[ "$(uname)" == "Darwin" ]]; then
    echo "macOS detected. Running macOS installer..."
    bash "$(dirname "$0")/install_macos.sh"
    exit $?
fi

echo "Starting Deassignment Installation..."

# 1. Check Python version
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "Found Python $PY_VER"
else
    echo "Python 3 is required but not found. Please install Python 3.8+"
    exit 1
fi

# 2. Check X11 vs Wayland and Set Required Tools
IS_WAYLAND=0
if [ "$XDG_SESSION_TYPE" == "wayland" ]; then
    echo "Wayland session detected."
    IS_WAYLAND=1
    REQUIRED_TOOLS="ydotool wl-copy grim slurp xdg-utils"
else
    echo "X11 session detected."
    REQUIRED_TOOLS="xdotool scrot xclip xdg-utils"
fi

# 3. Check for required system tools
TOOLS_MISSING=0
for tool in $REQUIRED_TOOLS; do
    if ! command -v $tool &>/dev/null; then
        echo "Missing system tool: $tool"
        TOOLS_MISSING=1
    fi
done

if [ $TOOLS_MISSING -eq 1 ]; then
    echo "Attempting to install missing system tools..."
    
    # Determine packages to install
    if [ $IS_WAYLAND -eq 1 ]; then
        PACKAGES="ydotool wl-clipboard grim slurp xdg-utils"
    else
        PACKAGES="xdotool scrot xclip xdg-utils"
    fi

    # Detect package manager and install
    if command -v apt-get &>/dev/null; then
        echo "Detected apt (Debian/Ubuntu). Installing packages..."
        sudo apt-get update
        sudo apt-get install -y $PACKAGES
    elif command -v dnf &>/dev/null; then
        echo "Detected dnf (Fedora). Installing packages..."
        sudo dnf install -y $PACKAGES
    elif command -v pacman &>/dev/null; then
        echo "Detected pacman (Arch). Installing packages..."
        sudo pacman -Sy --noconfirm $PACKAGES
    else
        echo "Could not auto-install tools (no supported package manager found). Please install the following tools manually:"
        echo "$PACKAGES"
        exit 1
    fi
fi

# 4. Install monospace fonts for code rendering
echo "Ensuring monospace fonts are available..."
if ! fc-list "DejaVu Sans Mono" | grep -q .; then
    echo "DejaVu Sans Mono not found, installing..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y fonts-dejavu-core
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y dejavu-sans-mono-fonts
    elif command -v pacman &>/dev/null; then
        sudo pacman -Sy --noconfirm ttf-dejavu
    else
        echo "WARNING: Could not install DejaVu Sans Mono. Code screenshots may use a fallback font."
    fi
else
    echo "DejaVu Sans Mono is already installed."
fi

# 5. Wayland-specific setup: ydotoold & uinput permissions
if [ $IS_WAYLAND -eq 1 ]; then
    echo ""
    echo "=== Wayland-specific setup ==="
    
    # Enable and start ydotoold
    echo "Enabling and starting ydotoold service..."
    if systemctl list-unit-files | grep -q ydotoold; then
        sudo systemctl enable --now ydotoold 2>/dev/null || true
        echo "ydotoold service enabled."
    else
        echo "ydotoold systemd service not found. You may need to start it manually: sudo ydotoold &"
    fi

    # Setup /dev/uinput permissions
    echo "Setting up /dev/uinput access..."
    CURRENT_USER=$(whoami)
    
    # Add user to input group
    if ! groups "$CURRENT_USER" | grep -q '\binput\b'; then
        echo "Adding $CURRENT_USER to 'input' group..."
        sudo usermod -aG input "$CURRENT_USER"
        echo "NOTE: You need to log out and back in for group changes to take effect."
    else
        echo "User is already in the 'input' group."
    fi

    # Create udev rule for uinput
    UDEV_RULE="/etc/udev/rules.d/80-uinput.rules"
    if [ ! -f "$UDEV_RULE" ]; then
        echo "Creating udev rule for uinput access..."
        echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee "$UDEV_RULE" > /dev/null
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo "udev rule created. A reboot may be required for full effect."
    else
        echo "udev rule already exists."
    fi
    
    echo "=== Wayland setup complete ==="
    echo ""
fi

# 6. Check for VSCode
if ! command -v code &>/dev/null; then
    echo "WARNING: VSCode ('code' command) not found. This tool requires VSCode to run code."
fi

# 7. Setup Python Virtual Environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 8. Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "============================================="
echo "  Installation complete!"
echo "============================================="
echo ""
echo "To start the application, run:"
echo "  ./venv/bin/python app.py"
echo ""
if [ $IS_WAYLAND -eq 1 ]; then
    echo "Wayland detected. Make sure:"
    echo "  1. ydotoold is running: sudo systemctl status ydotoold"
    echo "  2. You are in the 'input' group: groups \$USER"
    echo "  3. If you just added yourself to the group, log out and back in."
fi
