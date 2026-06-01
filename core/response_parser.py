import re
from typing import Dict, List, Tuple

class ResponseParser:
    """Parses and validates AI Markdown responses."""

    @staticmethod
    def parse(raw_response: str) -> Tuple[bool, Dict, str]:
        """
        Parses structured markdown text from the AI into a structured dict.
        Returns: (success, parsed_data, error_message)
        """
        questions = []
        
        # Split by "## Question"
        blocks = re.split(r'##\s*Question', raw_response, flags=re.IGNORECASE)
        
        for block in blocks[1:]: # Skip the first chunk (intro text before first header)
            if not block.strip():
                continue
                
            q = {}
            
            # Parse number from the very first line of the block
            first_line = block.split('\n', 1)[0].strip()
            num_match = re.search(r'\d+', first_line)
            if num_match:
                q['number'] = int(num_match.group())
            else:
                q['number'] = len(questions) + 1 # Fallback
                
            # Parse simple fields using non-greedy matches bounded by the next expected markdown
            stmt_match = re.search(r'\*\*Statement:\*\*\s*(.*?)(?=\*\*Filename:\*\*|###)', block, re.IGNORECASE | re.DOTALL)
            file_match = re.search(r'\*\*Filename:\*\*\s*(.*?)(?=\*\*Has Input:\*\*|###)', block, re.IGNORECASE | re.DOTALL)
            input_match = re.search(r'\*\*Has Input:\*\*\s*(.*?)(?=###|$)', block, re.IGNORECASE | re.DOTALL)
            
            q['statement'] = stmt_match.group(1).strip() if stmt_match else "Missing Statement"
            q['filename'] = file_match.group(1).strip().replace(" ", "_") if file_match else f"q{q['number']}.txt"
            
            has_input_str = input_match.group(1).lower().strip() if input_match else "false"
            q['has_input'] = 'true' in has_input_str or 'yes' in has_input_str
            
            # Parse code blocks
            # We look for the headers and then the very first code block after it
            # Sample Input
            si_section = re.search(r'###\s*Sample Input\s*```(?:text)?(.*?)```', block, re.IGNORECASE | re.DOTALL)
            q['sample_input'] = si_section.group(1).strip() if si_section else ""
            
            # Expected Output
            eo_section = re.search(r'###\s*Expected Output\s*```(?:text)?(.*?)```', block, re.IGNORECASE | re.DOTALL)
            q['expected_output'] = eo_section.group(1).strip() if eo_section else ""
            
            # Code
            # Matches any language identifier or none
            code_section = re.search(r'###\s*Code\s*```[a-zA-Z]*\n(.*?)```', block, re.IGNORECASE | re.DOTALL)
            q['code'] = code_section.group(1).strip() if code_section else ""
            
            # Basic validation
            if not q['code']:
                return False, {}, f"Failed to parse code block for Question {q['number']}. Ensure it is inside a '### Code' section with triple backticks."
                
            questions.append(q)

        if not questions:
            return False, {}, "Failed to parse Markdown. Ensure the AI used the '## Question [Number]' headers."

        return True, {"questions": questions}, ""
