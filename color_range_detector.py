
# Modern PyQt5 GUI for HSV color selection
import sys
import cv2
import numpy as np
import pickle
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QSlider, QPushButton, QVBoxLayout, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

class ColorRangeSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('HSV Color Range Selector')
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.hsv_min = [0, 0, 0]
        self.hsv_max = [255, 255, 255]
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def init_ui(self):
        layout = QVBoxLayout()
        self.image_label = QLabel()
        layout.addWidget(self.image_label)

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
            layout.addLayout(hbox)
            self.sliders.append(slider)

        self.save_btn = QPushButton('Save Range')
        self.save_btn.clicked.connect(self.save_range)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def slider_changed(self):
        self.hsv_min = [self.sliders[0].value(), self.sliders[1].value(), self.sliders[2].value()]
        self.hsv_max = [self.sliders[3].value(), self.sliders[4].value(), self.sliders[5].value()]

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array(self.hsv_min), np.array(self.hsv_max))
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        preview = cv2.addWeighted(frame, 0.7, mask_bgr, 0.3, 0)
        rgb_image = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def save_range(self):
        t = (*self.hsv_min, *self.hsv_max)
        with open('range.pickle', 'wb') as f:
            pickle.dump(t, f)
        self.close()

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

def main():
    app = QApplication(sys.argv)
    selector = ColorRangeSelector()
    selector.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()