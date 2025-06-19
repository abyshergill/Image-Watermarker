import sys
import os
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QSlider, QGroupBox, QFileDialog,
    QMessageBox, QStatusBar, QRadioButton, QStackedWidget, QColorDialog, QFontDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QColor, QFont # Import QColor and QFont for color/font dialogs

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
            self.load_watermark_image(waterark_path)

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
                        watermark_type: str, # 'image' or 'text'
                        watermark_size_percent: float, # Percentage 0.0 to 1.0
                        watermark_opacity: float,    # Percentage 0.0 to 1.0
                        text_watermark_details: dict = None): # Dict for text, font, color
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

# Define the main GUI application class using QMainWindow
class WatermarkApp(QMainWindow):
    """
    The main GUI application for image watermarking using PyQt5.
    """
    def __init__(self):
        """
        Initializes the WatermarkApp GUI.
        """
        super().__init__()
        self.setWindowTitle("Image Watermarker")
        self.setGeometry(100, 100, 700, 650) # Adjusted height for new controls

        self.watermarker = ImageWatermarker() # Initialize the core watermarker logic

        # Variables to store paths and settings
        self.input_folder_path = ""
        self.output_folder_path = ""

        # Image Watermark Settings
        self.watermark_image_path = ""

        # Text Watermark Settings
        self.watermark_text = ""
        self.text_font = QFont("Arial", 24) # Default font
        self.text_color = QColor(0, 0, 0) # Default black

        self.watermark_size_value = 15 # Default 15%
        self.watermark_opacity_value = 50 # Default 50%
        self.selected_watermark_type = "image" # Default to image watermark

        self._create_widgets()
        self._load_last_settings() # Load settings from a configuration file

        self.worker_thread = None # To hold the QThread instance
        self.worker = None # To hold the WatermarkWorker instance

    def _create_widgets(self):
        """
        Creates and arranges all GUI widgets.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Input Folder Selection ---
        input_group = QGroupBox("Input Images Folder")
        input_layout = QHBoxLayout(input_group)
        self.input_entry = QLineEdit(self.input_folder_path)
        self.input_entry.setReadOnly(True)
        input_layout.addWidget(self.input_entry)
        browse_input_btn = QPushButton("Browse")
        browse_input_btn.clicked.connect(self._browse_input_folder)
        input_layout.addWidget(browse_input_btn)
        main_layout.addWidget(input_group)

        # --- Output Folder Selection ---
        output_group = QGroupBox("Output Watermarked Images Folder")
        output_layout = QHBoxLayout(output_group)
        self.output_entry = QLineEdit(self.output_folder_path)
        self.output_entry.setReadOnly(True)
        output_layout.addWidget(self.output_entry)
        browse_output_btn = QPushButton("Browse")
        browse_output_btn.clicked.connect(self._browse_output_folder)
        output_layout.addWidget(browse_output_btn)
        main_layout.addWidget(output_group)

        # --- Watermark Type Selection ---
        type_group = QGroupBox("Select Watermark Type")
        type_layout = QHBoxLayout(type_group)
        self.image_radio = QRadioButton("Image Watermark")
        self.text_radio = QRadioButton("Text Watermark")
        type_layout.addWidget(self.image_radio)
        type_layout.addWidget(self.text_radio)
        type_layout.addStretch(1) # Push radios to left
        main_layout.addWidget(type_group)

        self.image_radio.toggled.connect(self._toggle_watermark_type)
        self.text_radio.toggled.connect(self._toggle_watermark_type)

        # --- Stacked Widget for Watermark Settings ---
        self.watermark_settings_stack = QStackedWidget()

        # Image Watermark Settings Page
        self.image_settings_page = QWidget()
        image_settings_layout = QVBoxLayout(self.image_settings_page)
        image_settings_layout.setContentsMargins(0, 0, 0, 0) # No extra margins for sub-widget

        watermark_img_group = QGroupBox("Watermark Image File")
        watermark_img_layout = QHBoxLayout(watermark_img_group)
        self.watermark_img_entry = QLineEdit(self.watermark_image_path)
        self.watermark_img_entry.setReadOnly(True)
        watermark_img_layout.addWidget(self.watermark_img_entry)
        browse_watermark_btn = QPushButton("Browse")
        browse_watermark_btn.clicked.connect(self._browse_watermark_image)
        watermark_img_layout.addWidget(browse_watermark_btn)
        image_settings_layout.addWidget(watermark_img_group)
        self.watermark_settings_stack.addWidget(self.image_settings_page)

        # Text Watermark Settings Page
        self.text_settings_page = QWidget()
        text_settings_layout = QVBoxLayout(self.text_settings_page)
        text_settings_layout.setContentsMargins(0, 0, 0, 0) # No extra margins for sub-widget

        text_input_group = QGroupBox("Watermark Text")
        text_input_layout = QVBoxLayout(text_input_group)
        self.watermark_text_entry = QLineEdit(self.watermark_text)
        self.watermark_text_entry.setPlaceholderText("Enter text to watermark...")
        self.watermark_text_entry.textChanged.connect(self._save_settings) # Save on text change
        text_input_layout.addWidget(self.watermark_text_entry)
        text_settings_layout.addWidget(text_input_group)

        font_color_layout = QHBoxLayout()
        # Font Selection
        font_group = QGroupBox("Font")
        font_layout = QHBoxLayout(font_group)
        self.font_label = QLabel(self.text_font.family() + ", " + str(self.text_font.pointSize()))
        font_layout.addWidget(self.font_label)
        select_font_btn = QPushButton("Select Font")
        select_font_btn.clicked.connect(self._select_font)
        font_layout.addWidget(select_font_btn)
        font_color_layout.addWidget(font_group)

        # Color Selection
        color_group = QGroupBox("Color")
        color_layout = QHBoxLayout(color_group)
        self.color_preview = QLabel("   ") # Placeholder for color
        self.color_preview.setStyleSheet(f"background-color: {self.text_color.name()}; border: 1px solid black;")
        color_layout.addWidget(self.color_preview)
        select_color_btn = QPushButton("Select Color")
        select_color_btn.clicked.connect(self._select_color)
        color_layout.addWidget(select_color_btn)
        font_color_layout.addWidget(color_group)

        text_settings_layout.addLayout(font_color_layout)
        self.watermark_settings_stack.addWidget(self.text_settings_page)

        main_layout.addWidget(self.watermark_settings_stack)

        # --- Watermark Size Slider ---
        size_group = QGroupBox("Watermark Size")
        size_layout = QVBoxLayout(size_group)
        size_label_layout = QHBoxLayout()
        size_label_layout.addWidget(QLabel("Watermark Size (% of smallest dimension):"))
        self.size_value_label = QLabel(f"{self.watermark_size_value:.0f}%")
        size_label_layout.addWidget(self.size_value_label)
        size_label_layout.addStretch(1)
        size_layout.addLayout(size_label_layout)

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(5, 100)
        self.size_slider.setValue(self.watermark_size_value)
        self.size_slider.setTickPosition(QSlider.TicksBelow)
        self.size_slider.setTickInterval(5)
        self.size_slider.valueChanged.connect(self._update_size_label)
        size_layout.addWidget(self.size_slider)
        main_layout.addWidget(size_group)

        # --- Watermark Opacity Slider ---
        opacity_group = QGroupBox("Watermark Opacity")
        opacity_layout = QVBoxLayout(opacity_group)
        opacity_label_layout = QHBoxLayout()
        opacity_label_layout.addWidget(QLabel("Watermark Opacity (%):"))
        self.opacity_value_label = QLabel(f"{self.watermark_opacity_value:.0f}%")
        opacity_label_layout.addWidget(self.opacity_value_label)
        opacity_label_layout.addStretch(1)
        opacity_layout.addLayout(opacity_label_layout)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100) # Changed range to start from 20 for "smaller limit" on transparency
        self.opacity_slider.setValue(self.watermark_opacity_value)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(5)
        self.opacity_slider.valueChanged.connect(self._update_opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        main_layout.addWidget(opacity_group)

        # --- Start Button ---
        self.start_button = QPushButton("Start Watermarking")
        self.start_button.clicked.connect(self._start_watermarking)
        main_layout.addWidget(self.start_button)

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Set initial watermark type based on saved settings
        if self.selected_watermark_type == "text":
            self.text_radio.setChecked(True)
        else:
            self.image_radio.setChecked(True) # Default to image if not text or unrecognized

    def _toggle_watermark_type(self):
        """Switches between image and text watermark settings pages."""
        if self.image_radio.isChecked():
            self.watermark_settings_stack.setCurrentWidget(self.image_settings_page)
            self.selected_watermark_type = "image"
        elif self.text_radio.isChecked():
            self.watermark_settings_stack.setCurrentWidget(self.text_settings_page)
            self.selected_watermark_type = "text"
        self._save_settings()

    def _update_size_label(self, value):
        """Updates the label next to the size slider."""
        self.watermark_size_value = value
        self.size_value_label.setText(f"{value:.0f}%")
        self._save_settings() # Save setting immediately on slider change

    def _update_opacity_label(self, value):
        """Updates the label next to the opacity slider."""
        self.watermark_opacity_value = value
        self.opacity_value_label.setText(f"{value:.0f}%")
        self._save_settings() # Save setting immediately on slider change

    def _browse_input_folder(self):
        """Opens a dialog to select the input folder."""
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Input Folder", self.input_folder_path)
        if folder_selected:
            self.input_folder_path = folder_selected
            self.input_entry.setText(folder_selected)
            self.statusBar.showMessage(f"Input folder set: {folder_selected}")
            self._save_settings()

    def _browse_output_folder(self):
        """Opens a dialog to select the output folder."""
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_folder_path)
        if folder_selected:
            self.output_folder_path = folder_selected
            self.output_entry.setText(folder_selected)
            self.statusBar.showMessage(f"Output folder set: {folder_selected}")
            self._save_settings()

    def _browse_watermark_image(self):
        """Opens a dialog to select the watermark image."""
        file_selected, _ = QFileDialog.getOpenFileName(
            self, "Select Watermark Image", self.watermark_image_path,
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_selected:
            self.watermark_image_path = file_selected
            self.watermark_img_entry.setText(file_selected)
            try:
                self.watermarker.load_watermark_image(file_selected)
                self.statusBar.showMessage(f"Watermark image loaded: {os.path.basename(file_selected)}")
                self._save_settings()
            except (FileNotFoundError, IOError) as e:
                QMessageBox.critical(self, "Error Loading Watermark", str(e))
                self.statusBar.showMessage("Error loading watermark.")

    def _select_font(self):
        """Opens a dialog to select font for text watermark."""
        font, ok = QFontDialog.getFont(self.text_font, self, "Select Font for Watermark")
        if ok:
            self.text_font = font
            self.font_label.setText(font.family() + ", " + str(font.pointSize()))
            self.statusBar.showMessage(f"Font set to: {font.family()}, {font.pointSize()}pt")
            self._save_settings()

    def _select_color(self):
        """Opens a dialog to select color for text watermark."""
        color = QColorDialog.getColor(self.text_color, self, "Select Color for Watermark")
        if color.isValid():
            self.text_color = color
            self.color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self.statusBar.showMessage(f"Color set to: {color.name()}")
            self._save_settings()

    def _start_watermarking(self):
        """
        Initiates the watermarking process in a separate thread.
        Validates inputs before starting.
        """
        input_folder = self.input_folder_path
        output_folder = self.output_folder_path

        if not input_folder or not os.path.isdir(input_folder):
            QMessageBox.critical(self, "Invalid Input", "Please select a valid input folder.")
            return
        if not output_folder:
            QMessageBox.critical(self, "Invalid Output", "Please select an output folder.")
            return

        watermark_type = self.selected_watermark_type
        text_details = None

        if watermark_type == "image":
            watermark_path = self.watermark_image_path
            if not watermark_path or not os.path.exists(watermark_path):
                QMessageBox.critical(self, "Invalid Watermark", "Please select a valid watermark image.")
                return
            if self.watermarker.watermark_image is None:
                QMessageBox.critical(self, "Watermark Not Loaded", "The watermark image failed to load. Please re-select.")
                return
        elif watermark_type == "text":
            self.watermark_text = self.watermark_text_entry.text()
            if not self.watermark_text.strip():
                QMessageBox.critical(self, "Invalid Watermark Text", "Please enter some text for the watermark.")
                return
            # Convert QColor to RGB tuple for PIL
            color_rgb = (self.text_color.red(), self.text_color.green(), self.text_color.blue())
            text_details = {
                'text': self.watermark_text,
                'font_path': self.text_font.key().split(',')[0], # Get font family as path hint
                'color_rgb': color_rgb
            }
            # PyQt QFont pointSize is usually what PIL expects, but conversion might be needed
            # For simplicity, PIL uses pixel size or points directly. Using a default
            # point size for system fonts that PIL can recognize.
            # Actual pixel size calculated inside apply_watermark based on image dimensions.

        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        self.start_button.setEnabled(False) # Disable button during processing
        self.statusBar.showMessage("Watermarking in progress...")

        # Create a QThread and a worker object
        # Note: using standard threading.Thread as QThread has specific usage patterns
        # for moving objects to the thread, which is more complex for direct run() calls.
        # For simple background tasks, threading.Thread with signals is fine.
        self.worker = WatermarkWorker(
            input_folder,
            output_folder,
            watermark_type,
            self.watermark_size_value / 100.0, # Convert percentage to float 0.0-1.0
            self.watermark_opacity_value / 100.0,
            self.watermarker,
            text_details
        )
        self.worker_thread = threading.Thread(target=self.worker.run)


        # Connect worker signals to slots in the main thread
        self.worker.update_progress.connect(self.statusBar.showMessage)
        self.worker.job_finished.connect(self._job_done)

        # Start the worker thread
        self.worker_thread.start()

    def _job_done(self, processed_count, total_count, errors):
        """
        Called when watermarking is complete. Shows a pop-up and resets UI.
        This slot is connected to the worker's job_finished signal,
        ensuring it runs in the main GUI thread.
        """
        self.start_button.setEnabled(True) # Re-enable button
        self.statusBar.showMessage("Watermarking complete.")

        message = f"Job Done! Watermarked {processed_count} of {total_count} images."
        if errors:
            error_details = "\n".join(errors)
            message += f"\n\nErrors encountered:\n{error_details}"
            QMessageBox.warning(self, "Watermarking Complete with Errors", message)
        else:
            QMessageBox.information(self, "Watermarking Complete", message)

        self._save_settings() # Save settings after job completion

    def _save_settings(self):
        """Saves current settings to a simple configuration file."""
        config_path = "watermarker_config.txt"
        with open(config_path, "w") as f:
            f.write(f"input_folder={self.input_folder_path}\n")
            f.write(f"output_folder={self.output_folder_path}\n")
            f.write(f"selected_watermark_type={self.selected_watermark_type}\n")

            # Image Watermark Settings
            f.write(f"watermark_image={self.watermark_image_path}\n")

            # Text Watermark Settings
            f.write(f"watermark_text={self.watermark_text_entry.text()}\n")
            f.write(f"text_font_family={self.text_font.family()}\n")
            f.write(f"text_font_size={self.text_font.pointSize()}\n")
            f.write(f"text_color={self.text_color.name()}\n") # Save color as hex string

            f.write(f"watermark_size={self.watermark_size_value}\n")
            f.write(f"watermark_opacity={self.watermark_opacity_value}\n")

    def _load_last_settings(self):
        """Loads last saved settings from the configuration file."""
        config_path = "watermarker_config.txt"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line:
                            key, value = line.split("=", 1)
                            if key == "input_folder":
                                self.input_folder_path = value
                                self.input_entry.setText(value)
                            elif key == "output_folder":
                                self.output_folder_path = value
                                self.output_entry.setText(value)
                            elif key == "selected_watermark_type":
                                self.selected_watermark_type = value
                                if value == "image":
                                    self.image_radio.setChecked(True)
                                else:
                                    self.text_radio.setChecked(True)
                            elif key == "watermark_image":
                                self.watermark_image_path = value
                                self.watermark_img_entry.setText(value)
                                if os.path.exists(value):
                                    try:
                                        self.watermarker.load_watermark_image(value)
                                    except Exception as e:
                                        print(f"Warning: Could not auto-load image watermark from config: {e}")
                            elif key == "watermark_text":
                                self.watermark_text = value
                                self.watermark_text_entry.setText(value)
                            elif key == "text_font_family":
                                # Reconstruct font. Point size will be loaded next.
                                self.text_font.setFamily(value)
                            elif key == "text_font_size":
                                self.text_font.setPointSize(int(value))
                                self.font_label.setText(self.text_font.family() + ", " + str(self.text_font.pointSize()))
                            elif key == "text_color":
                                self.text_color = QColor(value)
                                self.color_preview.setStyleSheet(f"background-color: {self.text_color.name()}; border: 1px solid black;")
                            elif key == "watermark_size":
                                self.watermark_size_value = float(value)
                                self.size_slider.setValue(int(self.watermark_size_value))
                                self._update_size_label(int(self.watermark_size_value))
                            elif key == "watermark_opacity":
                                self.watermark_opacity_value = float(value)
                                self.opacity_slider.setValue(int(self.watermark_opacity_value))
                                self._update_opacity_label(int(self.watermark_opacity_value))
                self.statusBar.showMessage("Loaded last session settings.")
                # Ensure the correct stack page is shown after loading settings
                self._toggle_watermark_type()
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.statusBar.showMessage("Could not load previous settings.")

# Main entry point for the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WatermarkApp()
    window.show()
    sys.exit(app.exec_())
