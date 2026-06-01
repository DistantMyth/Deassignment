# Deassignment 🚀

An automated, self-hosted web tool that takes programming assignment questions, generates AI prompts, and automates your entire desktop to create a polished PowerPoint presentation containing the questions, syntax-highlighted code, and execution screenshots.

## Features

- 🪄 **Wizard UI**: A beautiful, step-by-step interface to guide you through the process.
- 🤖 **AI Prompt Generation**: Automatically creates prompts for ChatGPT, Claude, or Gemini in "All at once" or "Step-by-step" modes (to prevent hallucination on large assignments).
- 🖥️ **Full Desktop Automation**: Uses `xdotool` on Linux to switch virtual desktops, focus VSCode, open files, run commands, and take screenshots.
- 🖼️ **Syntax Highlighting**: Uses `Pygments` to render your code into beautiful, presentation-ready images rather than plain text.
- 📊 **PPTX Generation**: Clones the last slide of your provided template and formats the questions, code, and screenshots perfectly within the safe zones.
- ⚡ **Real-time Progress**: Watch the automation happen with live Server-Sent Events (SSE) updates in the browser.

## Prerequisites

Deassignment currently relies on X11 for desktop automation and is designed for Linux.

- **Linux with X11** (Wayland is *not* supported. If you use Wayland, you must log out and select an "Xorg" or "X11" session).
- **Python 3.8+**
- **Visual Studio Code** (`code` in your PATH)

## Quick Start

1. Clone or download this repository.
2. Run the installation script (this will create a virtual environment, install Python packages, and attempt to install `xdotool`, `scrot`, and `xclip` if missing):
   ```bash
   ./install.sh
   ```
3. Start the application:
   ```bash
   ./venv/bin/python app.py
   ```
4. Open your browser and go to: **http://127.0.0.1:5000**

## How to Use

### 1. System Check
The app will verify you have the required tools installed. If anything fails, follow the on-screen instructions.

### 2. Configuration
- Select your programming language (Python, C, C++, Java, JS).
- Enter the total number of questions.
- Select your AI prompting mode. For large assignments (>15 questions), **Step-by-step** is highly recommended to prevent the AI from making mistakes or running out of context.
- Ensure the desktop switching shortcuts match your system's settings.

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

- **"xdotool fails to type code correctly"**: We solved this! The app now writes files directly to disk and opens them, avoiding typing simulation issues entirely.
- **"Screenshots show the wrong window"**: Make sure you leave your mouse alone during execution. `scrot -u` captures the currently focused window.
- **"VSCode terminal isn't opening"**: Ensure your VSCode terminal shortcut is `ctrl+` (backtick) or update the setting in `config/defaults.py`.
- **"Code runs but closes immediately / no screenshot"**: You can increase the `EXECUTION_TIMEOUT` in `config/defaults.py`.

## Future Roadmap

- macOS Support (via AppleScript)
- Windows Support (via PyAutoGUI/PowerShell)
- Direct API Integration for the AI generation step.
