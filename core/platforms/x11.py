import subprocess
import time
import logging
from core.platforms.base import BaseAutomator

logger = logging.getLogger("deassignment.automator")
screenshot_logger = logging.getLogger("deassignment.screenshot")


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


class X11Screenshot:
    """Handles screenshot capture on Linux (X11)."""

    @staticmethod
    def capture_active_window(output_path: str) -> bool:
        screenshot_logger.info(f"Capturing active window screenshot to: {output_path}")
        try:
            subprocess.run(["scrot", "-u", output_path], check=True, stderr=subprocess.PIPE)
            screenshot_logger.info("Screenshot captured successfully via scrot")
            return True
        except subprocess.CalledProcessError as e:
            screenshot_logger.warning(f"scrot failed: {e.stderr.decode()}, trying fallback with import")
            try:
                window_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()
                subprocess.run(["import", "-window", window_id, output_path], check=True)
                screenshot_logger.info("Screenshot captured via import fallback")
                return True
            except Exception as ex:
                screenshot_logger.error(f"Fallback screenshot method also failed: {ex}")
                return False
        except FileNotFoundError:
            screenshot_logger.error("scrot is not installed!")
            return False
