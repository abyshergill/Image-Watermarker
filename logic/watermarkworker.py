from PIL import Image, ImageDraw, ImageFont
import os
import glob 
from PyQt5.QtCore import QObject, pyqtSignal 

class WatermarkWorker:
    def __init__(self, input_folder, output_folder, watermark_type,
                 watermark_size_ratio, watermark_opacity_ratio,
                 watermarker_instance, text_details=None, add_date=False):
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.watermark_type = watermark_type
        self.watermark_size_ratio = watermark_size_ratio
        self.watermark_opacity_ratio = watermark_opacity_ratio
        self.watermarker = watermarker_instance
        self.text_details = text_details
        self.add_date = add_date
        self._signal_emitter = None 

    def set_signal_emitter(self, emitter):
        """
        Sets the QObject instance that will emit signals to the GUI thread.
        """
        self._signal_emitter = emitter

    def run(self):
        """
        The main watermarking logic to be run in a separate thread.
        """
        image_files = [] 
        errors = []

        try:
            if not os.path.isdir(self.input_folder):
                errors.append(f"Input folder not found or is not a directory: '{self.input_folder}'")
                if self._signal_emitter:
                    self._signal_emitter.job_finished.emit(0, 0, errors)
                return

            all_files_in_folder = os.listdir(self.input_folder)
            image_files = [f for f in all_files_in_folder
                           if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
            
        except FileNotFoundError:
            errors.append(f"Input folder does not exist: '{self.input_folder}'")
            if self._signal_emitter:
                self._signal_emitter.job_finished.emit(0, 0, errors)
            return
        except PermissionError:
            errors.append(f"Permission denied to access input folder: '{self.input_folder}'")
            if self._signal_emitter:
                self._signal_emitter.job_finished.emit(0, 0, errors)
            return
        except Exception as e:
            errors.append(f"Unexpected error listing files in input folder: {e}")
            if self._signal_emitter:
                self._signal_emitter.job_finished.emit(0, 0, errors)
            return

        total_images = len(image_files)
        processed_count = 0

        if total_images == 0: 
            if self._signal_emitter:
                self._signal_emitter.job_finished.emit(0, 0, ["No supported image files found in the input folder."])
            return

        for i, filename in enumerate(image_files):
            input_filepath = os.path.join(self.input_folder, filename)
            output_filepath = os.path.join(self.output_folder, filename)

            try:
                if self.watermark_type == "image":
                    self.watermarker.apply_watermark_image(
                        input_filepath, output_filepath,
                        self.watermark_size_ratio, self.watermark_opacity_ratio,
                        self.add_date
                    )
                elif self.watermark_type == "text":
                    self.watermarker.apply_watermark_text(
                        input_filepath, output_filepath,
                        self.text_details, 
                        self.watermark_size_ratio,
                        self.watermark_opacity_ratio,
                        self.add_date
                    )
                processed_count += 1
                if self._signal_emitter:
                    self._signal_emitter.update_progress.emit(f"Processing {i+1}/{total_images}: {filename}")
            except Exception as e:
                errors.append(f"Error processing {filename}: {e}")
                if self._signal_emitter:
                    self._signal_emitter.update_progress.emit(f"Error on {filename}. Processed {i+1}/{total_images}.")

        if self._signal_emitter:
            self._signal_emitter.job_finished.emit(processed_count, total_images, errors)


