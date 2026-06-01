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
        if os.environ.get("XDG_SESSION_TYPE", "") == "wayland":
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
        try:
            # Capture the full screen since getting active window geometry
            # requires compositor-specific IPC (swaymsg, hyprctl, etc.)
            subprocess.run(["grim", output_path], check=True, stderr=subprocess.PIPE)
            logger.info("Full-screen screenshot captured via grim")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"grim failed: {e.stderr.decode()}")
            return False
        except FileNotFoundError:
            logger.error("grim is not installed!")
            return False
