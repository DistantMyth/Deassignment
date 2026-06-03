# Deassignment 🚀

An automated, self-hosted web tool that takes programming assignment questions, generates AI prompts, and automates your entire desktop to create a polished PowerPoint presentation containing the questions, syntax-highlighted code, and execution screenshots.

**Works on both X11 and Wayland.**

## Features

- 🪄 **Wizard UI**: A beautiful, step-by-step interface to guide you through the process.
- 🤖 **AI Prompt Generation**: Automatically creates prompts for ChatGPT, Claude, or Gemini in "All at once" or "Step-by-step" modes (to prevent hallucination on large assignments).
- 🖥️ **Full Desktop Automation**: Supports **both X11** (`xdotool`) **and Wayland** (`ydotool`) — switches virtual desktops, focuses VSCode, opens files, runs commands, and takes screenshots.
- 🖼️ **Syntax Highlighting**: Uses `Pygments` to render your code into beautiful, presentation-ready images with automatic font detection and fallback.
- 📊 **PPTX Generation**: Clones the last slide of your provided template and formats the questions, code, and screenshots perfectly within the safe zones.
- ⚡ **Real-time Progress**: Watch the automation happen with live Server-Sent Events (SSE) updates in the browser.
- 💾 **Config Persistence**: Your settings (language, shortcuts, batch size) are remembered across sessions.

## Prerequisites

- **Linux** (X11 or Wayland session)
- **Python 3.8+**
- **Visual Studio Code** (`code` in your PATH)

### X11 Requirements
| Tool | Purpose |
|------|---------|
| `xdotool` | Desktop automation (window focus, keyboard simulation) |
| `scrot` | Screenshot capture |
| `xclip` | Clipboard integration |

### Wayland Requirements
| Tool | Purpose |
|------|---------|
| `ydotool` + `ydotoold` | Desktop automation (keyboard/mouse via uinput) |
| `wl-clipboard` (`wl-copy`) | Clipboard integration |
| `grim` | Screenshot capture |

> **Note:** On Wayland, `ydotool` requires the `ydotoold` daemon to be running and your user must have write access to `/dev/uinput`.

## Quick Start

1. Clone or download this repository.
2. Run the installation script (this will create a virtual environment, install Python packages, and set up the required system tools):
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. Start the application:
   ```bash
   ./venv/bin/python app.py
   ```
4. Open your browser and go to: **http://127.0.0.1:5000**

## How to Use

### 1. System Check
The app will verify you have the required tools installed. It auto-detects whether you're running X11 or Wayland and checks for the appropriate tools. If anything fails, follow the on-screen instructions.

### 2. Configuration
- Select your programming language (Python, C, C++, Java, JS).
- Enter the total number of questions.
- Select your AI prompting mode. For large assignments (>15 questions), **Step-by-step** is highly recommended to prevent the AI from making mistakes or running out of context.
- Ensure the desktop switching shortcuts match your system's settings.

> **Tip:** Your configuration is automatically saved and restored on your next visit.

### 3. Template Upload
Upload a `.pptx` file. 
**Important:** The tool uses the **last slide** of your presentation as the template for all generated content. Make sure the last slide has the styling/background you want.

### 4. AI Prompting
1. Click the copy button to copy the generated prompt.
2. Paste it into your preferred AI (ChatGPT, Claude, etc.) along with your questions document.
3. Wait for the response, copy the JSON, and paste it into the "Paste AI Response" box.
4. Click **Validate & Save**. (If using step-by-step mode, repeat this for each batch).

### 5. Pre-flight Checklist & Execution
Before you start, make sure:
1. VSCode is open on a **different virtual desktop** (usually Desktop 2).
2. You don't have unsaved work open in VSCode.
3. The integrated terminal in VSCode is open (or can be opened with ``Ctrl+` ``).

Click **Start Automation** and **TAKE YOUR HANDS OFF THE KEYBOARD AND MOUSE**.
The tool will take over, write the code, run it, take screenshots, and compile the presentation. You can watch the progress live in your browser.

## Wayland Setup Guide

If you're on Wayland (GNOME 43+, KDE Plasma 6, Sway, Hyprland, etc.), you need a few extra steps:

### 1. Install Dependencies
```bash
# Fedora
sudo dnf install ydotool wl-clipboard grim

# Ubuntu/Debian
sudo apt install ydotool wl-clipboard grim

# Arch
sudo pacman -S ydotool wl-clipboard grim
```

### 2. Start the ydotoold Daemon
```bash
sudo systemctl enable --now ydotoold
```

### 3. Set Up /dev/uinput Permissions
```bash
# Add your user to the input group
sudo usermod -aG input $USER

# Create a udev rule (one-time)
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/80-uinput.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# Log out and back in for group changes to take effect
```

### 4. Desktop Shortcuts
Common Wayland desktop switching shortcuts:
- **GNOME:** `super+Left` / `super+Right` (with workspaces set to horizontal)
- **KDE Plasma:** `meta+Left` / `meta+Right`
- **Sway/Hyprland:** Custom key bindings (check your config)

Enter your shortcuts in the Configuration step.

## Troubleshooting

### General
- **"xdotool fails to type code correctly"**: We solved this! The app now writes files directly to disk and opens them, avoiding typing simulation issues entirely.
- **"Screenshots show the wrong window"**: Make sure you leave your mouse alone during execution. `scrot -u` captures the currently focused window.
- **"VSCode terminal isn't opening"**: Ensure your VSCode terminal shortcut is `ctrl+` (backtick) or update the setting in `config/defaults.py`.
- **"Code runs but closes immediately / no screenshot"**: You can increase the `EXECUTION_TIMEOUT` in `config/defaults.py`.

### Wayland-Specific
- **"ydotool: command failed (exit code 2)"**: This is a permissions issue. Make sure:
  1. `ydotoold` daemon is running: `sudo systemctl status ydotoold`
  2. Your user is in the `input` group: `groups $USER`
  3. `/dev/uinput` is writable: `ls -la /dev/uinput`
  4. You logged out and back in after adding yourself to the group.

- **"ydotoold is not starting automatically"**: The app will attempt to auto-start it, but if that fails:
  ```bash
  sudo systemctl enable --now ydotoold
  ```

- **"No usable fonts named: DejaVu Sans Mono"**: Install the font:
  ```bash
  # Fedora
  sudo dnf install dejavu-sans-mono-fonts
  
  # Ubuntu/Debian
  sudo apt install fonts-dejavu-core
  
  # Arch
  sudo pacman -S ttf-dejavu
  ```
  The app now auto-detects available monospace fonts, so this error should be rare.

## Future Roadmap

- macOS Support (via AppleScript)
- Windows Support (via PyAutoGUI/PowerShell)
- Direct API Integration for the AI generation step.
