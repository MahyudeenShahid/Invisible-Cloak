import sys
import cv2
import numpy as np
import pickle
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QSlider, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

EFFECTS = ['none', 'pixelate', 'blur', 'cartoon']

class MainGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Invisible Cloak - All-in-One')
        self.cap = None
        self.hsv_min = [0, 0, 0]
        self.hsv_max = [255, 255, 255]
        self.effect_idx = 0
        self.running = False
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.image_label = QLabel('Camera Preview')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('background-color: #222;')
        self.image_label.mousePressEvent = self.pick_color_from_frame
        main_layout.addWidget(self.image_label)
        
        # HSV sliders
        self.sliders = []
        slider_labels = ['H Min', 'S Min', 'V Min', 'H Max', 'S Max', 'V Max']
        self.slider_values = [0, 0, 0, 255, 255, 255]
        for i, label in enumerate(slider_labels):
            hbox = QHBoxLayout()
            lbl = QLabel(label)
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(255)
            slider.setValue(self.slider_values[i])
            slider.valueChanged.connect(self.slider_changed)
            hbox.addWidget(lbl)
            hbox.addWidget(slider)
            main_layout.addLayout(hbox)
            self.sliders.append(slider)

        # Effect selector
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(EFFECTS)
        self.effect_combo.currentIndexChanged.connect(self.effect_changed)
        main_layout.addWidget(QLabel('Effect:'))
        main_layout.addWidget(self.effect_combo)

        # Buttons
        self.bg_btn = QPushButton('Capture Background')
        self.bg_btn.clicked.connect(self.capture_background)
        main_layout.addWidget(self.bg_btn)

        self.start_btn = QPushButton('Start Invisibility')
        self.start_btn.clicked.connect(self.toggle_invisibility)
        main_layout.addWidget(self.start_btn)

        self.save_btn = QPushButton('Save HSV Range')
        self.save_btn.clicked.connect(self.save_range)
        main_layout.addWidget(self.save_btn)

        self.setLayout(main_layout)
    def pick_color_from_frame(self, event):
        # Only pick color if a frame is available
        if self.cap is None:
            return
        ret, img = self.cap.read()
        if not ret:
            return
        img = cv2.flip(img, 1)
        # Get click position relative to label size
        label_w = self.image_label.width()
        label_h = self.image_label.height()
        h, w, _ = img.shape
        x = int(event.pos().x() * w / label_w)
        y = int(event.pos().y() * h / label_h)
        if 0 <= x < w and 0 <= y < h:
            bgr = img[y, x]
            hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
            # Convert to int to avoid overflow
            h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
            hmin = max(0, h - 20)
            smin = max(0, s - 40)
            vmin = max(0, v - 40)
            hmax = min(179, h + 20)
            smax = min(255, s + 40)
            vmax = min(255, v + 40)
            self.sliders[0].setValue(hmin)
            self.sliders[1].setValue(smin)
            self.sliders[2].setValue(vmin)
            self.sliders[3].setValue(hmax)
            self.sliders[4].setValue(smax)
            self.sliders[5].setValue(vmax)
            QMessageBox.information(self, 'Color Picked', f'HSV: {[h, s, v]}\nSliders updated!')

    def init_ui_continued(self):
        main_layout = QVBoxLayout()
        
        # HSV sliders
        self.sliders = []
        slider_labels = ['H Min', 'S Min', 'V Min', 'H Max', 'S Max', 'V Max']
        self.slider_values = [0, 0, 0, 255, 255, 255]
        for i, label in enumerate(slider_labels):
            hbox = QHBoxLayout()
            lbl = QLabel(label)
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(255)
            slider.setValue(self.slider_values[i])
            slider.valueChanged.connect(self.slider_changed)
            hbox.addWidget(lbl)
            hbox.addWidget(slider)
            main_layout.addLayout(hbox)
            self.sliders.append(slider)

        # Effect selector
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(EFFECTS)
        self.effect_combo.currentIndexChanged.connect(self.effect_changed)
        main_layout.addWidget(QLabel('Effect:'))
        main_layout.addWidget(self.effect_combo)

        # Buttons
        self.bg_btn = QPushButton('Capture Background')
        self.bg_btn.clicked.connect(self.capture_background)
        main_layout.addWidget(self.bg_btn)

        self.start_btn = QPushButton('Start Invisibility')
        self.start_btn.clicked.connect(self.toggle_invisibility)
        main_layout.addWidget(self.start_btn)

        self.save_btn = QPushButton('Save HSV Range')
        self.save_btn.clicked.connect(self.save_range)
        main_layout.addWidget(self.save_btn)

        self.setLayout(main_layout)

    def slider_changed(self):
        self.hsv_min = [self.sliders[0].value(), self.sliders[1].value(), self.sliders[2].value()]
        self.hsv_max = [self.sliders[3].value(), self.sliders[4].value(), self.sliders[5].value()]

    def effect_changed(self, idx):
        self.effect_idx = idx

    def capture_background(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        # Capture background
        ret, frame = self.cap.read()
        if ret:
            self.background = cv2.flip(frame, 1)
            QMessageBox.information(self, 'Background', 'Background captured!')
        else:
            QMessageBox.warning(self, 'Error', 'Failed to capture background.')

    def save_range(self):
        t = (*self.hsv_min, *self.hsv_max)
        with open('range.pickle', 'wb') as f:
            pickle.dump(t, f)
        QMessageBox.information(self, 'Saved', 'HSV range saved to range.pickle')

    def toggle_invisibility(self):
        if not hasattr(self, 'background'):
            QMessageBox.warning(self, 'Error', 'Please capture background first!')
            return
        if self.cap is None:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.running = not self.running
        if self.running:
            self.start_btn.setText('Stop Invisibility')
            self.timer.start(30)
        else:
            self.start_btn.setText('Start Invisibility')
            self.timer.stop()

    def update_frame(self):
        if not self.running:
            return
        ret, img = self.cap.read()
        if not ret:
            return
        img = cv2.flip(img, 1)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array(self.hsv_min), np.array(self.hsv_max))
        mask1 = cv2.morphologyEx(mask1, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
        mask1 = cv2.morphologyEx(mask1, cv2.MORPH_DILATE, np.ones((3,3), np.uint8))
        mask2 = cv2.bitwise_not(mask1)
        res1 = cv2.bitwise_and(img, img, mask=mask2)
        res2 = cv2.bitwise_and(self.background, self.background, mask=mask1)
        final = cv2.addWeighted(res1, 1, res2, 1, 0)
        final = self.apply_effect(final, EFFECTS[self.effect_idx])
        rgb_image = cv2.cvtColor(final, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def apply_effect(self, img, effect):
        if effect == 'pixelate':
            h, w = img.shape[:2]
            temp = cv2.resize(img, (w//16, h//16), interpolation=cv2.INTER_LINEAR)
            return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
        elif effect == 'blur':
            return cv2.GaussianBlur(img, (21, 21), 0)
        elif effect == 'cartoon':
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.medianBlur(gray, 7)
            edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                          cv2.THRESH_BINARY, 9, 9)
            color = cv2.bilateralFilter(img, 9, 250, 250)
            cartoon = cv2.bitwise_and(color, color, mask=edges)
            return cartoon
        return img

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = MainGUI()
    gui.show()
    sys.exit(app.exec_())
