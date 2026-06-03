"""
Default configurations for Deassignment.
"""

from core.platform_detect import get_platform

# Default desktop switching shortcuts — Linux (X11)
DEFAULT_DESKTOP_SWITCH_LEFT = "ctrl+shift+Left"
DEFAULT_DESKTOP_SWITCH_RIGHT = "ctrl+shift+Right"

# Default desktop switching shortcuts — macOS (Mission Control Spaces)
MACOS_DEFAULT_DESKTOP_SWITCH_LEFT = "ctrl+Left"
MACOS_DEFAULT_DESKTOP_SWITCH_RIGHT = "ctrl+Right"

# VSCode defaults
DEFAULT_VSCODE_NEW_FILE = "ctrl+n"
DEFAULT_VSCODE_SAVE = "ctrl+s"
DEFAULT_VSCODE_TERMINAL = "ctrl+grave"

# macOS default monospace font (built-in, no install needed)
MACOS_DEFAULT_MONO_FONT = "Menlo"


def get_default_shortcuts() -> dict:
    """Return platform-appropriate default desktop switching shortcuts."""
    platform = get_platform()
    if platform == 'macos':
        return {
            "shortcut_left": MACOS_DEFAULT_DESKTOP_SWITCH_LEFT,
            "shortcut_right": MACOS_DEFAULT_DESKTOP_SWITCH_RIGHT,
        }
    # Linux defaults (both X11 and Wayland use the same default keys)
    return {
        "shortcut_left": DEFAULT_DESKTOP_SWITCH_LEFT,
        "shortcut_right": DEFAULT_DESKTOP_SWITCH_RIGHT,
    }

# Supported programming languages and their configurations
LANGUAGES = {
    "python": {
        "name": "Python",
        "extension": ".py",
        "compile_cmd": None,
        "run_cmd": "python3 {filename}",
        "comment_prefix": "#"
    },
    "c": {
        "name": "C",
        "extension": ".c",
        "compile_cmd": "gcc {filename} -o {filename_no_ext}",
        "run_cmd": "./{filename_no_ext}",
        "comment_prefix": "//"
    },
    "cpp": {
        "name": "C++",
        "extension": ".cpp",
        "compile_cmd": "g++ -std=c++17 {filename} -o {filename_no_ext}",
        "run_cmd": "./{filename_no_ext}",
        "comment_prefix": "//"
    },
    "java": {
        "name": "Java",
        "extension": ".java",
        "compile_cmd": "javac {filename}",
        "run_cmd": "java {filename_no_ext}",
        "comment_prefix": "//"
    },
    "javascript": {
        "name": "JavaScript (Node.js)",
        "extension": ".js",
        "compile_cmd": None,
        "run_cmd": "node {filename}",
        "comment_prefix": "//"
    }
}

# Slide layout configurations
PPT_CONFIG = {
    "safe_zone_top": 1.5,     # inches from top
    "safe_zone_bottom": 1.0,  # inches from bottom
    "safe_zone_left": 0.5,    # inches from left
    "safe_zone_right": 0.5,   # inches from right
    "font_name": "Arial",     # Default font for text
    "font_size_title": 18,
    "code_style": "monokai"   # Pygments style for code screenshots
}

# Execution config
EXECUTION_TIMEOUT = 5.0  # seconds to wait for code execution
DELAY_BETWEEN_ACTIONS = 0.5  # seconds
