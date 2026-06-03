import subprocess
import sys
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
        from core.platform_detect import get_platform
        platform = get_platform()
        logger.info(f"Detected platform: '{platform}'")
        if platform == 'macos':
            logger.info("Using MacOSAutomator (AppleScript + pbcopy)")
            return MacOSAutomator(config)
        elif platform == 'wayland':
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

    # Standard socket paths for ydotool 1.0+
    _YDOTOOL_SOCKET_PATHS = [
        "/tmp/.ydotool_socket",
        os.path.expanduser("~/.ydotool_socket"),
        f"/run/user/{os.getuid()}/.ydotool_socket",
    ]

    def __init__(self, config: dict):
        super().__init__(config)
        self._ydotool_env = os.environ.copy()
        self._ensure_ydotoold()

    def _find_socket(self):
        """Find a ydotool socket that the current user can access."""
        # Check YDOTOOL_SOCKET env first
        env_sock = os.environ.get("YDOTOOL_SOCKET")
        if env_sock and os.path.exists(env_sock) and os.access(env_sock, os.W_OK):
            return env_sock
        for sock in self._YDOTOOL_SOCKET_PATHS:
            if os.path.exists(sock) and os.access(sock, os.W_OK):
                return sock
        return None

    def _ensure_ydotoold(self):
        """Ensure the ydotoold daemon is running AND accessible by this user."""
        # Check /dev/uinput permissions first
        if not os.path.exists("/dev/uinput"):
            logger.error("/dev/uinput does not exist. Try: sudo modprobe uinput")
        elif not os.access("/dev/uinput", os.W_OK):
            logger.warning(
                "/dev/uinput not writable. Fix: sudo usermod -aG input $USER && re-login"
            )

        # If daemon is running, check if the socket is accessible
        if self._is_ydotoold_running():
            sock = self._find_socket()
            if sock:
                logger.info(f"ydotoold running, using socket: {sock}")
                self._ydotool_env["YDOTOOL_SOCKET"] = sock
                return
            # Daemon running but socket not accessible (root-owned socket problem)
            logger.warning(
                "ydotoold is running but socket is NOT accessible by current user. "
                "This usually means it was started as root. "
                "Killing it and restarting as current user..."
            )
            self._kill_ydotoold()
            time.sleep(0.5)

        # Now start ydotoold as current user (requires /dev/uinput access via input group)
        user_socket = f"/tmp/.ydotool_socket_{os.getuid()}"

        # Strategy 1: Start as current user with explicit socket path
        if os.access("/dev/uinput", os.W_OK):
            for sock_path in [user_socket, "/tmp/.ydotool_socket"]:
                try:
                    # Remove stale socket if exists
                    if os.path.exists(sock_path):
                        try:
                            os.unlink(sock_path)
                        except OSError:
                            continue

                    env = os.environ.copy()
                    env["YDOTOOL_SOCKET"] = sock_path
                    subprocess.Popen(
                        ["ydotoold"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True, env=env
                    )
                    time.sleep(1.0)
                    if self._is_ydotoold_running() and os.path.exists(sock_path) and os.access(sock_path, os.W_OK):
                        logger.info(f"ydotoold started as current user, socket: {sock_path}")
                        self._ydotool_env["YDOTOOL_SOCKET"] = sock_path
                        return
                except (FileNotFoundError, OSError) as e:
                    logger.debug(f"User-level ydotoold start failed with socket {sock_path}: {e}")

        # Strategy 2: systemctl --user
        try:
            subprocess.run(
                ["systemctl", "--user", "start", "ydotoold"],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5
            )
            time.sleep(0.5)
            if self._is_ydotoold_running():
                sock = self._find_socket()
                if sock:
                    self._ydotool_env["YDOTOOL_SOCKET"] = sock
                    logger.info(f"ydotoold started via systemctl --user, socket: {sock}")
                    return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Strategy 3: sudo (last resort — socket will be root-owned)
        try:
            subprocess.Popen(
                ["sudo", "-n", "ydotoold"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(1.0)
            if self._is_ydotoold_running():
                sock = self._find_socket()
                if sock:
                    self._ydotool_env["YDOTOOL_SOCKET"] = sock
                    logger.info(f"ydotoold started via sudo, socket: {sock}")
                    return
                logger.warning("ydotoold started as root but socket not accessible")
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

        logger.error(
            "FAILED to start ydotoold with an accessible socket.\n"
            "Please start it manually as your own user:\n"
            "  ydotoold &\n"
            "Or if that fails, fix /dev/uinput permissions:\n"
            "  sudo usermod -aG input $USER  # then re-login"
        )

    @staticmethod
    def _kill_ydotoold():
        """Kill any running ydotoold processes."""
        try:
            subprocess.run(["sudo", "-n", "kill", "-9"] +
                           subprocess.check_output(["pgrep", "-x", "ydotoold"]).decode().split(),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(["pkill", "-x", "ydotoold"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

    @staticmethod
    def _is_ydotoold_running() -> bool:
        """Check if ydotoold process is running."""
        try:
            result = subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _run_ydotool(self, cmd: list, check=True) -> str:
        """Run a command with the ydotool socket env set."""
        cmd_str = ' '.join(cmd)
        logger.debug(f"Running (with YDOTOOL_SOCKET): {cmd_str}")
        try:
            result = subprocess.run(cmd, check=check, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=self._ydotool_env)
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

    def _ydotool_run(self, cmd: list, retries: int = 2) -> str:
        """Run a ydotool command with retry logic and clear error messages."""
        for attempt in range(retries + 1):
            try:
                return self._run_ydotool(cmd)
            except subprocess.CalledProcessError as e:
                if e.returncode == 2 and attempt < retries:
                    logger.warning(
                        f"ydotool failed (exit 2), attempt {attempt + 1}/{retries + 1}. "
                        f"Re-checking ydotoold..."
                    )
                    self._ensure_ydotoold()
                    time.sleep(0.5)
                elif e.returncode == 2:
                    raise RuntimeError(
                        f"ydotool command failed after {retries + 1} attempts (exit code 2).\n"
                        f"The ydotoold socket is likely inaccessible.\n"
                        f"Fix: kill any root-owned ydotoold and restart as your user:\n"
                        f"  sudo pkill ydotoold; ydotoold &\n"
                        f"Or fix /dev/uinput: sudo usermod -aG input $USER (then re-login)\n"
                        f"Command: {' '.join(cmd)}"
                    ) from e
                else:
                    raise

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
        
        self._ydotool_run(["ydotool", "key"] + sequence)

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
            stdin=subprocess.PIPE,
            env=self._ydotool_env
        )
        proc.communicate(input=text.encode())

    def close_active_tab(self):
        """Close active tab: Ctrl+W"""
        logger.debug("Closing active tab: Ctrl+W via ydotool")
        self._ydotool_combo(29, 17)  # CTRL + W
        time.sleep(self.delay)
