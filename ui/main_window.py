import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QSizePolicy
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QTimer, Qt

from detect.yolov8_detect import YoloPlateDetector
from ocr.plate_easyocr import PlateOCR
from preprocess.plate_preprocessor import PlatePreprocessor
from database.db import save_plate

from ui.history_window import HistoryWindow
from logic.decision import auto_decision_from_db


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ANPR – Vietnam License Plate")
        self.resize(1000, 600)

        self.ui_ready = False
        QTimer.singleShot(300, lambda: setattr(self, "ui_ready", True))
        self.current_plate = None
        self.current_confidence = None
        self.last_logged_plate = None

        # ===== PIPELINE =====
        self.detector = YoloPlateDetector(
            "Vietnam_license_plate_group19/models/yolov8/best.pt",
            device=0,
            conf_thres=0.7
        )
        self.ocr = PlateOCR(gpu=True)
        self.pre = PlatePreprocessor()

        self.build_ui()

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.frame_count = 0
        self.process_interval = 15

    # ================= UI =================
    def build_ui(self):
        self.image_label = QLabel("Camera")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background:black; border:2px solid #444;")

        self.plate_crop_label = QLabel("Biển số (YOLO)")
        self.plate_crop_label.setFixedSize(380, 300)
        self.plate_crop_label.setAlignment(Qt.AlignCenter)
        self.plate_crop_label.setStyleSheet("border:2px solid #666; background:#111;")

        self.lbl_plate = self.make_label(22, bold=True)
        self.lbl_type = self.make_label(20)
        self.lbl_color = self.make_label(20)
        self.lbl_status = self.make_label(22, bold=True)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        for w in [self.lbl_plate, self.lbl_type, self.lbl_color, self.lbl_status]:
            info_layout.addWidget(w)

        self.btn_allow = QPushButton("✅ Cho vào")
        self.btn_deny = QPushButton("❌ Không cho vào")
        self.btn_history = QPushButton("📜 Lịch sử")
        self.btn_start = QPushButton("🎥 Start")
        self.btn_stop = QPushButton("⏹ Stop")

        self.btn_history.clicked.connect(self.open_history)
        self.btn_start.clicked.connect(self.start_camera)
        self.btn_stop.clicked.connect(self.stop_camera)
        self.btn_allow.clicked.connect(self.force_allow)
        self.btn_deny.clicked.connect(self.force_deny)

        btn_layout = QHBoxLayout()
        for b in [self.btn_allow, self.btn_deny, self.btn_history, self.btn_start, self.btn_stop]:
            b.setMinimumHeight(40)
            b.setStyleSheet("font-size:16px;")
            btn_layout.addWidget(b)

        left = QVBoxLayout()
        left.addWidget(self.image_label, 1)
        left.addLayout(btn_layout)

        right = QVBoxLayout()
        right.addWidget(self.plate_crop_label)
        right.addLayout(info_layout)

        main = QHBoxLayout()
        main.addLayout(left, 4)
        main.addLayout(right, 1)

        container = QWidget()
        container.setLayout(main)
        self.setCentralWidget(container)

    def make_label(self, size, bold=False):
        lbl = QLabel("---")
        lbl.setFixedHeight(28)
        lbl.setStyleSheet(
            f"font-size:{size}px; font-weight:{'bold' if bold else 'normal'};"
            "margin:0; padding:0; color:white;"
        )
        return lbl

    # ================= CAMERA =================
    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.timer.start(30)

    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

    def update_frame(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        self.show_image(frame)
        self.frame_count += 1
        if self.frame_count % self.process_interval != 0:
            return

        crop, _, conf = self.detector.detect_and_crop(frame)
        if crop is None:
            return

        self.show_plate_crop(crop)
        plate_color, _ = self.pre.detect_plate_color(crop)
        fixed, _ = self.pre.rectify_plate(crop)
        ocr_img, _ = self.pre.enhance_for_ocr(fixed)

        plate, plate_type, _ = self.ocr.recognize(ocr_img)
        if not plate:
            return
        
        self.current_plate = plate
        self.current_confidence = conf

        allowed = auto_decision_from_db(plate, plate_color)
        decision = "ALLOW" if allowed else "DENY"

        self.lbl_plate.setText(f"Biển số: {plate}")
        self.lbl_type.setText("Loại xe: Ô tô" if plate_type == "car" else "Loại xe: Gắn máy")
        self.lbl_color.setText("Màu biển: white")
        self.lbl_status.setText(
            "Trạng thái: ✅ ĐƯỢC PHÉP" if allowed else "Trạng thái: ❌ KHÔNG ĐƯỢC PHÉP"
        )

        if plate != self.last_logged_plate:
            save_plate(plate, conf, decision, "camera")
            self.last_logged_plate = plate


    # ================= DISPLAY =================
    def show_image(self, img):
        if not self.ui_ready:
            return
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0],
                      rgb.strides[0], QImage.Format_RGB888)
        self.image_label.setPixmap(
            QPixmap.fromImage(qimg).scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def show_plate_crop(self, crop):
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0],
                      rgb.strides[0], QImage.Format_RGB888)
        self.plate_crop_label.setPixmap(
            QPixmap.fromImage(qimg).scaled(
                self.plate_crop_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def open_history(self):
        self.history = HistoryWindow()
        self.history.show()

    def force_allow(self):
        if not self.current_plate:
            QMessageBox.warning(self, "Lỗi", "Chưa có biển số để xử lý")
            return

        save_plate(
            self.current_plate,
            self.current_confidence or 1.0,
            "ALLOW",
            image_path="manual"
        )

        self.lbl_status.setText("Trạng thái: ✅ ĐƯỢC PHÉP (MANUAL)")
        QMessageBox.information(self, "Override", "Đã CHO PHÉP xe vào (ghi log)")


    def force_deny(self):
        if not self.current_plate:
            QMessageBox.warning(self, "Lỗi", "Chưa có biển số để xử lý")
            return

        save_plate(
            self.current_plate,
            self.current_confidence or 1.0,
            "DENY",
            image_path="manual"
        )

        self.lbl_status.setText("Trạng thái: ❌ KHÔNG ĐƯỢC PHÉP (MANUAL)")
        QMessageBox.warning(self, "Override", "Đã TỪ CHỐI xe vào (ghi log)")

