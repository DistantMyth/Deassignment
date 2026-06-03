import subprocess
import time
import os
import logging
from core.platforms.base import BaseAutomator

logger = logging.getLogger("deassignment.automator")
screenshot_logger = logging.getLogger("deassignment.screenshot")


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


class WaylandScreenshot:
    """Handles screenshot capture on Linux (Wayland)."""

    @staticmethod
    def capture_active_window(output_path: str) -> bool:
        screenshot_logger.info(f"Capturing Wayland screenshot to: {output_path}")
        
        # Strategy 1: grim (works on wlroots based compositors like Sway, Hyprland, and some KDE)
        try:
            subprocess.run(["grim", output_path], check=True, stderr=subprocess.PIPE)
            screenshot_logger.info("Full-screen screenshot captured via grim")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            screenshot_logger.debug(f"grim failed or not found: {e}. Trying GNOME fallback...")
            
        # Strategy 2: gnome-screenshot (works on GNOME Wayland if installed)
        try:
            subprocess.run(["gnome-screenshot", "-f", output_path], check=True, stderr=subprocess.PIPE)
            screenshot_logger.info("Screenshot captured via gnome-screenshot fallback")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            screenshot_logger.error(f"gnome-screenshot failed or not found: {e}")
            screenshot_logger.error("Wayland screenshot failed. If you are on GNOME, try installing 'gnome-screenshot' or switch to an X11 session.")
            return False
