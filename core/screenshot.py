import os
import subprocess
import time
import logging

logger = logging.getLogger("deassignment.screenshot")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [SCREENSHOT] %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)


class ScreenshotFactory:
    @staticmethod
    def get_screenshotter():
        from core.platform_detect import get_platform
        platform = get_platform()
        if platform == 'macos':
            logger.info("Using MacOSScreenshot (screencapture)")
            return MacOSScreenshot()
        elif platform == 'wayland':
            logger.info("Using WaylandScreenshot (grim)")
            return WaylandScreenshot()
        logger.info("Using X11Screenshot (scrot)")
        return X11Screenshot()

class X11Screenshot:
    """Handles screenshot capture on Linux (X11)."""

    @staticmethod
    def capture_active_window(output_path: str) -> bool:
        logger.info(f"Capturing active window screenshot to: {output_path}")
        try:
            subprocess.run(["scrot", "-u", output_path], check=True, stderr=subprocess.PIPE)
            logger.info("Screenshot captured successfully via scrot")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"scrot failed: {e.stderr.decode()}, trying fallback with import")
            try:
                window_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()
                subprocess.run(["import", "-window", window_id, output_path], check=True)
                logger.info("Screenshot captured via import fallback")
                return True
            except Exception as ex:
                logger.error(f"Fallback screenshot method also failed: {ex}")
                return False
        except FileNotFoundError:
            logger.error("scrot is not installed!")
            return False

class WaylandScreenshot:
    """Handles screenshot capture on Linux (Wayland)."""

    @staticmethod
    def capture_active_window(output_path: str) -> bool:
        logger.info(f"Capturing Wayland screenshot to: {output_path}")
        
        # Strategy 1: grim (works on wlroots based compositors like Sway, Hyprland, and some KDE)
        try:
            subprocess.run(["grim", output_path], check=True, stderr=subprocess.PIPE)
            logger.info("Full-screen screenshot captured via grim")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"grim failed or not found: {e}. Trying GNOME fallback...")
            
        # Strategy 2: gnome-screenshot (works on GNOME Wayland if installed)
        try:
            subprocess.run(["gnome-screenshot", "-f", output_path], check=True, stderr=subprocess.PIPE)
            logger.info("Screenshot captured via gnome-screenshot fallback")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"gnome-screenshot failed or not found: {e}")
            logger.error("Wayland screenshot failed. If you are on GNOME, try installing 'gnome-screenshot' or switch to an X11 session.")
            return False


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
                    logger.debug(f"Found VSCode window ID: {window_id}")
                    return window_id
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug(f"Could not get VSCode window ID: {e}")
        return None

    @staticmethod
    def capture_active_window(output_path: str) -> bool:
        logger.info(f"Capturing macOS screenshot to: {output_path}")

        # Strategy 1: Capture specific VSCode window by ID
        window_id = MacOSScreenshot._get_vscode_window_id()
        if window_id:
            try:
                subprocess.run(
                    ["screencapture", "-o", "-l", window_id, output_path],
                    check=True, stderr=subprocess.PIPE, timeout=10
                )
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"Window screenshot captured via screencapture -l {window_id}")
                    return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                logger.debug(f"screencapture -l failed: {e}. Trying full-screen fallback...")

        # Strategy 2: Full-screen capture (fallback)
        try:
            subprocess.run(
                ["screencapture", "-o", output_path],
                check=True, stderr=subprocess.PIPE, timeout=10
            )
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info("Full-screen screenshot captured via screencapture")
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"screencapture failed: {e}")

        logger.error("macOS screenshot capture failed entirely.")
        return False

