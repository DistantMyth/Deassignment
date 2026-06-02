import subprocess
import time
import os
import logging

# Setup a dedicated logger for automation
logger = logging.getLogger("deassignment.automator")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [AUTOMATOR] %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)


class DesktopAutomatorFactory:
    """Factory to return the appropriate automator based on the display server."""
    
    @staticmethod
    def get_automator(config: dict):
        session = os.environ.get("XDG_SESSION_TYPE", "")
        logger.info(f"Detected session type: '{session}'")
        if session == "wayland":
            logger.info("Using WaylandAutomator (ydotool + wl-clipboard)")
            return WaylandAutomator(config)
        logger.info("Using X11Automator (xdotool + xclip)")
        return X11Automator(config)


class BaseAutomator:
    def __init__(self, config: dict):
        self.config = config
        self.delay = config.get("DELAY_BETWEEN_ACTIONS", 1.0)

    def _run(self, cmd: list, check=True) -> str:
        cmd_str = ' '.join(cmd)
        logger.debug(f"Running: {cmd_str}")
        try:
            result = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout = result.stdout.decode().strip()
            stderr = result.stderr.decode().strip()
            if stdout:
                logger.debug(f"  stdout: {stdout[:200]}")
            if stderr:
                logger.warning(f"  stderr: {stderr[:200]}")
            return stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command FAILED: {cmd_str}")
            logger.error(f"  exit code: {e.returncode}")
            logger.error(f"  stderr: {e.stderr.decode()[:500]}")
            raise

    def get_current_desktop(self) -> int:
        raise NotImplementedError()

    def switch_desktop_forward(self):
        """Switch one desktop to the right (towards VSCode)."""
        raise NotImplementedError()

    def switch_desktop_back(self):
        """Switch one desktop to the left (back to original)."""
        raise NotImplementedError()

    def open_file_in_vscode(self, filepath: str):
        """Opens a file in VSCode using the CLI. (Universal across display servers)"""
        logger.info(f"Opening file in VSCode: {filepath}")
        subprocess.run(["code", filepath])
        time.sleep(2.5)
        self.focus_vscode()
        
    def focus_vscode(self) -> bool:
        raise NotImplementedError()

    def focus_terminal(self):
        """Focus the integrated terminal in VSCode. Subclasses implement this."""
        raise NotImplementedError()

    def clipboard_copy(self, text: str):
        """Copy text to clipboard. Subclasses implement this."""
        raise NotImplementedError()
    
    def simulate_paste_in_terminal(self):
        """Simulate Ctrl+Shift+V (terminal paste). Subclasses implement this."""
        raise NotImplementedError()
        
    def simulate_enter(self):
        """Simulate pressing Enter. Subclasses implement this."""
        raise NotImplementedError()

    def simulate_typing(self, text: str):
        """Simulate typing text character by character. Subclasses implement this."""
        raise NotImplementedError()
        
    def close_terminal(self):
        """Close the integrated terminal by sending 'exit' and Enter."""
        logger.info("Closing terminal by sending 'exit'")
        self.clipboard_copy("exit")
        time.sleep(0.3)
        self.simulate_paste_in_terminal()
        time.sleep(0.3)
        self.simulate_enter()
        time.sleep(self.delay)

    def run_commands_in_terminal(self, cmd_string: str):
        """
        Focus the VSCode terminal, paste a command, and press Enter.
        """
        logger.info(f"Running in terminal: {cmd_string[:100]}...")
        
        logger.debug("Step 1: Focusing VSCode window")
        self.focus_vscode()
        time.sleep(0.5)
        
        logger.debug("Step 2: Opening/focusing integrated terminal")
        self.focus_terminal()
        time.sleep(self.delay * 2)
        
        logger.debug("Step 3: Copying command to clipboard")
        self.clipboard_copy(cmd_string)
        time.sleep(0.3)
        
        logger.debug("Step 4: Pasting from clipboard (Ctrl+Shift+V for terminal)")
        self.simulate_paste_in_terminal()
        time.sleep(0.5)
        
        logger.debug("Step 5: Pressing Enter to execute")
        self.simulate_enter()
        logger.info("Command sent to terminal successfully")
        
    def close_active_tab(self):
        raise NotImplementedError()


