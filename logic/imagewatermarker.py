from PIL import Image, ImageDraw, ImageFont
import os
import glob 
from PyQt5.QtCore import QObject, pyqtSignal 

class ImageWatermarker:
    def __init__(self):
        self.watermark_image = None 

    def load_watermark_image(self, path):
        try:
            self.watermark_image = Image.open(path).convert("RGBA")
        except Exception as e:
            raise IOError(f"Failed to load watermark image: {e}")

    def apply_watermark_image(self, input_path, output_path, size_ratio, opacity_ratio):
        """
        Applies an image watermark to an image.
        """
        try:
            base_image = Image.open(input_path).convert("RGBA")
            if self.watermark_image is None:
                raise ValueError("Watermark image not loaded. Please select one.")

            img_width, img_height = base_image.size
            wm_width, wm_height = self.watermark_image.size
            target_wm_size = int(min(img_width, img_height) * size_ratio)
            if wm_width > wm_height:
                new_wm_width = target_wm_size
                new_wm_height = int(wm_height * (new_wm_width / wm_width))
            else:
                new_wm_height = target_wm_size
                new_wm_width = int(wm_width * (new_wm_height / wm_height)) 
            
            new_wm_width = max(1, new_wm_width)
            new_wm_height = max(1, new_wm_height)

            resized_watermark = self.watermark_image.resize((new_wm_width, new_wm_height), Image.LANCZOS)

            alpha = resized_watermark.split()[-1]
            alpha = Image.eval(alpha, lambda x: x * opacity_ratio)
            resized_watermark.putalpha(alpha)

            padding = 20 
            paste_x = img_width - new_wm_width - padding
            paste_y = img_height - new_wm_height - padding

            paste_x = max(0, paste_x)
            paste_y = max(0, paste_y)

            base_image.paste(resized_watermark, (paste_x, paste_y), resized_watermark)
            base_image.save(output_path)
        except Exception as e:
            raise Exception(f"Failed to apply image watermark: {e}")


    def apply_watermark_text(self, input_path, output_path, text_details, size_ratio, opacity_ratio):
        """
        Applies text watermarks (sender and receiver) to an image.
        Can apply as a single centered text or a repeated pattern.
        """
        try:
            base_image = Image.open(input_path).convert("RGBA")
            img_width, img_height = base_image.size
            watermark_layer = Image.new('RGBA', base_image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark_layer)
            font_family = text_details.get('font_family', 'Arial')
            font_size_pt = text_details.get('font_size_pt', 24) 
            base_font_pixel_size = int(img_height * size_ratio * 0.1)
            if base_font_pixel_size < 10: 
                base_font_pixel_size = 10
            try:
                font = ImageFont.truetype(font_family, base_font_pixel_size)
            except IOError:
                print(f"Warning: Font '{font_family}' not found. Using Arial. Ensure 'arial.ttf' is accessible.")
                try:
                    font = ImageFont.truetype("arial.ttf", base_font_pixel_size)
                except IOError:
                    print("Error: 'arial.ttf' not found. Text watermark may not be applied or may use a generic font.")
                    font = ImageFont.load_default() 
                    
            sender_text = text_details.get('sender_text', '')
            receiver_text = text_details.get('receiver_text', '')
            color_rgb = text_details.get('color_rgb', (0, 0, 0))
            outline_enabled = text_details.get('outline_enabled', False)
            repetition_enabled = text_details.get('repetition_enabled', False) 

            opacity = int(255 * opacity_ratio)
            fill_color = color_rgb + (opacity,)
            outline_color = (0, 0, 0, opacity) 

            text_lines = []
            if sender_text.strip():
                text_lines.append(sender_text)

            if receiver_text.strip():
                text_lines.append(receiver_text)
            
            if not text_lines: 
                return

            if repetition_enabled:
                combined_text = ""
                if len(text_lines) == 2:
                    combined_text = f"{text_lines[0]} | {text_lines[1]}"

                elif len(text_lines) == 1:
                    combined_text = text_lines[0]
                
                if not combined_text.strip(): 
                    return
                
                dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1,1)))
                bbox = dummy_draw.textbbox((0,0), combined_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                horizontal_spacing = text_width + 50 
                vertical_spacing = text_height + 50 
                num_repeats_x = int(img_width / horizontal_spacing) + 2
                num_repeats_y = int(img_height / vertical_spacing) + 2
                start_x = (img_width - (num_repeats_x * horizontal_spacing - 50)) / 2
                start_y = (img_height - (num_repeats_y * vertical_spacing - 50)) / 2

                for row in range(num_repeats_y):
                    for col in range(num_repeats_x):
                        x_pos = start_x + col * horizontal_spacing
                        y_pos = start_y + row * vertical_spacing

                        if outline_enabled:
                            outline_thickness = max(1, int(base_font_pixel_size * 0.05))
                            for dx in range(-outline_thickness, outline_thickness + 1):
                                for dy in range(-outline_thickness, outline_thickness + 1):
                                    if dx != 0 or dy != 0:
                                        draw.text((x_pos + dx, y_pos + dy), combined_text, font=font, fill=outline_color)
                            draw.text((x_pos, y_pos), combined_text, font=font, fill=(color_rgb[0], color_rgb[1], color_rgb[2], 0))

                        else:
                            draw.text((x_pos, y_pos), combined_text, font=font, fill=fill_color)

            else:
                text1 = text_lines[0] if len(text_lines) > 0 else ""
                text2 = text_lines[1] if len(text_lines) > 1 else ""

                bbox1 = draw.textbbox((0,0), text1, font=font)
                text1_width = bbox1[2] - bbox1[0]
                text1_height = bbox1[3] - bbox1[1]

                text2_width = 0
                text2_height = 0
                if text2:
                    bbox2 = draw.textbbox((0,0), text2, font=font)
                    text2_width = bbox2[2] - bbox2[0]
                    text2_height = bbox2[3] - bbox2[1]

                max_text_width = max(text1_width, text2_width)
                
                total_text_block_height = text1_height
                line_gap = 10 
                if text2:
                    total_text_block_height += text2_height + line_gap

                start_x = (img_width - max_text_width) / 2
                start_y = (img_height - total_text_block_height) / 2

                if text1.strip():
                    x1_pos = (img_width - text1_width) / 2
                    y1_pos = start_y

                    if outline_enabled:
                        outline_thickness = max(1, int(base_font_pixel_size * 0.05))
                        for dx in range(-outline_thickness, outline_thickness + 1):
                            for dy in range(-outline_thickness, outline_thickness + 1):
                                if dx != 0 or dy != 0:
                                    draw.text((x1_pos + dx, y1_pos + dy), text1, font=font, fill=outline_color)
                        draw.text((x1_pos, y1_pos), text1, font=font, fill=(color_rgb[0], color_rgb[1], color_rgb[2], 0))
                    else:
                        draw.text((x1_pos, y1_pos), text1, font=font, fill=fill_color)

                if text2.strip():
                    x2_pos = (img_width - text2_width) / 2
                    y2_pos = start_y + text1_height + line_gap

                    if outline_enabled:
                        outline_thickness = max(1, int(base_font_pixel_size * 0.05))
                        for dx in range(-outline_thickness, outline_thickness + 1):
                            for dy in range(-outline_thickness, outline_thickness + 1):
                                if dx != 0 or dy != 0:
                                    draw.text((x2_pos + dx, y2_pos + dy), text2, font=font, fill=outline_color)
                        draw.text((x2_pos, y2_pos), text2, font=font, fill=(color_rgb[0], color_rgb[1], color_rgb[2], 0))
                    else:
                        draw.text((x2_pos, y2_pos), text2, font=font, fill=fill_color)

            watermarked_image = Image.alpha_composite(base_image, watermark_layer)
            watermarked_image.save(output_path)

        except Exception as e:
            raise Exception(f"Failed to apply text watermark: {e}")
        
    def __init__(self):
        self.watermark_image = None 

    def load_watermark_image(self, path):
        try:
            self.watermark_image = Image.open(path).convert("RGBA")
        except Exception as e:
            raise IOError(f"Failed to load watermark image: {e}")

    def apply_watermark_image(self, input_path, output_path, size_ratio, opacity_ratio):
        """
        Applies an image watermark to an image.
        """
        try:
            base_image = Image.open(input_path).convert("RGBA")
            if self.watermark_image is None:
                raise ValueError("Watermark image not loaded. Please select one.")

            img_width, img_height = base_image.size
            wm_width, wm_height = self.watermark_image.size
            target_wm_size = int(min(img_width, img_height) * size_ratio)
            
            if wm_width > wm_height:
                new_wm_width = target_wm_size
                new_wm_height = int(wm_height * (new_wm_width / wm_width))
            else:
                new_wm_height = target_wm_size
                new_wm_width = int(wm_width * (new_wm_height / wm_height)) 
            
            new_wm_width = max(1, new_wm_width)
            new_wm_height = max(1, new_wm_height)

            resized_watermark = self.watermark_image.resize((new_wm_width, new_wm_height), Image.LANCZOS)

            alpha = resized_watermark.split()[-1]
            alpha = Image.eval(alpha, lambda x: x * opacity_ratio)
            resized_watermark.putalpha(alpha)
            padding = 20 
            paste_x = img_width - new_wm_width - padding
            paste_y = img_height - new_wm_height - padding

            paste_x = max(0, paste_x)
            paste_y = max(0, paste_y)

            base_image.paste(resized_watermark, (paste_x, paste_y), resized_watermark)
            base_image.save(output_path)
        except Exception as e:
            raise Exception(f"Failed to apply image watermark: {e}")




