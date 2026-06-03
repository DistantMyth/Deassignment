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
            from core.platforms.macos import MacOSScreenshot
            logger.info("Using MacOSScreenshot (screencapture)")
            return MacOSScreenshot()
        elif platform == 'wayland':
            from core.platforms.wayland import WaylandScreenshot
            logger.info("Using WaylandScreenshot (grim)")
            return WaylandScreenshot()
            
        from core.platforms.x11 import X11Screenshot
        logger.info("Using X11Screenshot (scrot)")
        return X11Screenshot()

