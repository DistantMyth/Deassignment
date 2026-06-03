document.addEventListener('DOMContentLoaded', () => {
    // Inject SVG gradient for circular progress
    const svgHTML = `
    <svg style="width:0;height:0;position:absolute;" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#00d4ff" />
          <stop offset="100%" stop-color="#7a28ff" />
        </linearGradient>
      </defs>
    </svg>`;
    document.body.insertAdjacentHTML('afterbegin', svgHTML);

    // State
    const state = {
        currentStep: 1,
        config: {},
        templatePath: null,
        prompts: [],
        currentPromptIndex: 0,
        parsedQuestions: [],
        taskId: null,
        evtSource: null,
        isWayland: false,
        isMacOS: false,
        platform: 'x11',
        displayServer: 'Unknown'
    };

    // Navigation setup
    const steps = document.querySelectorAll('.wizard-step');
    const indicators = document.querySelectorAll('.step-item');
    
    function showStep(stepNum) {
        steps.forEach(s => s.classList.remove('active'));
        document.getElementById(`step-${stepNum}`).classList.add('active');
        
        indicators.forEach(i => {
            const iStep = parseInt(i.dataset.step);
            if (iStep === stepNum) {
                i.classList.add('active');
                i.classList.remove('completed');
            } else if (iStep < stepNum) {
                i.classList.remove('active');
                i.classList.add('completed');
            } else {
                i.classList.remove('active', 'completed');
            }
        });
        
        state.currentStep = stepNum;
        
        // Trigger specific logic for steps
        if (stepNum === 1) runSystemChecks();
        if (stepNum === 4) generatePrompts();
        if (stepNum === 5) updatePreflightForDisplayServer();
    }

    // Attach Next/Prev listeners
    document.querySelectorAll('.btn-prev').forEach(btn => {
        btn.addEventListener('click', () => showStep(state.currentStep - 1));
    });

    document.getElementById('btn-next-1').addEventListener('click', () => showStep(2));
    
    document.getElementById('btn-next-2').addEventListener('click', () => {
        // Gather config
        const form = document.getElementById('config-form');
        const formData = new FormData(form);
        state.config = Object.fromEntries(formData.entries());
        
        // Fix types
        state.config.total_questions = parseInt(state.config.total_questions);
        state.config.batch_size = parseInt(state.config.batch_size);
        
        // Save config for next session
        saveConfig(state.config);
        
        showStep(3);
    });
    
    document.getElementById('btn-next-3').addEventListener('click', () => showStep(4));
    document.getElementById('btn-next-4').addEventListener('click', () => showStep(5));
    document.getElementById('btn-start-pipeline').addEventListener('click', () => {
        showStep(6);
        startPipeline();
    });

    // --- Config Persistence ---

    async function loadSavedConfig() {
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            
            if (data.status === 'success' && data.config && Object.keys(data.config).length > 0) {
                const cfg = data.config;
                
                // Populate form fields
                if (cfg.language) {
                    const langSelect = document.getElementById('config-language');
                    if (langSelect) langSelect.value = cfg.language;
                }
                if (cfg.total_questions) {
                    const totalInput = document.getElementById('config-total-questions');
                    if (totalInput) totalInput.value = cfg.total_questions;
                }
                if (cfg.mode) {
                    const modeRadio = document.querySelector(`input[name="mode"][value="${cfg.mode}"]`);
                    if (modeRadio) {
                        modeRadio.checked = true;
                        // Trigger the change event to show/hide batch options
                        modeRadio.dispatchEvent(new Event('change'));
                    }
                }
                if (cfg.batch_size) {
                    const batchInput = document.getElementById('config-batch-size');
                    if (batchInput) {
                        batchInput.value = cfg.batch_size;
                        const output = batchInput.nextElementSibling;
                        if (output) output.value = cfg.batch_size;
                    }
                }
                if (cfg.shortcut_left) {
                    const leftInput = document.getElementById('config-shortcut-left');
                    if (leftInput) leftInput.value = cfg.shortcut_left;
                }
                if (cfg.shortcut_right) {
                    const rightInput = document.getElementById('config-shortcut-right');
                    if (rightInput) rightInput.value = cfg.shortcut_right;
                }

                // Show restored message
                const restoredMsg = document.getElementById('config-restored-msg');
                if (restoredMsg) {
                    restoredMsg.classList.remove('hidden');
                    setTimeout(() => restoredMsg.classList.add('fade-out'), 4000);
                    setTimeout(() => restoredMsg.classList.add('hidden'), 5000);
                }
            }
        } catch (e) {
            console.log('No saved config found, using defaults.');
        }
    }

    async function saveConfig(config) {
        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
        } catch (e) {
            console.warn('Failed to save config:', e);
        }
    }

    // Load saved config on startup
    loadSavedConfig();

    // --- Step 1: System Checks ---

    // Human-readable names for all possible check keys
    const CHECK_NAMES = {
        // X11 tools
        'xdotool': { name: 'xdotool', desc: 'Desktop automation (X11)' },
        'scrot': { name: 'scrot', desc: 'Screenshot tool (X11)' },
        'xclip': { name: 'xclip', desc: 'Clipboard integration (X11)' },
        // Wayland tools
        'ydotool': { name: 'ydotool', desc: 'Desktop automation (Wayland)' },
        'wl-copy': { name: 'wl-copy', desc: 'Clipboard integration (Wayland)' },
        'grim': { name: 'grim', desc: 'Screenshot tool (Wayland)' },
        'ydotool_daemon': { name: 'ydotoold', desc: 'ydotool daemon service' },
        'uinput_access': { name: '/dev/uinput', desc: 'Input device access for ydotool' },
        // macOS tools
        'osascript': { name: 'osascript', desc: 'AppleScript automation (macOS)' },
        'screencapture': { name: 'screencapture', desc: 'Screenshot tool (macOS)' },
        'pbcopy': { name: 'pbcopy', desc: 'Clipboard integration (macOS)' },
        'accessibility': { name: 'Accessibility', desc: 'System Events permission (macOS)' },
        // Common
        'vscode': { name: 'Visual Studio Code', desc: 'Code editor' },
        'display_server': { name: 'Display Server', desc: 'Platform detected' },
    };

    async function runSystemChecks() {
        try {
            const res = await fetch('/api/preflight');
            const data = await res.json();
            
            state.isWayland = data.is_wayland;
            state.isMacOS = data.is_macos || false;
            state.platform = data.platform || (data.is_macos ? 'macos' : data.is_wayland ? 'wayland' : 'x11');
            state.displayServer = data.display_server || (data.is_macos ? 'macOS' : data.is_wayland ? 'Wayland' : 'X11');

            // Update display server badge in sidebar
            const badgeLabel = document.getElementById('display-server-label');
            const badge = document.getElementById('display-server-badge');
            if (badgeLabel) {
                badgeLabel.textContent = state.displayServer;
                if (state.isMacOS) {
                    badge.classList.add('macos');
                } else {
                    badge.classList.add(state.isWayland ? 'wayland' : 'x11');
                }
            }

            // Show platform-specific shortcut hints
            if (state.isWayland) {
                const hint = document.getElementById('wayland-shortcut-hint');
                if (hint) hint.classList.remove('hidden');
            }
            if (state.isMacOS) {
                const macHint = document.getElementById('macos-shortcut-hint');
                if (macHint) macHint.classList.remove('hidden');
                // Update shortcut input defaults for macOS
                const leftInput = document.getElementById('config-shortcut-left');
                const rightInput = document.getElementById('config-shortcut-right');
                if (leftInput && leftInput.value === 'ctrl+shift+Left') leftInput.value = 'ctrl+Left';
                if (rightInput && rightInput.value === 'ctrl+shift+Right') rightInput.value = 'ctrl+Right';
            }

            const container = document.getElementById('system-checks');
            container.innerHTML = ''; // clear loading
            
            let allPassed = true;
            
            for (const [key, passed] of Object.entries(data.checks)) {
                if (!passed) allPassed = false;
                
                const icon = passed ? '✓' : '✗';
                const statusCls = passed ? 'pass' : 'fail';
                const info = CHECK_NAMES[key] || { name: key, desc: '' };
                const displayName = info.name;
                const displayDesc = passed 
                    ? (info.desc ? `${info.desc} — Ready` : 'Found & Ready')
                    : (info.desc ? `${info.desc} — Missing or incompatible` : 'Missing or incompatible');
                
                container.innerHTML += `
                    <div class="check-card ${statusCls}">
                        <div class="check-icon">${icon}</div>
                        <div class="check-info">
                            <h3>${displayName}</h3>
                            <p>${displayDesc}</p>
                        </div>
                    </div>
                `;
            }
            
            document.getElementById('btn-next-1').disabled = !allPassed;
            
            if (!allPassed) {
                let helpMsg = '';
                if (state.isMacOS) {
                    helpMsg = 'All macOS tools should be built-in. ';
                    if (data.checks.accessibility === false) {
                        helpMsg += '<br>Grant Accessibility permissions: <strong>System Settings → Privacy & Security → Accessibility</strong> → Add your terminal app.';
                    }
                    if (!data.checks.vscode) {
                        helpMsg += '<br>Install VSCode and ensure the <code>code</code> command is in your PATH.';
                    }
                } else {
                    const toolList = state.isWayland 
                        ? 'ydotool, wl-clipboard, grim' 
                        : 'xdotool, scrot, xclip';

                    helpMsg = `Please install missing tools: <code>${toolList}</code>`;
                    
                    if (state.isWayland) {
                        if (!data.checks.ydotool_daemon) {
                            helpMsg += '<br>Start the ydotool daemon: <code>sudo systemctl enable --now ydotoold</code>';
                        }
                        if (data.checks.uinput_access === false) {
                            helpMsg += '<br>Fix uinput access: <code>sudo usermod -aG input $USER</code> then re-login.';
                        }
                    }
                }
                
                container.innerHTML += `<div class="alert alert-warning full-width mt-3">${helpMsg}</div>`;
            }
            
        } catch (e) {
            console.error(e);
        }
    }

    // Initialize step 1
    runSystemChecks();

    // Step 2: Form UI logic
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const batchOptions = document.querySelector('.step-by-step-options');
    
    modeRadios.forEach(r => {
        r.addEventListener('change', (e) => {
            if (e.target.value === 'step_by_step') {
                batchOptions.classList.remove('hidden');
            } else {
                batchOptions.classList.add('hidden');
            }
        });
    });

    // Step 3: File Upload
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('template-upload');
    const nextBtn3 = document.getElementById('btn-next-3');
    const statusMsg = document.getElementById('upload-status');

    dropZone.addEventListener('click', () => fileInput.click());
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length === 0) return;
        const file = files[0];
        if (!file.name.endsWith('.pptx')) {
            statusMsg.innerHTML = `<span class="status-error">Error: Only .pptx files are allowed.</span>`;
            return;
        }
        
        statusMsg.innerHTML = `Uploading ${file.name}...`;
        
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/api/upload-template', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                state.templatePath = data.filepath;
                statusMsg.innerHTML = `<span class="status-success">✓ File uploaded successfully!</span>`;
                dropZone.querySelector('h3').textContent = file.name;
                nextBtn3.disabled = false;
            } else {
                statusMsg.innerHTML = `<span class="status-error">${data.error}</span>`;
            }
        })
        .catch(err => {
            statusMsg.innerHTML = `<span class="status-error">Upload failed.</span>`;
            console.error(err);
        });
    }

    // Step 4: AI Prompt Generation & Response
    async function generatePrompts() {
        try {
            const res = await fetch('/api/generate-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(state.config)
            });
            const data = await res.json();
            
            state.prompts = data.prompts;
            state.currentPromptIndex = 0;
            state.parsedQuestions = [];
            
            updatePromptDisplay();
            
            if (state.prompts.length > 1) {
                document.getElementById('step-by-step-controls').classList.remove('hidden');
                document.getElementById('questions-progress-container').classList.remove('hidden');
                document.getElementById('q-total').textContent = state.config.total_questions;
            } else {
                document.getElementById('step-by-step-controls').classList.add('hidden');
                document.getElementById('questions-progress-container').classList.add('hidden');
            }
            
        } catch (e) {
            console.error("Failed to generate prompt", e);
        }
    }

    function updatePromptDisplay() {
        const display = document.getElementById('prompt-display');
        const counter = document.getElementById('prompt-counter');
        const nextBtn = document.getElementById('btn-next-prompt');
        
        display.textContent = state.prompts[state.currentPromptIndex];
        counter.textContent = `${state.currentPromptIndex + 1} of ${state.prompts.length}`;
        
        if (state.currentPromptIndex === state.prompts.length - 1) {
            nextBtn.textContent = "All prompts shown";
            nextBtn.disabled = true;
        } else {
            nextBtn.textContent = "View Next Prompt";
            nextBtn.disabled = false;
        }
    }

    document.getElementById('btn-next-prompt').addEventListener('click', () => {
        if (state.currentPromptIndex < state.prompts.length - 1) {
            state.currentPromptIndex++;
            updatePromptDisplay();
            document.getElementById('ai-response').value = ''; // clear for next
        }
    });

    document.getElementById('copy-prompt-btn').addEventListener('click', () => {
        const text = document.getElementById('prompt-display').textContent;
        navigator.clipboard.writeText(text).then(() => {
            const btn = document.getElementById('copy-prompt-btn');
            btn.innerHTML = `<span style="color:var(--success)">✓</span>`;
            setTimeout(() => {
                btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
            }, 2000);
        });
    });

    document.getElementById('btn-validate-response').addEventListener('click', async () => {
        const rawResponse = document.getElementById('ai-response').value;
        const msgDiv = document.getElementById('validation-msg');
        
        if (!rawResponse.trim()) {
            msgDiv.innerHTML = `<span class="status-error">Please paste a response first.</span>`;
            return;
        }
        
        msgDiv.innerHTML = "Validating...";
        
        try {
            const res = await fetch('/api/submit-response', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ response: rawResponse })
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                const newQs = data.data.questions;
                state.parsedQuestions = [...state.parsedQuestions, ...newQs];
                
                msgDiv.innerHTML = `<span class="status-success">✓ Successfully parsed ${newQs.length} questions.</span>`;
                
                // Update progress
                if (state.prompts.length > 1) {
                    const received = state.parsedQuestions.length;
                    const total = state.config.total_questions;
                    document.getElementById('q-received').textContent = received;
                    document.getElementById('q-progress-fill').style.width = `${Math.min(100, (received/total)*100)}%`;
                    
                    if (received >= total) {
                        document.getElementById('btn-next-4').disabled = false;
                        msgDiv.innerHTML += `<br><span class="status-success">All questions received! You can proceed.</span>`;
                    }
                } else {
                    document.getElementById('btn-next-4').disabled = false;
                }
                
                document.getElementById('ai-response').value = ''; // clear
            } else {
                msgDiv.innerHTML = `<span class="status-error">${data.message}</span>`;
            }
        } catch (e) {
            msgDiv.innerHTML = `<span class="status-error">Validation request failed.</span>`;
        }
    });

    // Step 5: Checklist
    const checkboxes = document.querySelectorAll('.flight-check');
    const btnStart = document.getElementById('btn-start-pipeline');
    
    checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            const allChecked = Array.from(checkboxes).every(c => c.checked);
            btnStart.disabled = !allChecked;
        });
    });

    function updatePreflightForDisplayServer() {
        // Show Wayland-specific permission alert
        const waylandAlert = document.getElementById('wayland-permission-alert');
        if (waylandAlert) {
            if (state.isWayland) {
                waylandAlert.classList.remove('hidden');
            } else {
                waylandAlert.classList.add('hidden');
            }
        }
        // Show macOS-specific permission alert
        const macosAlert = document.getElementById('macos-permission-alert');
        if (macosAlert) {
            if (state.isMacOS) {
                macosAlert.classList.remove('hidden');
            } else {
                macosAlert.classList.add('hidden');
            }
        }
    }

    // Step 6: Pipeline Execution
    async function startPipeline() {
        try {
            const res = await fetch('/api/start-pipeline', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    config: state.config,
                    questions: state.parsedQuestions,
                    template_path: state.templatePath
                })
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                state.taskId = data.task_id;
                listenToProgress(data.task_id);
            } else {
                alert("Failed to start pipeline: " + data.error);
            }
        } catch (e) {
            alert("Error starting pipeline");
        }
    }

    function updateCircleProgress(pct) {
        const circle = document.getElementById('main-progress-circle');
        const text = document.getElementById('progress-percentage');
        
        // 2 * PI * 45 = 282.74
        const circumference = 283;
        const offset = circumference - (pct / 100) * circumference;
        
        circle.style.strokeDashoffset = offset;
        text.textContent = `${Math.round(pct)}%`;
    }

    function listenToProgress(taskId) {
        if (state.evtSource) state.evtSource.close();
        
        state.evtSource = new EventSource(`/api/progress/${taskId}`);
        
        state.evtSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            
            if (data.status === 'processing') {
                if (data.question) {
                    document.getElementById('current-question').textContent = `Processing Question ${data.question} of ${data.total}`;
                    const pct = ((data.question - 1) / data.total) * 100; // Rough estimate based on q index
                    updateCircleProgress(pct);
                }
                if (data.action) {
                    document.getElementById('current-task').textContent = data.action;
                }
            } else if (data.status === 'question_done') {
                const pct = (data.question / data.total) * 100;
                updateCircleProgress(pct);
            } else if (data.status === 'complete') {
                state.evtSource.close();
                updateCircleProgress(100);
                
                document.querySelector('.processing-container').classList.add('hidden');
                document.getElementById('processing-title').classList.add('hidden');
                document.getElementById('processing-subtitle').classList.add('hidden');
                
                const completeState = document.getElementById('completion-state');
                completeState.classList.remove('hidden');
                
                // Set download link
                if (data.file) {
                    const filename = data.file.split('/').pop();
                    document.getElementById('download-btn').href = `/api/download/${filename}`;
                }
                
                // Show confetti
                confetti({
                    particleCount: 150,
                    spread: 70,
                    origin: { y: 0.6 }
                });
            } else if (data.status === 'error') {
                state.evtSource.close();
                document.getElementById('current-task').textContent = "ERROR: " + data.message;
                document.getElementById('current-task').style.color = "var(--danger)";
            } else if (data.status === 'cancelled') {
                state.evtSource.close();
                document.getElementById('current-task').textContent = "Cancelled by user.";
            }
        };
    }

    // Controls
    document.getElementById('btn-pause').addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        const isPaused = btn.textContent.includes('Resume');
        const action = isPaused ? 'resume' : 'pause';
        
        fetch(`/api/pipeline/${state.taskId}/${action}`, { method: 'POST' })
            .then(() => {
                if (isPaused) {
                    btn.innerHTML = `<span class="icon">⏸</span> Pause`;
                } else {
                    btn.innerHTML = `<span class="icon">▶</span> Resume`;
                }
            });
    });

    document.getElementById('btn-cancel').addEventListener('click', () => {
        if(confirm("Are you sure you want to cancel the automation?")) {
            fetch(`/api/pipeline/${state.taskId}/cancel`, { method: 'POST' });
        }
    });
});
