import json
from typing import List, Dict

class PromptGenerator:
    """Generates prompts for the AI based on configuration."""

    def __init__(self, config: dict):
        self.config = config
        self.language = config.get("language", "python")
        self.total_questions = config.get("total_questions", 1)
        self.mode = config.get("mode", "all_at_once")  # 'all_at_once' or 'step_by_step'
        self.batch_size = config.get("batch_size", 10)
        self.chat_mode = config.get("chat_mode", "continue") # 'continue' or 'new'

    def generate_schema(self) -> str:
        """Returns the Markdown schema explanation for the prompt."""
        return """
For each question, provide the response strictly in the following Markdown format. Do not use JSON. Do not deviate from these headers.

## Question [Number]
**Statement:** [The exact question statement from the document]
**Filename:** [A short, descriptive filename, e.g., 'q1_factorial.""" + self.get_extension() + """']
**Has Input:** [true if the program requires user input via stdin, false otherwise]

### Sample Input
```text
[If has_input is true, provide a realistic sample input here. Otherwise, leave empty.]
```

### Expected Output
```text
[The expected output for the given sample input, or empty if none]
```

### Code
```""" + self.language + """
[The complete, runnable code to solve the question]
```
"""

    def get_extension(self) -> str:
        # Simple lookup, real implementation would use defaults.py
        exts = {"python": "py", "c": "c", "cpp": "cpp", "java": "java", "javascript": "js"}
        return exts.get(self.language.lower(), "txt")

    def generate_prompts(self) -> List[str]:
        """Generates a list of prompts based on the mode."""
        if self.mode == "all_at_once":
            return [self._generate_single_prompt(1, self.total_questions)]
        
        # Step-by-step mode
        prompts = []
        for i in range(1, self.total_questions + 1, self.batch_size):
            start = i
            end = min(i + self.batch_size - 1, self.total_questions)
            prompts.append(self._generate_batch_prompt(start, end, is_first=(i==1)))
        return prompts

    def _generate_single_prompt(self, start: int, end: int) -> str:
        prompt = f"I am providing a document containing {self.total_questions} programming questions. "
        prompt += f"Please write code to solve all questions in {self.language}.\n\n"
        prompt += self.generate_schema()
        return prompt

    def _generate_batch_prompt(self, start: int, end: int, is_first: bool) -> str:
        if self.chat_mode == "new" or is_first:
            prompt = f"I have a document containing {self.total_questions} programming questions. "
            prompt += f"Please write code to solve questions {start} through {end} in {self.language}.\n\n"
            prompt += self.generate_schema()
            return prompt
        else:
            # Continuing same chat
            prompt = f"Continue with the next batch. Please write code to solve questions {start} through {end} in {self.language}.\n"
            prompt += "Use the exact same Markdown format as before, with no other conversational text."
            return prompt
