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
            from core.platforms.macos import MacOSAutomator
            logger.info("Using MacOSAutomator (AppleScript + pbcopy)")
            return MacOSAutomator(config)
        elif platform == 'wayland':
            from core.platforms.wayland import WaylandAutomator
            logger.info("Using WaylandAutomator (ydotool + wl-clipboard)")
            return WaylandAutomator(config)
            
        from core.platforms.x11 import X11Automator
        logger.info("Using X11Automator (xdotool + xclip)")
        return X11Automator(config)

