import subprocess
import time
import os
import logging
from core.platforms.base import BaseAutomator

logger = logging.getLogger("deassignment.automator")
screenshot_logger = logging.getLogger("deassignment.screenshot")


class MacOSAutomator(BaseAutomator):
    """Handles desktop automation on macOS using AppleScript (osascript).

    All automation is done via native macOS tools:
      - osascript (AppleScript) for keyboard simulation and window management
      - pbcopy for clipboard operations
      - screencapture is handled by MacOSScreenshot (in screenshot.py)

    macOS keyboard differences from Linux:
      - Paste in terminal: Cmd+V (not Ctrl+Shift+V)
      - Close tab: Cmd+W (not Ctrl+W)
      - VSCode terminal toggle: Ctrl+` (same as Linux — VSCode uses Ctrl on macOS too)
      - Desktop switching: Ctrl+Left/Right (Mission Control Spaces)
    """

    # AppleScript key code mapping for special keys
    _APPLESCRIPT_KEYCODES = {
        "left": 123,
        "right": 124,
        "down": 125,
        "up": 126,
        "return": 36,
        "enter": 36,
        "tab": 48,
        "escape": 53,
        "delete": 51,
        "grave": 50,
        "`": 50,
        "f1": 122, "f2": 120, "f3": 99, "f4": 118,
        "f5": 96, "f6": 97, "f7": 98, "f8": 100,
    }

    # Modifier name → AppleScript modifier
    _APPLESCRIPT_MODIFIERS = {
        "ctrl": "control down",
        "control": "control down",
        "cmd": "command down",
        "command": "command down",
        "shift": "shift down",
        "alt": "option down",
        "option": "option down",
        "super": "command down",
        "meta": "command down",
    }

    def _osascript(self, script: str) -> str:
        """Run an AppleScript snippet via osascript."""
        cmd = ["osascript", "-e", script]
        logger.debug(f"AppleScript: {script[:120]}")
        try:
            result = subprocess.run(
                cmd, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=10
            )
            stdout = result.stdout.decode().strip()
            if stdout:
                logger.debug(f"  result: {stdout[:200]}")
            return stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"AppleScript FAILED: {script[:120]}")
            logger.error(f"  stderr: {e.stderr.decode()[:500]}")
            raise
        except subprocess.TimeoutExpired:
            logger.error(f"AppleScript TIMED OUT: {script[:120]}")
            raise

    def _keystroke(self, key: str, modifiers: list = None):
        """Simulate a keystroke via AppleScript System Events.

        Args:
            key: A single character to type, or a special key name.
            modifiers: List of modifier strings like ['control down', 'command down'].
        """
        mod_str = ""
        if modifiers:
            mod_str = " using {" + ", ".join(modifiers) + "}"

        # Check if key is a special key that needs 'key code' instead of 'keystroke'
        key_lower = key.lower()
        keycode = self._APPLESCRIPT_KEYCODES.get(key_lower)
        if keycode is not None:
            script = (
                f'tell application "System Events" to '
                f'key code {keycode}{mod_str}'
            )
        else:
            # Escape the key character for AppleScript string
            escaped = key.replace('\\', '\\\\').replace('"', '\\"')
            script = (
                f'tell application "System Events" to '
                f'keystroke "{escaped}"{mod_str}'
            )
        self._osascript(script)

    def _parse_shortcut(self, shortcut: str):
        """Parse a shortcut string like 'ctrl+cmd+Right' into (key, [modifiers]).

        Returns:
            Tuple of (key_name, [applescript_modifier_strings])
        """
        parts = [p.strip() for p in shortcut.split("+")]
        modifiers = []
        key = None
        for p in parts:
            mod = self._APPLESCRIPT_MODIFIERS.get(p.lower())
            if mod:
                if mod not in modifiers:  # avoid duplicates
                    modifiers.append(mod)
            else:
                key = p  # the last non-modifier part is the key
        return key, modifiers

    def get_current_desktop(self) -> int:
        """macOS Spaces index is not easily queryable, return 0."""
        logger.info("macOS: get_current_desktop not queryable, returning 0")
        return 0

    def switch_desktop_forward(self):
        """Switch one Space to the right."""
        shortcut = self.config.get("shortcut_right", "ctrl+Right")
        logger.info(f"macOS: Switching desktop FORWARD with: {shortcut}")
        key, modifiers = self._parse_shortcut(shortcut)
        if key:
            self._keystroke(key, modifiers)
        else:
            # Fallback: Ctrl+Right
            self._keystroke("right", ["control down"])
        time.sleep(self.delay + 0.3)  # Spaces animation takes a moment

    def switch_desktop_back(self):
        """Switch one Space to the left."""
        shortcut = self.config.get("shortcut_left", "ctrl+Left")
        logger.info(f"macOS: Switching desktop BACK with: {shortcut}")
        key, modifiers = self._parse_shortcut(shortcut)
        if key:
            self._keystroke(key, modifiers)
        else:
            # Fallback: Ctrl+Left
            self._keystroke("left", ["control down"])
        time.sleep(self.delay + 0.3)

    def open_file_in_vscode(self, filepath: str):
        """Opens a file in VSCode. On macOS, uses 'code' CLI + AppleScript activate."""
        logger.info(f"macOS: Opening file in VSCode: {filepath}")
        subprocess.run(["code", filepath])
        time.sleep(2.5)
        self.focus_vscode()

    def focus_vscode(self) -> bool:
        """Focus VSCode window using AppleScript."""
        logger.debug("macOS: Focusing VSCode via AppleScript")
        try:
            self._osascript('tell application "Visual Studio Code" to activate')
            time.sleep(self.delay)
            return True
        except Exception as e:
            logger.error(f"Failed to focus VSCode: {e}")
            return False

    def focus_terminal(self):
        """Open/focus the VSCode integrated terminal: Ctrl+` (same on macOS)."""
        logger.debug("macOS: Sending Ctrl+` to open/focus terminal")
        self._keystroke("`", ["control down"])
        time.sleep(self.delay)

    def clipboard_copy(self, text: str):
        """Copy text to macOS clipboard using pbcopy."""
        logger.debug(f"macOS: Copying to clipboard via pbcopy ({len(text)} chars)")
        proc = subprocess.Popen(
            ["pbcopy"],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=text.encode())

    def simulate_paste_in_terminal(self):
        """Simulate Cmd+V to paste in macOS terminal (not Ctrl+Shift+V like Linux)."""
        self._keystroke("v", ["command down"])

    def simulate_enter(self):
        """Simulate pressing Enter/Return."""
        self._keystroke("return")

    def simulate_typing(self, text: str):
        """Type text on macOS.

        For reliability, uses clipboard paste for multi-line text
        and AppleScript keystroke for short single-line text.
        """
        logger.debug(f"macOS: Typing {len(text)} characters")
        if len(text) > 50 or '\n' in text:
            # For longer text, use clipboard paste for reliability
            self.clipboard_copy(text)
            time.sleep(0.2)
            self.simulate_paste_in_terminal()
        else:
            # For short text, type character by character
            # Escape special characters for AppleScript
            for char in text:
                if char == '\n':
                    self._keystroke("return")
                elif char == '\t':
                    self._keystroke("tab")
                else:
                    self._keystroke(char)
                time.sleep(0.05)

    def close_active_tab(self):
        """Close active tab: Cmd+W (macOS uses Cmd instead of Ctrl)."""
        logger.debug("macOS: Closing active tab: Cmd+W")
        self._keystroke("w", ["command down"])
        time.sleep(self.delay)


