import sys
import os
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QSlider, QGroupBox, QFileDialog,
    QMessageBox, QStatusBar, QRadioButton, QStackedWidget, QColorDialog, QFontDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor, QFont 

from logic  import ImageWatermarker
from logic import WatermarkWorker 
#from .logic import ( ImageWatermarker, WatermarkWorker )


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

        try:
            self.setWindowIcon(QIcon('icon/icon.ico'))
        except Exception as e:
            print(f"Warning: Could not load window icon 'icon/icon.ico': {e}")
            # The application will still run, just without an icon

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
