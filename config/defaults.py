"""
Default configurations for Deassignment.
"""

# Default desktop switching shortcuts (can be overridden by user)
DEFAULT_DESKTOP_SWITCH_LEFT = "ctrl+shift+Left"
DEFAULT_DESKTOP_SWITCH_RIGHT = "ctrl+shift+Right"

# VSCode defaults
DEFAULT_VSCODE_NEW_FILE = "ctrl+n"
DEFAULT_VSCODE_SAVE = "ctrl+s"
DEFAULT_VSCODE_TERMINAL = "ctrl+grave"

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
