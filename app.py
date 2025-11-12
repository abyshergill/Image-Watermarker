import sys
import os
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QSlider, QGroupBox, QFileDialog,
    QMessageBox, QStatusBar, QRadioButton, QStackedWidget, QColorDialog, QFontDialog,
    QCheckBox 
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject 
from PyQt5.QtGui import QIcon, QColor, QFont

from logic import ImageWatermarker
from logic import WatermarkWorker

class WatermarkApp(QMainWindow):
    """
    The main GUI application for image watermarking using PyQt5.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Watermarker")
        self.setGeometry(100, 100, 750, 750) # Adjusted size for new controls

        try:
            self.setWindowIcon(QIcon('icon/icon.ico'))
        except Exception as e:
            print(f"Warning: Could not load window icon 'icon/icon.ico': {e}")

        self.watermarker = ImageWatermarker()

        self.input_folder_path = ""
        self.output_folder_path = ""
        self.watermark_image_path = ""

        self.sender_text = ""
        self.receiver_text = ""
        self.text_font = QFont("Arial", 24) 
        self.text_color = QColor(0, 0, 0) 
        self.text_outline_enabled = False 
        self.text_repetition_enabled = False 

        self.watermark_size_value = 15 
        self.watermark_opacity_value = 50 
        self.selected_watermark_type = "text" 

        self._create_widgets()
        self._load_last_settings() 

        self.input_entry.setText(self.input_folder_path)
        self.output_entry.setText(self.output_folder_path)
        self.watermark_img_entry.setText(self.watermark_image_path)
        self.watermark_text_entry_sender.setText(self.sender_text) 
        self.watermark_text_entry_receiver.setText(self.receiver_text) 
        self.font_label.setText(self.text_font.family() + ", " + str(self.text_font.pointSize()))
        self.color_preview.setStyleSheet(f"background-color: {self.text_color.name()}; border: 1px solid black;")
        self.size_slider.setValue(int(self.watermark_size_value))
        self.opacity_slider.setValue(int(self.watermark_opacity_value))
        self.text_outline_checkbox.setChecked(self.text_outline_enabled) 
        if self.text_repetition_enabled:
            self.repeat_text_radio.setChecked(True)
        else:
            self.single_text_radio.setChecked(True)

        if self.selected_watermark_type == "text":
            self.text_radio.setChecked(True)
        else:
            self.image_radio.setChecked(True)
        self._toggle_watermark_type() 

        self.worker_thread = None 
        self.worker = None 

    def _create_widgets(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        input_group = QGroupBox("Input Images Folder")
        input_layout = QHBoxLayout(input_group)
        self.input_entry = QLineEdit(self.input_folder_path)
        self.input_entry.setReadOnly(True)
        input_layout.addWidget(self.input_entry)
        browse_input_btn = QPushButton("Browse")
        browse_input_btn.clicked.connect(self._browse_input_folder)
        input_layout.addWidget(browse_input_btn)
        main_layout.addWidget(input_group)

        output_group = QGroupBox("Output Watermarked Images Folder")
        output_layout = QHBoxLayout(output_group)
        self.output_entry = QLineEdit(self.output_folder_path)
        self.output_entry.setReadOnly(True)
        output_layout.addWidget(self.output_entry)
        browse_output_btn = QPushButton("Browse")
        browse_output_btn.clicked.connect(self._browse_output_folder)
        output_layout.addWidget(browse_output_btn)
        main_layout.addWidget(output_group)

        type_group = QGroupBox("Select Watermark Type")
        type_layout = QHBoxLayout(type_group)
        self.image_radio = QRadioButton("Image Watermark")
        self.text_radio = QRadioButton("Text Watermark")
        type_layout.addWidget(self.image_radio)
        type_layout.addWidget(self.text_radio)
        type_layout.addStretch(1) 
        main_layout.addWidget(type_group)

        self.image_radio.toggled.connect(self._toggle_watermark_type)
        self.text_radio.toggled.connect(self._toggle_watermark_type)

        self.watermark_settings_stack = QStackedWidget()

        self.image_settings_page = QWidget()
        image_settings_layout = QVBoxLayout(self.image_settings_page)
        image_settings_layout.setContentsMargins(0, 0, 0, 0) 

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

        self.text_settings_page = QWidget()
        text_settings_layout = QVBoxLayout(self.text_settings_page)
        text_settings_layout.setContentsMargins(0, 0, 0, 0) 

        sender_text_group = QGroupBox("Sender Text")
        sender_text_layout = QVBoxLayout(sender_text_group)
        self.watermark_text_entry_sender = QLineEdit(self.sender_text)
        self.watermark_text_entry_sender.setPlaceholderText("Enter sender text...")
        self.watermark_text_entry_sender.textChanged.connect(self._save_settings)
        sender_text_layout.addWidget(self.watermark_text_entry_sender)
        text_settings_layout.addWidget(sender_text_group)

        receiver_text_group = QGroupBox("Receiver Text")
        receiver_text_layout = QVBoxLayout(receiver_text_group)
        self.watermark_text_entry_receiver = QLineEdit(self.receiver_text)
        self.watermark_text_entry_receiver.setPlaceholderText("Enter receiver text...")
        self.watermark_text_entry_receiver.textChanged.connect(self._save_settings)
        receiver_text_layout.addWidget(self.watermark_text_entry_receiver)
        text_settings_layout.addWidget(receiver_text_group)

        font_color_layout = QHBoxLayout()

        font_group = QGroupBox("Font")
        font_layout = QHBoxLayout(font_group)
        self.font_label = QLabel(self.text_font.family() + ", " + str(self.text_font.pointSize()))
        font_layout.addWidget(self.font_label)
        select_font_btn = QPushButton("Select Font")
        select_font_btn.clicked.connect(self._select_font)
        font_layout.addWidget(select_font_btn)
        font_color_layout.addWidget(font_group)

        color_group = QGroupBox("Color")
        color_layout = QHBoxLayout(color_group)
        self.color_preview = QLabel("   ") 
        self.color_preview.setStyleSheet(f"background-color: {self.text_color.name()}; border: 1px solid black;")
        color_layout.addWidget(self.color_preview)
        select_color_btn = QPushButton("Select Color")
        select_color_btn.clicked.connect(self._select_color)
        color_layout.addWidget(select_color_btn)
        font_color_layout.addWidget(color_group)

        text_settings_layout.addLayout(font_color_layout)

        self.text_outline_checkbox = QCheckBox("Apply Text Outline Effect (Transparent Fill)")
        self.text_outline_checkbox.setChecked(self.text_outline_enabled)
        self.text_outline_checkbox.stateChanged.connect(self._update_text_outline_setting)
        text_settings_layout.addWidget(self.text_outline_checkbox)

        repetition_group = QGroupBox("Text Placement")
        repetition_layout = QHBoxLayout(repetition_group)
        self.single_text_radio = QRadioButton("Single Text (Centered)")
        self.repeat_text_radio = QRadioButton("Repeat Text (Pattern)")
        repetition_layout.addWidget(self.single_text_radio)
        repetition_layout.addWidget(self.repeat_text_radio)
        repetition_layout.addStretch(1)
        text_settings_layout.addWidget(repetition_group)

        self.single_text_radio.toggled.connect(self._toggle_text_repetition_mode)
        self.repeat_text_radio.toggled.connect(self._toggle_text_repetition_mode)


        self.watermark_settings_stack.addWidget(self.text_settings_page)

        main_layout.addWidget(self.watermark_settings_stack)

        size_group = QGroupBox("Watermark Size")
        size_layout = QVBoxLayout(size_group)
        size_label_layout = QHBoxLayout()
        size_label_layout.addWidget(QLabel("Watermark Size (% of smallest image dimension):"))
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

        opacity_group = QGroupBox("Watermark Opacity")
        opacity_layout = QVBoxLayout(opacity_group)
        opacity_label_layout = QHBoxLayout()
        opacity_label_layout.addWidget(QLabel("Watermark Opacity (%):"))
        self.opacity_value_label = QLabel(f"{self.watermark_opacity_value:.0f}%")
        opacity_label_layout.addWidget(self.opacity_value_label)
        opacity_label_layout.addStretch(1)
        opacity_layout.addLayout(opacity_label_layout)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100) 
        self.opacity_slider.setValue(self.watermark_opacity_value)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(5)
        self.opacity_slider.valueChanged.connect(self._update_opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        main_layout.addWidget(opacity_group)

        self.start_button = QPushButton("Start Watermarking")
        self.start_button.clicked.connect(self._start_watermarking)
        main_layout.addWidget(self.start_button)

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def _toggle_watermark_type(self):
        if self.image_radio.isChecked():
            self.watermark_settings_stack.setCurrentWidget(self.image_settings_page)
            self.selected_watermark_type = "image"
        elif self.text_radio.isChecked():
            self.watermark_settings_stack.setCurrentWidget(self.text_settings_page)
            self.selected_watermark_type = "text"
        self._save_settings()

    def _toggle_text_repetition_mode(self):
        self.text_repetition_enabled = self.repeat_text_radio.isChecked()
        self._save_settings()

    def _update_size_label(self, value):
        self.watermark_size_value = value
        self.size_value_label.setText(f"{value:.0f}%")
        self._save_settings() 

    def _update_opacity_label(self, value):
        self.watermark_opacity_value = value
        self.opacity_value_label.setText(f"{value:.0f}%")
        self._save_settings() 

    def _update_text_outline_setting(self, state):
        self.text_outline_enabled = (state == Qt.Checked)
        self._save_settings()

    def _browse_input_folder(self):
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Input Folder", self.input_folder_path)
        if folder_selected:
            self.input_folder_path = folder_selected
            self.input_entry.setText(folder_selected)
            self.statusBar.showMessage(f"Input folder set: {folder_selected}")
            self._save_settings()

    def _browse_output_folder(self):
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_folder_path)
        if folder_selected:
            self.output_folder_path = folder_selected
            self.output_entry.setText(folder_selected)
            self.statusBar.showMessage(f"Output folder set: {folder_selected}")
            self._save_settings()

    def _browse_watermark_image(self):
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
        font, ok = QFontDialog.getFont(self.text_font, self, "Select Font for Watermark")
        if ok:
            self.text_font = font
            self.font_label.setText(font.family() + ", " + str(font.pointSize()))
            self.statusBar.showMessage(f"Font set to: {font.family()}, {font.pointSize()}pt")
            self._save_settings()

    def _select_color(self):
        color = QColorDialog.getColor(self.text_color, self, "Select Color for Watermark")
        if color.isValid():
            self.text_color = color
            self.color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self.statusBar.showMessage(f"Color set to: {color.name()}")
            self._save_settings()

    def _start_watermarking(self):
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
            self.sender_text = self.watermark_text_entry_sender.text()
            self.receiver_text = self.watermark_text_entry_receiver.text()

            if not self.sender_text.strip() and not self.receiver_text.strip():
                QMessageBox.critical(self, "Invalid Watermark Text", "Please enter text for either Sender or Receiver (or both).")
                return

            color_rgb = (self.text_color.red(), self.text_color.green(), self.text_color.blue())
            
            text_details = {
                'sender_text': self.sender_text,
                'receiver_text': self.receiver_text,
                'font_family': self.text_font.family(),
                'font_size_pt': self.text_font.pointSize(), 
                'color_rgb': color_rgb,
                'outline_enabled': self.text_outline_enabled, 
                'repetition_enabled': self.text_repetition_enabled 
            }

        os.makedirs(output_folder, exist_ok=True)

        self.start_button.setEnabled(False) 
        self.statusBar.showMessage("Watermarking in progress...")

        self.worker = WatermarkWorker(
            input_folder,
            output_folder,
            watermark_type,
            self.watermark_size_value / 100.0, 
            self.watermark_opacity_value / 100.0,
            self.watermarker,
            text_details 
        )
        
        self.signal_emitter = WorkerSignals()
        self.signal_emitter.update_progress.connect(self.statusBar.showMessage)
        self.signal_emitter.job_finished.connect(self._job_done)
        self.worker.set_signal_emitter(self.signal_emitter) 

        self.worker_thread = threading.Thread(target=self.worker.run)
        self.worker_thread.start()

    def _job_done(self, processed_count, total_count, errors):
        self.start_button.setEnabled(True) 
        self.statusBar.showMessage("Watermarking complete.")

        message = f"Job Done! Watermarked {processed_count} of {total_count} images."
        if errors:
            error_details = "\n".join(errors)
            message += f"\n\nErrors encountered:\n{error_details}"
            QMessageBox.warning(self, "Watermarking Complete with Errors", message)
        else:
            QMessageBox.information(self, "Watermarking Complete", message)

        self._save_settings() 

    def _save_settings(self):
        config_path = "watermarker_config.txt"
        with open(config_path, "w") as f:
            f.write(f"input_folder={self.input_folder_path}\n")
            f.write(f"output_folder={self.output_folder_path}\n")
            f.write(f"selected_watermark_type={self.selected_watermark_type}\n")

            f.write(f"watermark_image={self.watermark_image_path}\n")

            f.write(f"sender_text={self.watermark_text_entry_sender.text()}\n")
            f.write(f"receiver_text={self.watermark_text_entry_receiver.text()}\n")
            f.write(f"text_font_family={self.text_font.family()}\n")
            f.write(f"text_font_size={self.text_font.pointSize()}\n")
            f.write(f"text_color={self.text_color.name()}\n") 
            f.write(f"text_outline_enabled={self.text_outline_enabled}\n") 
            f.write(f"text_repetition_enabled={self.text_repetition_enabled}\n") 

            f.write(f"watermark_size={self.watermark_size_value}\n")
            f.write(f"watermark_opacity={self.watermark_opacity_value}\n")

    def _load_last_settings(self):
        config_path = "watermarker_config.txt"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    settings = {}
                    for line in f:
                        line = line.strip()
                        if "=" in line:
                            key, value = line.split("=", 1)
                            settings[key] = value

                self.input_folder_path = settings.get("input_folder", "")
                self.output_folder_path = settings.get("output_folder", "")
                self.selected_watermark_type = settings.get("selected_watermark_type", "text") 

                self.watermark_image_path = settings.get("watermark_image", "")

                self.sender_text = settings.get("sender_text", "")
                self.receiver_text = settings.get("receiver_text", "")
                
                font_family = settings.get("text_font_family", "Arial")
                font_size = int(settings.get("text_font_size", 24))
                self.text_font = QFont(font_family, font_size)

                self.text_color = QColor(settings.get("text_color", "#000000"))
                self.text_outline_enabled = settings.get("text_outline_enabled", "False").lower() == "true"
                self.text_repetition_enabled = settings.get("text_repetition_enabled", "False").lower() == "true" 

                self.watermark_size_value = float(settings.get("watermark_size", 15))
                self.watermark_opacity_value = float(settings.get("watermark_opacity", 50))

                self.statusBar.showMessage("Loaded last session settings.")
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.statusBar.showMessage("Could not load previous settings.")

class WorkerSignals(QObject):
    update_progress = pyqtSignal(str)
    job_finished = pyqtSignal(int, int, list)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WatermarkApp()
    window.show()
    sys.exit(app.exec_())