class MacOSScreenshot:
    """Handles screenshot capture on macOS using native screencapture.

    Primary strategy: Capture the frontmost VSCode window by ID using
    `screencapture -o -l <windowID>` (no shadow, specific window).

    Fallback: Full-screen capture via `screencapture -o`.
    """

    @staticmethod
    def _get_vscode_window_id() -> str:
        """Get the window ID of the frontmost VSCode window via AppleScript."""
        try:
            # Get the window ID of the frontmost window of VSCode
            script = (
                'tell application "System Events" to '
                'get id of first window of '
                '(first application process whose name is "Code")'
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=5
            )
            if result.returncode == 0:
                window_id = result.stdout.decode().strip()
                if window_id:
                    screenshot_logger.debug(f"Found VSCode window ID: {window_id}")
                    return window_id
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            screenshot_logger.debug(f"Could not get VSCode window ID: {e}")
        return None

    @staticmethod
    def capture_active_window(output_path: str) -> bool:
        screenshot_logger.info(f"Capturing macOS screenshot to: {output_path}")

        # Strategy 1: Capture specific VSCode window by ID
        window_id = MacOSScreenshot._get_vscode_window_id()
        if window_id:
            try:
                subprocess.run(
                    ["screencapture", "-o", "-l", window_id, output_path],
                    check=True, stderr=subprocess.PIPE, timeout=10
                )
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    screenshot_logger.info(f"Window screenshot captured via screencapture -l {window_id}")
                    return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                screenshot_logger.debug(f"screencapture -l failed: {e}. Trying full-screen fallback...")

        # Strategy 2: Full-screen capture (fallback)
        try:
            subprocess.run(
                ["screencapture", "-o", output_path],
                check=True, stderr=subprocess.PIPE, timeout=10
            )
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                screenshot_logger.info("Full-screen screenshot captured via screencapture")
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            screenshot_logger.error(f"screencapture failed: {e}")

        screenshot_logger.error("macOS screenshot capture failed entirely.")
        return False