class X11Automator(BaseAutomator):
    """Handles Linux desktop automation using xdotool (X11 only)."""
    
    def get_current_desktop(self) -> int:
        desktop = int(self._run(["xdotool", "get_desktop"]))
        logger.info(f"Current desktop: {desktop}")
        return desktop

    def switch_desktop_forward(self):
        logger.info("X11: Switching desktop forward")
        shortcut = self.config.get("shortcut_right", "ctrl+shift+Right")
        self._run(["xdotool", "key", "--clearmodifiers", shortcut])
        time.sleep(self.delay)

    def switch_desktop_back(self):
        logger.info("X11: Switching desktop back")
        shortcut = self.config.get("shortcut_left", "ctrl+shift+Left")
        self._run(["xdotool", "key", "--clearmodifiers", shortcut])
        time.sleep(self.delay)

    def focus_vscode(self) -> bool:
        logger.debug("Focusing VSCode via xdotool search --class code")
        try:
            stdout = self._run(["xdotool", "search", "--class", "code"])
            if not stdout:
                logger.warning("No VSCode window found!")
                return False
            window_id = stdout.split('\n')[0]
            logger.debug(f"Found VSCode window ID: {window_id}")
            self._run(["xdotool", "windowactivate", "--sync", window_id])
            time.sleep(self.delay)
            return True
        except Exception as e:
            logger.error(f"Failed to focus VSCode: {e}")
            return False

    def focus_terminal(self):
        logger.debug("Sending Ctrl+Shift+` to create/focus terminal")
        self._run(["xdotool", "key", "--clearmodifiers", "ctrl+shift+grave"])
        time.sleep(self.delay)

    def clipboard_copy(self, text: str):
        logger.debug(f"Copying to X11 clipboard via xclip ({len(text)} chars)")
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=text.encode())

    def simulate_paste_in_terminal(self):
        """Ctrl+Shift+V for terminal paste (Ctrl+V is 'lnext' in terminals)"""
        self._run(["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"])

    def simulate_enter(self):
        self._run(["xdotool", "key", "Return"])

    def simulate_typing(self, text: str):
        logger.debug(f"X11: Typing {len(text)} characters")
        proc = subprocess.Popen(
            ["xdotool", "type", "--delay", "50", "--file", "-"],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=text.encode())

    def close_active_tab(self):
        logger.debug("Closing active tab: Ctrl+W")
        self._run(["xdotool", "key", "--clearmodifiers", "ctrl+w"])
        time.sleep(self.delay)


# ydotool keycode reference (from /usr/include/linux/input-event-codes.h):
#   KEY_LEFTCTRL  = 29
#   KEY_LEFTSHIFT = 42
#   KEY_LEFTALT   = 56
#   KEY_LEFTMETA  = 125 (Windows/Super key)
#   KEY_GRAVE     = 41  (backtick `)
#   KEY_V         = 47
#   KEY_W         = 17
#   KEY_ENTER     = 28
#   KEY_LEFT      = 105
#   KEY_RIGHT     = 106

