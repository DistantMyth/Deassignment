import subprocess
import time
import logging

logger = logging.getLogger("deassignment.automator")

class BaseAutomator:
    def __init__(self, config: dict):
        self.config = config
        self.delay = config.get("DELAY_BETWEEN_ACTIONS", 1.0)

    def _run(self, cmd: list, check=True) -> str:
        cmd_str = ' '.join(cmd)
        logger.debug(f"Running: {cmd_str}")
        try:
            result = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout = result.stdout.decode().strip()
            stderr = result.stderr.decode().strip()
            if stdout:
                logger.debug(f"  stdout: {stdout[:200]}")
            if stderr:
                logger.warning(f"  stderr: {stderr[:200]}")
            return stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command FAILED: {cmd_str}")
            logger.error(f"  exit code: {e.returncode}")
            logger.error(f"  stderr: {e.stderr.decode()[:500]}")
            raise

    def get_current_desktop(self) -> int:
        raise NotImplementedError()

    def switch_desktop_forward(self):
        """Switch one desktop to the right (towards VSCode)."""
        raise NotImplementedError()

    def switch_desktop_back(self):
        """Switch one desktop to the left (back to original)."""
        raise NotImplementedError()

    def open_file_in_vscode(self, filepath: str):
        """Opens a file in VSCode using the CLI. (Universal across display servers)"""
        logger.info(f"Opening file in VSCode: {filepath}")
        subprocess.run(["code", filepath])
        time.sleep(2.5)
        self.focus_vscode()
        
    def focus_vscode(self) -> bool:
        raise NotImplementedError()

    def focus_terminal(self):
        """Focus the integrated terminal in VSCode. Subclasses implement this."""
        raise NotImplementedError()

    def clipboard_copy(self, text: str):
        """Copy text to clipboard. Subclasses implement this."""
        raise NotImplementedError()
    
    def simulate_paste_in_terminal(self):
        """Simulate Ctrl+Shift+V (terminal paste). Subclasses implement this."""
        raise NotImplementedError()
        
    def simulate_enter(self):
        """Simulate pressing Enter. Subclasses implement this."""
        raise NotImplementedError()

    def simulate_typing(self, text: str):
        """Simulate typing text character by character. Subclasses implement this."""
        raise NotImplementedError()
        
    def close_terminal(self):
        """Close the integrated terminal by sending 'exit' and Enter."""
        logger.info("Closing terminal by sending 'exit'")
        self.clipboard_copy("exit")
        time.sleep(0.3)
        self.simulate_paste_in_terminal()
        time.sleep(0.3)
        self.simulate_enter()
        time.sleep(self.delay)

    def run_commands_in_terminal(self, cmd_string: str):
        """
        Focus the VSCode terminal, paste a command, and press Enter.
        """
        logger.info(f"Running in terminal: {cmd_string[:100]}...")
        
        logger.debug("Step 1: Focusing VSCode window")
        self.focus_vscode()
        time.sleep(0.5)
        
        logger.debug("Step 2: Opening/focusing integrated terminal")
        self.focus_terminal()
        time.sleep(self.delay * 2)
        
        logger.debug("Step 3: Copying command to clipboard")
        self.clipboard_copy(cmd_string)
        time.sleep(0.3)
        
        logger.debug("Step 4: Pasting from clipboard (Ctrl+Shift+V for terminal)")
        self.simulate_paste_in_terminal()
        time.sleep(0.5)
        
        logger.debug("Step 5: Pressing Enter to execute")
        self.simulate_enter()
        logger.info("Command sent to terminal successfully")
        
    def close_active_tab(self):
        raise NotImplementedError()
