import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, \
    QFileDialog, QScrollArea, QProgressBar, QMenuBar, QAction, QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PIL import Image
import fitz  # PyMuPDF


class ImageProcessor(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(QImage, QImage)
    error = pyqtSignal(str)

    def __init__(self, file_path, is_pdf):
        super().__init__()
        self.file_path = file_path
        self.is_pdf = is_pdf

    def run(self):
        try:
            image = self.load_image(self.file_path, self.is_pdf)
            self.progress.emit(20)

            compressed_image_path = self.compress_image(image)
            self.progress.emit(40)

            image = self.downscale_image(compressed_image_path)
            self.progress.emit(60)

            image = self.color_code_image(image)
            self.progress.emit(100)

            original_qimage = self.image_to_qimage(self.load_image(self.file_path, self.is_pdf))
            processed_qimage = self.image_to_qimage(image)
            self.finished.emit(original_qimage, processed_qimage)
        except Exception as e:
            self.error.emit(str(e))

    def load_image(self, file_path, is_pdf):
        if is_pdf:
            doc = fitz.open(file_path)
            page = doc.load_page(0)  # just the first page
            pix = page.get_pixmap()
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            image = Image.open(file_path)
        return image.convert("RGB")

    def compress_image(self, image):
        compressed_image_path = "compressed_image.jpg"
        image.save(compressed_image_path, "JPEG", quality=10)
        return compressed_image_path

    def downscale_image(self, image_path):
        image = Image.open(image_path)
        return image.resize((300, 300), Image.LANCZOS)

    def enhanced_color_code_image(self, image):
        color_map = {
            (173, 255, 47): (173, 255, 47),  # light green
            (0, 100, 0): (0, 100, 0),  # dark green
            (0, 0, 255): (0, 0, 255),  # blue
            (255, 255, 0): (255, 255, 0),  # yellow
            (255, 0, 0): (255, 0, 0),  # red
            (128, 128, 128): (128, 128, 128)  # grey
        }

        def closest_color(r, g, b):
            closest_dist = float('inf')
            closest_color = (r, g, b)
            for key, value in color_map.items():
                dist = ((key[0] - r) ** 2 + (key[1] - g) ** 2 + (key[2] - b) ** 2) ** 0.5
                if dist < closest_dist:
                    closest_dist = dist
                    closest_color = value
            return closest_color

        width, height = image.size
        new_image = image.copy()
        for i in range(width):
            for j in range(height):
                r, g, b = image.getpixel((i, j))
                new_color = closest_color(r, g, b)
                new_image.putpixel((i, j), new_color)
        return new_image

    def color_code_image(self, image):
        return self.enhanced_color_code_image(image)

    def image_to_qimage(self, image):
        image = image.convert("RGB")
        width, height = image.size
        data = image.tobytes("raw", "RGB")
        return QImage(data, width, height, QImage.Format_RGB888)


class AvianRasterMapSimplifier(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("AvianRasterMapSimplifier")
        self.setGeometry(100, 100, 800, 600)  # Make the main UI box bigger

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area_widget = QWidget()
        self.scroll_area.setWidget(self.scroll_area_widget)
        self.scroll_area.setWidgetResizable(True)

        self.scroll_layout = QVBoxLayout(self.scroll_area_widget)

        self.layout.addWidget(self.scroll_area)

        self.btn_open = QPushButton("Choose Image or PDF", self)
        self.btn_open.clicked.connect(self.open_file)
        self.scroll_layout.addWidget(self.btn_open)

        self.image_layout = QHBoxLayout()
        self.scroll_layout.addLayout(self.image_layout)

        self.original_image_label = QLabel(self)
        self.image_layout.addWidget(self.original_image_label)

        self.processed_image_label = QLabel(self)
        self.image_layout.addWidget(self.processed_image_label)

        self.progress_bar = QProgressBar(self)
        self.scroll_layout.addWidget(self.progress_bar)

        self.btn_save = QPushButton("Save Processed Image", self)
        self.btn_save.clicked.connect(self.save_image)
        self.scroll_layout.addWidget(self.btn_save)

        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.file_menu = self.menu_bar.addMenu('File')
        self.save_action = QAction('Save', self)
        self.save_action.triggered.connect(self.save_image)
        self.file_menu.addAction(self.save_action)

        self.processed_image = None
        self.tmp_files = ["compressed_image.jpg"]
        self.show()

    def open_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image or PDF File", "",
                                                   "Image Files (*.png *.jpg *.jpeg *.bmp);;PDF Files (*.pdf)",
                                                   options=options)
        if file_path:
            is_pdf = file_path.lower().endswith('.pdf')
            self.image_processor = ImageProcessor(file_path, is_pdf)
            self.image_processor.progress.connect(self.update_progress)
            self.image_processor.finished.connect(self.display_images)
            self.image_processor.error.connect(self.show_error)
            self.image_processor.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def display_images(self, original_qimage, processed_qimage):
        self.processed_image = processed_qimage
        processed_pixmap = QPixmap.fromImage(processed_qimage)
        processed_pixmap_cropped = processed_pixmap.copy(0, 0, 300, 300)  # Crop to 300x300
        self.processed_image_label.setPixmap(processed_pixmap_cropped)

        original_pixmap = QPixmap.fromImage(original_qimage)
        if not original_pixmap.isNull():
            self.original_image_label.setPixmap(original_pixmap.scaled(300, 300, Qt.KeepAspectRatio))

    def save_image(self):
        if self.processed_image:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "JPEG Files (*.jpg);;All Files (*)",
                                                       options=options)
            if file_path:
                processed_pixmap = QPixmap.fromImage(self.processed_image)
                processed_pixmap_cropped = processed_pixmap.copy(0, 0, 300, 300)  # Crop to 300x300
                processed_qimage = processed_pixmap_cropped.toImage()
                processed_qimage.save(file_path)

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def closeEvent(self, event):
        for tmp_file in self.tmp_files:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AvianRasterMapSimplifier()
    sys.exit(app.exec_())
