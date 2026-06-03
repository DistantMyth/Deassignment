import os
import json
import time
import uuid
import subprocess
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from werkzeug.utils import secure_filename
import threading

from core import PromptGenerator, ResponseParser, Pipeline

app = Flask(__name__)

# Basic config
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

USER_CONFIG_PATH = os.path.join('config', 'user_config.json')

# Ensure directories exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['TEMP_FOLDER'], app.config['OUTPUT_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# In-memory store for pipelines (since it's a single-user local tool, this is fine)
active_pipelines = {}
progress_queues = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/preflight', methods=['GET'])
def preflight_check():
    """Checks if system requirements are met."""
    from core.platform_detect import get_platform
    platform = get_platform()
    is_wayland = platform == 'wayland'
    is_macos = platform == 'macos'
    
    checks = {
        "display_server": True,  # We support all three now
        "vscode": False
    }
    
    tools_to_check = []
    if is_macos:
        # macOS: all tools are built-in, just verify they exist
        tools_to_check = ["osascript", "screencapture", "pbcopy"]
        for t in tools_to_check:
            checks[t] = False
    elif is_wayland:
        tools_to_check = ["ydotool", "wl-copy", "grim"]
        for t in tools_to_check:
            checks[t] = False
    else:
        tools_to_check = ["xdotool", "scrot", "xclip"]
        for t in tools_to_check:
            checks[t] = False
        
    tools_to_check.append("code")
    
    # 'which' works on both Linux and macOS
    for tool in tools_to_check:
        try:
            subprocess.run(["which", tool], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            checks[tool if tool != "code" else "vscode"] = True
        except subprocess.CalledProcessError:
            pass
            
    # For Wayland, ydotool also requires the daemon to be running
    if is_wayland and checks.get("ydotool", False):
        try:
            res = subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.PIPE)
            daemon_running = res.returncode == 0

            if not daemon_running:
                # Try to auto-start ydotoold
                started = False
                
                # Strategy 1: systemctl --user
                try:
                    subprocess.run(
                        ["systemctl", "--user", "start", "ydotoold"],
                        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5
                    )
                    time.sleep(0.5)
                    res = subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.PIPE)
                    if res.returncode == 0:
                        started = True
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    pass

                # Strategy 2: sudo systemctl
                if not started:
                    try:
                        subprocess.run(
                            ["sudo", "-n", "systemctl", "start", "ydotoold"],
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5
                        )
                        time.sleep(0.5)
                        res = subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.PIPE)
                        if res.returncode == 0:
                            started = True
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                        pass

                daemon_running = started

            checks["ydotool_daemon"] = daemon_running
        except Exception:
            checks["ydotool_daemon"] = False

        # Check /dev/uinput permissions
        uinput_ok = os.path.exists("/dev/uinput") and os.access("/dev/uinput", os.W_OK)
        checks["uinput_access"] = uinput_ok

    # macOS-specific: check Accessibility permissions with a quick smoke test
    if is_macos:
        try:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to return name of first process'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5
            )
            checks["accessibility"] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            checks["accessibility"] = False

    # Determine display server name
    if is_macos:
        display_server = "macOS"
    elif is_wayland:
        display_server = "Wayland"
    else:
        display_server = "X11"
            
    return jsonify({
        "status": "success" if all(checks.values()) else "warning",
        "checks": checks,
        "is_wayland": is_wayland,
        "is_macos": is_macos,
        "platform": platform,
        "display_server": display_server
    })


# --- Config Persistence ---

@app.route('/api/config', methods=['GET'])
def get_saved_config():
    """Load saved user config from disk."""
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                config = json.load(f)
            return jsonify({"status": "success", "config": config})
        except (json.JSONDecodeError, IOError):
            return jsonify({"status": "success", "config": {}})
    return jsonify({"status": "success", "config": {}})


@app.route('/api/config', methods=['POST'])
def save_config():
    """Save user config to disk so it persists across sessions."""
    config = request.json
    if not config:
        return jsonify({"error": "No config provided"}), 400
    
    try:
        os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
        with open(USER_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return jsonify({"status": "success"})
    except IOError as e:
        return jsonify({"error": f"Failed to save config: {e}"}), 500


@app.route('/api/upload-template', methods=['POST'])
def upload_template():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and file.filename.endswith('.pptx'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({"status": "success", "filepath": filepath})
        
    return jsonify({"error": "Invalid file format. Must be .pptx"}), 400

@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt():
    config = request.json
    generator = PromptGenerator(config)
    prompts = generator.generate_prompts()
    return jsonify({"prompts": prompts})

@app.route('/api/submit-response', methods=['POST'])
def submit_response():
    data = request.json
    raw_response = data.get("response", "")
    
    success, parsed_data, error_msg = ResponseParser.parse(raw_response)
    
    if success:
        return jsonify({"status": "success", "data": parsed_data})
    else:
        return jsonify({"status": "error", "message": error_msg}), 400

@app.route('/api/start-pipeline', methods=['POST'])
def start_pipeline():
    data = request.json
    config = data.get("config", {})
    questions = data.get("questions", [])
    template_path = data.get("template_path")
    
    if not template_path or not os.path.exists(template_path):
        return jsonify({"error": "Template file not found."}), 400
        
    if not questions:
        return jsonify({"error": "No questions provided."}), 400

    task_id = str(uuid.uuid4())
    output_filename = f"assignment_{int(time.time())}.pptx"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    pipeline = Pipeline(
        config=config,
        questions=questions,
        template_path=template_path,
        output_path=output_path,
        temp_dir=app.config['TEMP_FOLDER']
    )
    
    active_pipelines[task_id] = pipeline
    progress_queues[task_id] = []
    
    def progress_callback(update):
        progress_queues[task_id].append(update)
        
    # Start pipeline in a separate thread
    thread = threading.Thread(target=pipeline.process, args=(progress_callback,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "success", "task_id": task_id, "output_file": output_filename})

@app.route('/api/progress/<task_id>', methods=['GET'])
def stream_progress(task_id):
    def event_stream():
        if task_id not in progress_queues:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Invalid task ID'})}\n\n"
            return
            
        queue = progress_queues[task_id]
        last_idx = 0
        
        while True:
            # Yield any new events
            while last_idx < len(queue):
                event = queue[last_idx]
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") in ["complete", "error", "cancelled"]:
                    return
                last_idx += 1
                
            time.sleep(0.5)
            
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/api/pipeline/<task_id>/<action>', methods=['POST'])
def manage_pipeline(task_id, action):
    if task_id not in active_pipelines:
        return jsonify({"error": "Invalid task ID"}), 404
        
    pipeline = active_pipelines[task_id]
    
    if action == "pause":
        pipeline.pause()
    elif action == "resume":
        pipeline.resume()
    elif action == "cancel":
        pipeline.cancel()
    else:
        return jsonify({"error": "Invalid action"}), 400
        
    return jsonify({"status": "success", "action": action})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
