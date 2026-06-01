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
    is_wayland = os.environ.get("XDG_SESSION_TYPE", "") == "wayland"
    
    checks = {
        "x11_wayland_compat": True, # We support both now
        "vscode": False
    }
    
    tools_to_check = []
    if is_wayland:
        tools_to_check = ["ydotool", "wl-copy", "grim"]
        for t in tools_to_check: checks[t] = False
    else:
        tools_to_check = ["xdotool", "scrot", "xclip"]
        for t in tools_to_check: checks[t] = False
        
    tools_to_check.append("code")
    
    for tool in tools_to_check:
        try:
            subprocess.run(["which", tool], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            checks[tool if tool != "code" else "vscode"] = True
        except subprocess.CalledProcessError:
            pass
            
    # For Wayland, ydotool also requires the daemon to be running
    if is_wayland and checks.get("ydotool", False):
        try:
            # Check if ydotoold is running (can be user or system service, or just running process)
            res = subprocess.run(["pgrep", "ydotoold"], stdout=subprocess.PIPE)
            if res.returncode != 0:
                checks["ydotool_daemon"] = False
            else:
                checks["ydotool_daemon"] = True
        except Exception:
            checks["ydotool_daemon"] = False
            
    return jsonify({
        "status": "success" if all(checks.values()) else "warning",
        "checks": checks,
        "is_wayland": is_wayland
    })

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
