import os
from typing import Dict, Any

class CodeRunner:
    """Handles preparing execution commands for different languages."""
    
    @staticmethod
    def get_run_commands(language_config: Dict[str, Any], filepath: str, has_input: bool = False, sample_input: str = "") -> list:
        """
        Returns a list of shell commands to execute the file.
        Uses heredoc for stdin if sample input is provided.
        """
        # Extract filename and filename without extension
        filename = os.path.basename(filepath)
        filename_no_ext = os.path.splitext(filename)[0]
        
        commands = []
        
        # 1. Compile step (if applicable)
        if language_config.get("compile_cmd"):
            compile_cmd = language_config["compile_cmd"].format(
                filename=filename, 
                filename_no_ext=filename_no_ext
            )
            commands.append(compile_cmd)
            
        # 2. Run step
        run_cmd = language_config["run_cmd"].format(
            filename=filename,
            filename_no_ext=filename_no_ext
        )
        
        if has_input and sample_input:
            # We no longer pipe input via shell (e.g., echo "..." | java ...).
            # Instead, the pipeline will simulate actual keystrokes after starting the program.
            pass
            
        commands.append(run_cmd)
        
        # Combine commands with && if there's a compile step
        if len(commands) > 1:
            return [" && ".join(commands)]
        return commands
