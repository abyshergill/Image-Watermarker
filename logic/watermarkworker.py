import os
from PyQt5.QtCore import Qt, pyqtSignal, QObject

# Worker class for running image processing in a separate thread
class WatermarkWorker(QObject):
    """
    Worker class to perform watermarking in a separate thread.
    Emits signals to update the GUI.
    """
    # Define signals that the worker will emit
    update_progress = pyqtSignal(str) # To update status text
    job_finished = pyqtSignal(int, int, list) # To signal completion with results

    def __init__(self, input_folder, output_folder, watermark_type, size_percent, opacity,
                 watermarker, text_watermark_details=None):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.watermark_type = watermark_type
        self.size_percent = size_percent
        self.opacity = opacity
        self.watermarker = watermarker
        self.text_watermark_details = text_watermark_details
        self._is_running = True # Control flag for thread



    def run(self):
        """
        The main method executed in the separate thread.
        """
        supported_formats = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
        image_files = [f for f in os.listdir(self.input_folder) if f.lower().endswith(supported_formats)]
        processed_count = 0
        total_count = len(image_files)
        errors = []

        if not image_files:
            self.update_progress.emit("No supported image files found in the input folder.")
            self.job_finished.emit(0, 0, [])
            return

        for i, filename in enumerate(image_files):
            if not self._is_running: # Allow stopping the thread if needed
                break

            input_path = os.path.join(self.input_folder, filename)
            output_path = os.path.join(self.output_folder, filename)

            self.update_progress.emit(f"Processing {filename} ({i+1}/{total_count})...")

            try:
                self.watermarker.apply_watermark(
                    input_path, output_path,
                    self.watermark_type,
                    self.size_percent,
                    self.opacity,
                    self.text_watermark_details
                )
                processed_count += 1
            except Exception as e:
                errors.append(f"Failed to watermark {filename}: {e}")
                print(f"Error watermarking {filename}: {e}") # Log to console for debugging

        self.job_finished.emit(processed_count, total_count, errors)

    def stop(self):
        """Stops the worker thread gracefully."""
        self._is_running = False