# Deassignment 🚀

An automated, self-hosted web tool that takes programming assignment questions, generates AI prompts, and automates your entire desktop to create a polished PowerPoint presentation containing the questions, syntax-highlighted code, and execution screenshots.

**Works on Linux (X11 & Wayland) and macOS.**

## Features

- 🪄 **Wizard UI**: A beautiful, step-by-step interface to guide you through the process.
- 🤖 **AI Prompt Generation**: Automatically creates prompts for ChatGPT, Claude, or Gemini in "All at once" or "Step-by-step" modes (to prevent hallucination on large assignments).
- 🖥️ **Full Desktop Automation**: Supports **X11**, **Wayland**, and **macOS** natively — switches virtual desktops, focuses VSCode, opens files, runs commands, and takes screenshots.
- 🖼️ **Syntax Highlighting**: Uses `Pygments` to render your code into beautiful, presentation-ready images with automatic font detection and fallback.
- 📊 **PPTX Generation**: Clones the last slide of your provided template and formats the questions, code, and screenshots perfectly within the safe zones.
- ⚡ **Real-time Progress**: Watch the automation happen with live Server-Sent Events (SSE) updates in the browser.
- 💾 **Config Persistence**: Your settings (language, shortcuts, batch size) are remembered across sessions.

## Quick Start

1. Clone or download this repository.
2. Run the installation script. The script automatically detects your OS and installs the required packages and sets up the Python virtual environment:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. Start the application:
   ```bash
   ./venv/bin/python app.py
   ```
4. Open your browser and go to: **http://127.0.0.1:5000**

## Platform Setup & Permissions

Deassignment uses native tools for your specific display server or OS. Review the requirements and setup for your platform:

### macOS (12 Monterey+)
All required tools are **built-in** (`osascript`, `screencapture`, `pbcopy`).
- **Permissions**: You MUST grant **Accessibility** and **Screen Recording** permissions to your terminal app (e.g., Terminal, iTerm2) in **System Settings → Privacy & Security**. Without Accessibility, keyboard simulation will fail.
- **Shortcuts**: Enable Mission Control desktop switching in **System Settings → Desktop & Dock → Mission Control**. The defaults are usually `Ctrl+Left` and `Ctrl+Right`.

### Linux (Wayland)
Requires `ydotool`, `wl-clipboard`, and `grim`.
- **ydotoold daemon**: The `ydotoold` daemon must be running (`sudo systemctl enable --now ydotoold`).
- **Permissions**: Your user must have write access to `/dev/uinput`. To do this, add yourself to the input group:
  ```bash
  sudo usermod -aG input $USER
  ```
  *(Remember to log out and log back in for group changes to take effect).*
- **Shortcuts**: Common Wayland shortcuts use the Super/Meta key (e.g., `super+Left`, `super+Right`).

### Linux (X11)
Requires `xdotool`, `scrot`, and `xclip`.
- Usually, these work out of the box without special daemons or permissions.
- **Shortcuts**: Usually `ctrl+alt+Left/Right` or `ctrl+shift+Left/Right`.

## How to Use

### 1. System Check
The app will verify you have the required tools installed. It auto-detects your platform and checks for the appropriate tools. If anything fails, follow the on-screen instructions.

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

## Troubleshooting

### General
- **"xdotool fails to type code correctly"**: We solved this! The app now writes files directly to disk and opens them, avoiding typing simulation issues entirely.
- **"Screenshots show the wrong window"**: Make sure you leave your mouse alone during execution. The tools capture the currently focused window.
- **"VSCode terminal isn't opening"**: Ensure your VSCode terminal shortcut is `ctrl+` (backtick) or update the setting in `config/defaults.py`.
- **"Code runs but closes immediately / no screenshot"**: You can increase the `EXECUTION_TIMEOUT` in `config/defaults.py`.

### macOS
- **"Not authorized to send Apple events"**: Grant Accessibility permissions: System Settings → Privacy & Security → Accessibility → Add your terminal app.
- **"Desktop switching doesn't work"**: Enable Mission Control shortcuts: System Settings → Desktop & Dock → Mission Control → Enable "Switch to Desktop" shortcuts, and ensure Ctrl+Left/Right are set.
- **"screencapture fails"**: Grant Screen Recording permission: System Settings → Privacy & Security → Screen Recording → Add your terminal app.
- **"Font not found" warnings**: macOS uses Menlo as the default monospace font. To use DejaVu Sans Mono, install it via: `brew install --cask font-dejavu-sans-mono`.

### Wayland
- **"ydotool: command failed (exit code 2)"**: This is a permissions issue. Make sure:
  1. `ydotoold` daemon is running: `sudo systemctl status ydotoold`
  2. Your user is in the `input` group: `groups $USER`
  3. `/dev/uinput` is writable: `ls -la /dev/uinput`
  4. You logged out and back in after adding yourself to the group.
- **"No usable fonts named: DejaVu Sans Mono"**: The app auto-detects monospace fonts, but you can install it via your package manager (e.g. `sudo dnf install dejavu-sans-mono-fonts`).

## Future Roadmap

- Windows Support (via PyAutoGUI/PowerShell)
- Direct API Integration for the AI generation step.