class WaylandAutomator(BaseAutomator):
    """Handles Linux desktop automation using ydotool and wl-clipboard (Wayland).
    
    ydotool uses raw Linux input keycodes, NOT symbolic names.
    Syntax: keycode:1 (press) keycode:0 (release)
    """

    def _ydotool_combo(self, *keycodes):
        """
        Simulate a key combination using ydotool raw keycodes.
        Press all keys in order, then release in reverse order.
        e.g., _ydotool_combo(29, 42, 41) = Ctrl+Shift+Grave
        """
        sequence = []
        for kc in keycodes:
            sequence.append(f"{kc}:1")  # press
        for kc in reversed(keycodes):
            sequence.append(f"{kc}:0")  # release
        
        key_names = {29: "CTRL", 42: "SHIFT", 56: "ALT", 125: "SUPER",
                     41: "GRAVE", 47: "V", 17: "W", 28: "ENTER",
                     105: "LEFT", 106: "RIGHT"}
        combo_name = "+".join(key_names.get(kc, str(kc)) for kc in keycodes)
        logger.debug(f"ydotool combo: {combo_name} -> ydotool key {' '.join(sequence)}")
        
        self._run(["ydotool", "key"] + sequence)

    def get_current_desktop(self) -> int:
        logger.info("Wayland: get_current_desktop not available, returning 0")
        return 0

    _keycode_map = {
        "ctrl": 29, "control": 29,
        "shift": 42,
        "alt": 56,
        "super": 125, "meta": 125, "win": 125,
        "left": 105, "right": 106,
        "up": 103, "down": 108,
        "pageup": 104, "pagedown": 109,
    }

    def _parse_shortcut(self, shortcut: str) -> list:
        """Parse a human-readable shortcut like 'ctrl+meta+Right' into ydotool keycodes."""
        parts = [p.strip().lower() for p in shortcut.split("+")]
        keycodes = []
        for p in parts:
            kc = self._keycode_map.get(p)
            if kc is None:
                logger.warning(f"Unknown key in shortcut: '{p}', skipping")
                continue
            keycodes.append(kc)
        return keycodes

    def switch_desktop_forward(self):
        """Switch one desktop to the right using the user's shortcut."""
        shortcut = self.config.get("shortcut_right", "super+Right")
        logger.info(f"Switching desktop FORWARD with: {shortcut}")
        keycodes = self._parse_shortcut(shortcut)
        if keycodes:
            self._ydotool_combo(*keycodes)
        else:
            logger.error(f"Could not parse shortcut: {shortcut}")
        time.sleep(self.delay)

    def switch_desktop_back(self):
        """Switch one desktop to the left using the user's shortcut."""
        shortcut = self.config.get("shortcut_left", "super+Left")
        logger.info(f"Switching desktop BACK with: {shortcut}")
        keycodes = self._parse_shortcut(shortcut)
        if keycodes:
            self._ydotool_combo(*keycodes)
        else:
            logger.error(f"Could not parse shortcut: {shortcut}")
        time.sleep(self.delay)

    def focus_vscode(self) -> bool:
        logger.debug("Wayland: relying on 'code <file>' to grab focus")
        return True

    def focus_terminal(self):
        """Open/focus VSCode integrated terminal: Ctrl+Shift+Grave"""
        logger.debug("Sending Ctrl+Shift+Grave via ydotool to open terminal")
        self._ydotool_combo(29, 42, 41)  # CTRL + SHIFT + GRAVE
        time.sleep(self.delay)

    def clipboard_copy(self, text: str):
        """Copy text to Wayland clipboard using wl-copy via stdin."""
        logger.debug(f"Copying to Wayland clipboard via wl-copy ({len(text)} chars)")
        proc = subprocess.Popen(
            ["wl-copy"],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=text.encode())

    def simulate_paste_in_terminal(self):
        """Simulate Ctrl+Shift+V (terminal paste — Ctrl+V is 'lnext' in terminals)"""
        self._ydotool_combo(29, 42, 47)  # CTRL + SHIFT + V

    def simulate_enter(self):
        """Simulate Enter key"""
        self._ydotool_combo(28)  # ENTER

    def simulate_typing(self, text: str):
        """Type text using ydotool type via stdin"""
        logger.debug(f"Wayland: Typing {len(text)} characters")
        proc = subprocess.Popen(
            ["ydotool", "type", "-d", "50", "-f", "-"],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=text.encode())

    def close_active_tab(self):
        """Close active tab: Ctrl+W"""
        logger.debug("Closing active tab: Ctrl+W via ydotool")
        self._ydotool_combo(29, 17)  # CTRL + W
        time.sleep(self.delay)
