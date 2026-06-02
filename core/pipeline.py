import os
import time
import logging
from typing import Dict, Any, Callable
from .ppt_engine import PPTEngine
from .desktop_automator import DesktopAutomatorFactory
from .code_runner import CodeRunner
from .screenshot import ScreenshotFactory
from config import defaults

logger = logging.getLogger("deassignment.pipeline")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [PIPELINE] %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)


class Pipeline:
    """Orchestrates the entire automated generation process."""

    def __init__(self, config: Dict[str, Any], questions: list, template_path: str, output_path: str, temp_dir: str):
        self.config = config
        self.questions = questions
        self.output_path = output_path
        self.temp_dir = temp_dir
        
        logger.info(f"Pipeline init: {len(questions)} questions, language={config.get('language')}")
        logger.info(f"Template: {template_path}")
        logger.info(f"Output: {output_path}")
        
        self.ppt_engine = PPTEngine(template_path, defaults.PPT_CONFIG)
        self.automator = DesktopAutomatorFactory.get_automator(config)
        self.screenshotter = ScreenshotFactory.get_screenshotter()
        self.language = config.get("language", "python")
        self.lang_config = defaults.LANGUAGES.get(self.language, defaults.LANGUAGES["python"])
        
        self.is_paused = False
        self.is_cancelled = False

    def _check_cancelled(self):
        """Check if the pipeline has been cancelled. Returns True if cancelled."""
        if self.is_cancelled:
            logger.warning("Pipeline cancelled by user!")
            return True
        return False

    def _wait_with_cancel(self, seconds: float, progress_callback=None, msg="Waiting..."):
        """Sleep in small increments so we can respond to cancel quickly."""
        elapsed = 0.0
        interval = 0.25
        while elapsed < seconds:
            if self._check_cancelled():
                if progress_callback:
                    progress_callback({"status": "cancelled", "message": "Processing cancelled by user."})
                return False
            while self.is_paused and not self.is_cancelled:
                time.sleep(0.25)
            time.sleep(interval)
            elapsed += interval
        return True
        
    def process(self, progress_callback: Callable[[dict], None]):
        """Runs the pipeline and yields progress updates."""
        try:
            total = len(self.questions)
            logger.info(f"=== Pipeline starting: {total} questions ===")
            
            # On Wayland we don't know desktop indices, so we just go right and come back left
            original_desktop = self.automator.get_current_desktop()
            
            for i, q in enumerate(self.questions):
                if self._check_cancelled():
                    progress_callback({"status": "cancelled", "message": "Processing cancelled."})
                    return
                    
                while self.is_paused and not self.is_cancelled:
                    time.sleep(0.5)
                
                if self._check_cancelled():
                    progress_callback({"status": "cancelled", "message": "Processing cancelled."})
                    return
                    
                q_num = q["number"]
                statement = q["statement"]
                code = q["code"]
                filename = q["filename"]
                
                logger.info(f"--- Question {q_num}/{total}: {filename} ---")
                logger.debug(f"Statement: {statement[:80]}...")
                logger.debug(f"Code length: {len(code)} chars")
                
                progress_callback({
                    "status": "processing", 
                    "question": q_num, 
                    "total": total,
                    "action": f"Creating PPT slides for Question {q_num}..."
                })
                
                # 1. PPT Question Slide
                logger.info("Creating question slide")
                self.ppt_engine.add_question_slide(q_num, statement)
                
                # 2. PPT Code Slide
                logger.info("Creating code slide with syntax highlighting")
                self.ppt_engine.add_code_slide(q_num, statement, code, self.language, self.temp_dir)
                
                if self._check_cancelled():
                    progress_callback({"status": "cancelled", "message": "Processing cancelled."})
                    return
                
                # 3. Write code to file
                progress_callback({"status": "processing", "question": q_num, "total": total, "action": "Writing code file..."})
                filepath = os.path.join(self.temp_dir, filename)
                logger.info(f"Writing code to: {filepath}")
                with open(filepath, "w") as f:
                    f.write(code)
                    
                # 4. Automate execution and screenshot
                progress_callback({"status": "processing", "question": q_num, "total": total, "action": "Switching to VSCode desktop..."})
                
                # Switch desktop to VSCode
                logger.info("Switching FORWARD to VSCode desktop")
                self.automator.switch_desktop_forward()
                
                if self._check_cancelled():
                    progress_callback({"status": "cancelled", "message": "Processing cancelled."})
                    return
                
                # Open file in VSCode
                progress_callback({"status": "processing", "question": q_num, "total": total, "action": "Opening file in VSCode..."})
                logger.info("Opening file in VSCode")
                self.automator.open_file_in_vscode(filepath)
                
                if self._check_cancelled():
                    progress_callback({"status": "cancelled", "message": "Processing cancelled."})
                    return
                
                # Get run command
                cmds = CodeRunner.get_run_commands(
                    self.lang_config, 
                    filepath, 
                    q.get("has_input", False), 
                    q.get("sample_input", "")
                )
                
                # Build the full command: cd into the directory first, then run
                file_dir = os.path.dirname(os.path.abspath(filepath))
                full_cmd = f"cd '{file_dir}' && {cmds[0]}"
                
                # Run command in terminal
                progress_callback({"status": "processing", "question": q_num, "total": total, "action": "Running code in terminal..."})
                logger.info(f"Full terminal command: {full_cmd}")
                self.automator.run_commands_in_terminal(full_cmd)
                
                if self._check_cancelled():
                    progress_callback({"status": "cancelled", "message": "Processing cancelled."})
                    return

                # Simulate typing if there is input
                if q.get("has_input", False) and q.get("sample_input", ""):
                    progress_callback({"status": "processing", "question": q_num, "total": total, "action": "Simulating typing input..."})
                    logger.info("Waiting 1s for program to start, then typing input")
                    if not self._wait_with_cancel(1.0, progress_callback):
                        return
                    
                    sample_input = q.get("sample_input", "")
                    if not sample_input.endswith('\n'):
                        sample_input += '\n'
                        
                    self.automator.simulate_typing(sample_input)
                
                # Wait for execution
                exec_timeout = self.config.get("execution_timeout", defaults.EXECUTION_TIMEOUT)
                progress_callback({"status": "processing", "question": q_num, "total": total, "action": f"Waiting {exec_timeout}s for execution..."})
                logger.info(f"Waiting {exec_timeout}s for code execution")
                if not self._wait_with_cancel(exec_timeout, progress_callback):
                    return
                
                # Screenshot
                progress_callback({"status": "processing", "question": q_num, "total": total, "action": "Capturing screenshot..."})
                screenshot_path = os.path.join(self.temp_dir, f"screenshot_{q_num}.png")
                logger.info(f"Taking screenshot: {screenshot_path}")
                self.screenshotter.capture_active_window(screenshot_path)
                
                if self._check_cancelled():
                    progress_callback({"status": "cancelled", "message": "Processing cancelled."})
                    return
                
                # Cleanup VSCode
                logger.info("Closing terminal session")
                self.automator.close_terminal()
                logger.info("Closing active editor tab")
                self.automator.close_active_tab()
                
                # Switch back
                logger.info("Switching BACK to original desktop")
                self.automator.switch_desktop_back()
                
                # 5. PPT Screenshot Slide
                progress_callback({"status": "processing", "question": q_num, "total": total, "action": "Adding screenshot to PPT..."})
                logger.info("Adding screenshot slide to PPT")
                self.ppt_engine.add_screenshot_slide(q_num, screenshot_path)
                
                progress_callback({"status": "question_done", "question": q_num, "total": total})
                logger.info(f"=== Question {q_num} complete ===")
                
            if not self.is_cancelled:
                progress_callback({"status": "processing", "action": "Saving Presentation..."})
                logger.info(f"Saving presentation to: {self.output_path}")
                self.ppt_engine.save(self.output_path)
                progress_callback({"status": "complete", "file": self.output_path})
                logger.info("=== Pipeline complete! ===")
                
        except Exception as e:
            logger.exception(f"Pipeline crashed with error: {e}")
            progress_callback({"status": "error", "message": str(e)})

    def pause(self):
        logger.info("Pipeline PAUSED")
        self.is_paused = True
        
    def resume(self):
        logger.info("Pipeline RESUMED")
        self.is_paused = False
        
    def cancel(self):
        logger.info("Pipeline CANCEL requested")
        self.is_cancelled = True
