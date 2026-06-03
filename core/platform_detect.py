"""
Platform detection module for Deassignment.

Single source of truth for OS/display-server detection.
Returns 'macos', 'wayland', or 'x11' based on the current environment.
"""

import sys
import os


def get_platform() -> str:
    """Detect the current platform and display server.

    Returns:
        'macos'   — running on macOS (darwin)
        'wayland' — running on Linux with a Wayland session
        'x11'     — running on Linux with an X11 session (or fallback)
    """
    if sys.platform == 'darwin':
        return 'macos'
    session = os.environ.get('XDG_SESSION_TYPE', 'x11').lower()
    return 'wayland' if session == 'wayland' else 'x11'


def is_macos() -> bool:
    """Convenience check for macOS."""
    return sys.platform == 'darwin'


def is_linux() -> bool:
    """Convenience check for Linux."""
    return sys.platform.startswith('linux')
