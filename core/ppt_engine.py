import os
from copy import deepcopy
import io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image

# Pygments for code highlighting
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import ImageFormatter

class PPTEngine:
    """Handles all PPTX generation and manipulation."""
    
    def __init__(self, template_path: str, config: dict):
        self.prs = Presentation(template_path)
        self.config = config
        
        # Determine the template slide (user requested last slide)
        if len(self.prs.slides) == 0:
            raise ValueError("Template presentation has no slides.")
        self.template_slide = self.prs.slides[-1]
        
    def _duplicate_template_slide(self):
        """
        Creates a new slide based on the template slide.
        Properly handles copying both text/shapes and images.
        """
        new_slide = self.prs.slides.add_slide(self.template_slide.slide_layout)
        
        for shape in self.template_slide.shapes:
            if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                # Re-add image via blob to maintain valid rId relationships
                image_blob = shape.image.blob
                image_stream = io.BytesIO(image_blob)
                new_slide.shapes.add_picture(
                    image_stream,
                    shape.left, shape.top,
                    shape.width, shape.height
                )
            else:
                # Safe to deepcopy XML for other elements
                new_el = deepcopy(shape.element)
                new_slide.shapes._spTree.insert_element_before(new_el, 'p:extLst')
                
        return new_slide
        
    def _add_header_to_slide(self, slide, text: str):
        """Adds a title/header to the slide within the top safe zone."""
        left = Inches(self.config.get("safe_zone_left", 0.5))
        top = Inches(self.config.get("safe_zone_top", 1.5))
        width = self.prs.slide_width - Inches(self.config.get("safe_zone_left", 0.5) + self.config.get("safe_zone_right", 0.5))
        height = Inches(1.0)
        
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = text
        run.font.name = self.config.get("font_name", "Arial")
        run.font.size = Pt(self.config.get("font_size_title", 18))
        run.font.bold = True
        return top + height # Return bottom position of header

    def add_question_slide(self, q_num: int, q_statement: str):
        """Adds a slide showing just the question."""
        slide = self._duplicate_template_slide()
        self._add_header_to_slide(slide, f"Question {q_num}:\n{q_statement}")

    def _code_to_image(self, code: str, language: str, output_path: str):
        """Renders code to a syntax-highlighted PNG image using Pygments."""
        lexer = get_lexer_by_name(language)
        # We use a relatively large font so it's readable on a slide
        formatter = ImageFormatter(
            font_size=16,
            font_name="DejaVu Sans Mono", # Or Consolas
            line_pad=6,
            image_pad=10,
            line_numbers=True,
            style=self.config.get("code_style", "monokai"),
        )
        with open(output_path, "wb") as f:
            highlight(code, lexer, formatter, outfile=f)

    def add_code_slide(self, q_num: int, q_statement: str, code: str, language: str, temp_dir: str):
        """
        Adds slide(s) containing the code and the question statement.
        If code is too long, splits it across multiple slides.
        """
        # 1. Render entire code to image
        code_img_path = os.path.join(temp_dir, f"code_{q_num}.png")
        self._code_to_image(code, language, code_img_path)
        
        # 2. Setup the first slide with the full question statement
        slide = self._duplicate_template_slide()
        header_text = f"Question {q_num}:\n{q_statement}"
        header_bottom = self._add_header_to_slide(slide, header_text)
        
        left = Inches(self.config.get("safe_zone_left", 0.5))
        top = header_bottom + Inches(0.2)
        
        max_width = self.prs.slide_width - Inches(self.config.get("safe_zone_left", 0.5) + self.config.get("safe_zone_right", 0.5))
        max_height = self.prs.slide_height - top - Inches(self.config.get("safe_zone_bottom", 1.0))
        
        with Image.open(code_img_path) as img:
            img_w, img_h = img.size
            
            # Calculate rendering scale (assume 96 DPI natively = 9525 EMUs per pixel)
            EMUS_PER_PIXEL = 9525
            
            rendered_w = img_w * EMUS_PER_PIXEL
            if rendered_w > max_width:
                rendered_w = max_width
                
            scale = rendered_w / (img_w * EMUS_PER_PIXEL)
            rendered_h_full = img_h * EMUS_PER_PIXEL * scale
            
            if rendered_h_full <= max_height:
                slide.shapes.add_picture(code_img_path, left, top, width=rendered_w)
            else:
                # Image is too tall, we need to crop and spill over to new slides
                y_offset = 0
                slide_idx = 0
                
                while y_offset < img_h:
                    if slide_idx == 0:
                        current_slide = slide
                        current_max_h = max_height
                        current_top = top
                    else:
                        current_slide = self._duplicate_template_slide()
                        h_bottom = self._add_header_to_slide(current_slide, f"")
                        current_top = h_bottom + Inches(0.2)
                        current_max_h = self.prs.slide_height - current_top - Inches(self.config.get("safe_zone_bottom", 1.0))
                        
                    # How many pixels can fit in the available height?
                    px_to_fit = int(current_max_h / (EMUS_PER_PIXEL * scale))
                    
                    if px_to_fit <= 50:
                        px_to_fit = 200 # Fallback to prevent infinite loop
                        
                    crop_box = (0, y_offset, img_w, min(y_offset + px_to_fit, img_h))
                    cropped = img.crop(crop_box)
                    chunk_path = os.path.join(temp_dir, f"code_chunk_{q_num}_{slide_idx}.png")
                    cropped.save(chunk_path)
                    
                    current_slide.shapes.add_picture(chunk_path, left, current_top, width=rendered_w)
                    
                    y_offset += px_to_fit
                    slide_idx += 1

    def add_screenshot_slide(self, q_num: int, screenshot_path: str):
        """Adds a slide containing the execution screenshot."""
        slide = self._duplicate_template_slide()
        self._add_header_to_slide(slide, f"Question {q_num} (Output):")
        
        left = Inches(self.config.get("safe_zone_left", 0.5))
        top = Inches(self.config.get("safe_zone_top", 1.5)) + Inches(1.0) # Header roughly takes 1 inch
        
        max_width = self.prs.slide_width - Inches(self.config.get("safe_zone_left", 0.5) + self.config.get("safe_zone_right", 0.5))
        max_height = self.prs.slide_height - top - Inches(self.config.get("safe_zone_bottom", 1.0))
        
        with Image.open(screenshot_path) as img:
            img_w, img_h = img.size
            
        aspect = img_h / img_w
        
        if (max_width * aspect) > max_height:
            # Constrain by height
            slide.shapes.add_picture(screenshot_path, left, top, height=max_height)
        else:
            # Constrain by width
            slide.shapes.add_picture(screenshot_path, left, top, width=max_width)
            
    def save(self, output_path: str):
        """Saves the presentation."""
        # Optionally, remove the original template slide if it was just a blank placeholder
        # However, deleting slides in python-pptx is complex and prone to breaking references.
        # It's safer to leave it or ask user to provide a 1-slide template.
        self.prs.save(output_path)
