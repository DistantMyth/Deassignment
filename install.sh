#!/bin/bash
set -e

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

if [ $IS_WAYLAND -eq 1 ]; then
    echo "Checking ydotoold service..."
    if ! systemctl is-active --quiet ydotoold && ! sudo systemctl is-active --quiet ydotoold; then
        echo "WARNING: ydotool requires the ydotoold daemon to be running. Please start it:"
        echo "sudo systemctl enable --now ydotoold"
    fi
fi

# 4. Check for VSCode
if ! command -v code &>/dev/null; then
    echo "WARNING: VSCode ('code' command) not found. This tool requires VSCode to run code."
fi

# 5. Setup Python Virtual Environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 6. Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installation complete!"
echo "To start the application, run: ./venv/bin/python app.py"
