import os
from PIL import Image, ImageDraw, ImageFont # Import ImageDraw and ImageFont for text watermarking



# Define a class for the core image watermarking logic
class ImageWatermarker:
    """
    Handles the core logic for applying watermarks to images and text.
    """
    def __init__(self, watermark_path: str = None):
        """
        Initializes the ImageWatermarker with an optional watermark image path.

        Args:
            watermark_path (str): Path to the watermark image.
        """
        self.watermark_image = None
        if watermark_path:
            self.load_watermark_image(watermark_path)

    def load_watermark_image(self, watermark_path: str):
        """
        Loads the watermark image. Converts it to RGBA for consistent handling of opacity.

        Args:
            watermark_path (str): Path to the watermark image.
        Raises:
            FileNotFoundError: If the watermark path is invalid.
            IOError: If the watermark image cannot be opened.
        """
        if not os.path.exists(watermark_path):
            raise FileNotFoundError(f"Watermark image not found: {watermark_path}")
        try:
            # Open watermark image and ensure it's in RGBA mode for transparency
            self.watermark_image = Image.open(watermark_path).convert("RGBA")
        except Exception as e:
            raise IOError(f"Could not open watermark image: {e}")

    def apply_watermark(self,
                        input_image_path: str,
                        output_image_path: str,
                        watermark_type: str, 
                        watermark_size_percent: float, 
                        watermark_opacity: float,    
                        text_watermark_details: dict = None): 
        """
        Applies either an image or text watermark to a single input image and saves it.
        The watermark will be repeated across the image.

        Args:
            input_image_path (str): Path to the input image.
            output_image_path (str): Path to save the watermarked image.
            watermark_type (str): Specifies the type of watermark ('image' or 'text').
            watermark_size_percent (float): Watermark size relative to the base image's smallest dimension (0.0 to 1.0).
            watermark_opacity (float): Opacity of the watermark (0.0 to 1.0).
            text_watermark_details (dict): Dictionary containing 'text', 'font_path', 'font_size_px', 'color_rgb' for text watermarking.
        Raises:
            IOError: If input image cannot be opened or output cannot be saved.
            ValueError: If watermark is not loaded or parameters are out of range.
        """
        if not (0 <= watermark_size_percent <= 1):
            raise ValueError("Watermark size percentage must be between 0 and 1.")
        if not (0 <= watermark_opacity <= 1):
            raise ValueError("Watermark opacity must be between 0 and 1.")

        try:
            # Open the input image. Convert to RGBA to handle potential alpha channels
            base_image = Image.open(input_image_path).convert("RGBA")
            base_width, base_height = base_image.size
            min_dim = min(base_width, base_height)

            watermark_to_paste = None
            watermark_actual_width = 0
            watermark_actual_height = 0

            # Create a transparent layer for the watermarks
            watermark_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))

            if watermark_type == 'image':
                if self.watermark_image is None:
                    raise ValueError("No image watermark loaded. Please load a watermark image first.")
                
                # Determine watermark size based on the base image's smallest dimension
                target_watermark_width = int(min_dim * watermark_size_percent)
                watermark_aspect_ratio = self.watermark_image.width / self.watermark_image.height
                target_watermark_height = int(target_watermark_width / watermark_aspect_ratio)

                watermark_to_paste = self.watermark_image.resize(
                    (target_watermark_width, target_watermark_height), Image.Resampling.LANCZOS
                )

                # Adjust watermark opacity
                alpha = watermark_to_paste.split()[3]
                alpha = Image.eval(alpha, lambda x: int(x * watermark_opacity))
                watermark_to_paste.putalpha(alpha)

                watermark_actual_width = watermark_to_paste.width
                watermark_actual_height = watermark_to_paste.height

            elif watermark_type == 'text':
                if not text_watermark_details:
                    raise ValueError("Text watermark details are missing.")

                text = text_watermark_details['text']
                font_path = text_watermark_details['font_path']
                color_rgb = text_watermark_details['color_rgb']

                if not text:
                    # If no text is provided, simply save the original image
                    Image.open(input_image_path).save(output_image_path)
                    return

                # Calculate font size based on watermark_size_percent and image dimensions
                font_size = int(min_dim * watermark_size_percent * 0.8) # 0.8 is a scaling factor, adjust as needed
                if font_size < 1: font_size = 1 # Minimum font size

                font_obj = None
                try:
                    font_obj = ImageFont.truetype(font_path, font_size)
                except Exception:
                    try:
                        font_obj = ImageFont.truetype("arial.ttf", font_size)
                    except IOError:
                        font_obj = ImageFont.load_default()

                # Create a temporary image to measure text size
                temp_draw = ImageDraw.Draw(Image.new("RGBA", (1,1)))
                text_bbox = temp_draw.textbbox((0, 0), text, font=font_obj)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                # Create the text watermark as an image
                text_img = Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0))
                draw_text_img = ImageDraw.Draw(text_img)

                # Color is an RGB tuple, need to add alpha from opacity
                alpha_val = int(watermark_opacity * 255)
                text_color_rgba = color_rgb + (alpha_val,)
                
                # Draw text on the temporary image (adjusting for font's internal padding/origin)
                draw_text_img.text((-text_bbox[0], -text_bbox[1]), text, font=font_obj, fill=text_color_rgba)
                
                watermark_to_paste = text_img
                watermark_actual_width = text_img.width
                watermark_actual_height = text_img.height

            else:
                raise ValueError(f"Unknown watermark type: {watermark_type}")

            if watermark_to_paste:
                # Calculate repetition pattern
                # Add some padding (e.g., 20% of watermark size)
                x_spacing = int(watermark_actual_width * 1.2) # Watermark width + 20% padding
                y_spacing = int(watermark_actual_height * 1.2) # Watermark height + 20% padding

                # If spacing is too small (e.g., if watermark_size_percent is very small)
                if x_spacing == 0: x_spacing = watermark_actual_width + 10
                if y_spacing == 0: y_spacing = watermark_actual_height + 10


                # Tile the watermark across the image
                for y in range(0, base_height + y_spacing, y_spacing):
                    for x in range(0, base_width + x_spacing, x_spacing):
                        watermark_layer.paste(watermark_to_paste, (x, y), watermark_to_paste)

            # Composite the base image with the watermark layer
            watermarked_image = Image.alpha_composite(base_image, watermark_layer)

            # Convert back to original mode if possible, or a common mode like RGB/L.
            original_mode = Image.open(input_image_path).mode
            if original_mode == 'L': # Grayscale
                watermarked_image = watermarked_image.convert("L")
            elif original_mode == 'RGB':
                watermarked_image = watermarked_image.convert("RGB")
            # If original was RGBA, it stays RGBA (our current watermarked_image is RGBA)

            watermarked_image.save(output_image_path)

        except Exception as e:
            raise IOError(f"Error processing image {os.path.basename(input_image_path)}: {e}")