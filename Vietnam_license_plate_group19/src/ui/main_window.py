import cv2
import os
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QSizePolicy
)
from PySide6.QtGui import QPixmap, QImage, QFont
from PySide6.QtCore import QTimer, Qt

# Import các module xử lý 
from detect.yolov8_detect import YoloPlateDetector
from ocr.plate_easyocr import PlateOCR
from preprocess.plate_preprocessor import PlatePreprocessor
from database.db import save_plate
from ui.history_window import HistoryWindow
from logic.decision import auto_decision_from_db

# Import phần cứng
from arduino_comm.serial_control import BarrierController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ANPR - Vietnam License Plate Recognition")
        self.resize(1100, 650)
        # Biến cờ để tránh update UI khi chưa khởi tạo xong
        self.ui_ready = False
        QTimer.singleShot(300, lambda: setattr(self, "ui_ready", True))
        # Biến trạng thái
        self.current_plate = None
        self.current_confidence = None
        self.last_logged_plate = None
        self.no_plate_count = 0 
        # Cấu hình
        #  Sửa đường dẫn model cho đúng với máy !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        MODEL_PATH = r"D:\XuLiAnhSo_EPS\XLA_G19\Vietnam_license_plate_group19\models\yolov8\best.pt"
        # Cấu hình Camera và Arduino
        self.camera_url = "http://192.168.1.213:81/stream" # Hoặc số 0 nếu dùng webcam laptop
        self.arduino_port = "COM6"
        # Qui trình xử lí
        try:
            self.detector = YoloPlateDetector(MODEL_PATH, device=0, conf_thres=0.7)
            self.ocr = PlateOCR(gpu=True)
            self.pre = PlatePreprocessor() # Class tiền xử lý ảnh
            self.barrier = BarrierController(port=self.arduino_port)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Khởi Tạo", str(e))
        self.build_ui()
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.frame_count = 0
        self.is_allowed_signal = False

    # Giao diện
    def build_ui(self):
        # 1. Thiết lập nền tối 
        self.setStyleSheet("""
            QMainWindow { background-color: #202020; }
            QWidget { background-color: #202020; color: white; }
            QLabel { color: white; font-family: 'Segoe UI'; }
        """)
        # Khung camera ở phía bên trái
        self.image_label = QLabel("Đang chờ Camera...")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #aaaaaa; background-color: #000;")
        # Khung cắt biển số ở bên phải
        self.plate_crop_label = QLabel("Biển số")
        self.plate_crop_label.setFixedSize(380, 250)
        self.plate_crop_label.setAlignment(Qt.AlignCenter)
        self.plate_crop_label.setStyleSheet("border: 1px solid #aaaaaa; background-color: #000;")
        # Các nhãn thông tin ở bên dưới
        self.lbl_plate = self.make_label("Biển số: ---", 20, bold=True)
        self.lbl_type = self.make_label("Loại xe: ---", 16)
        self.lbl_color = self.make_label("Phân loại: ---", 16)
        self.lbl_status = self.make_label("Trạng thái: ...", 20, bold=True)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.addWidget(self.lbl_plate)
        info_layout.addWidget(self.lbl_type)
        info_layout.addWidget(self.lbl_color)
        info_layout.addWidget(self.lbl_status)
        info_layout.addStretch()
        # Các nút bấm
        self.btn_allow = QPushButton("✅ Cho vào")
        self.btn_deny = QPushButton("❌ Không cho vào")
        self.btn_history = QPushButton("📜 Lịch sử")
        self.btn_start = QPushButton("🎞 Start")
        self.btn_stop = QPushButton("⏹ Stop")
        # Style nút bấm
        btn_style = """
            QPushButton {
                background-color: #333333; color: white;
                border: 1px solid #555; padding: 8px;
                font-size: 14px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #555555; }
        """
        for btn in [self.btn_allow, self.btn_deny, self.btn_history, self.btn_start, self.btn_stop]:
            btn.setStyleSheet(btn_style)
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
        # Kết nối sự kiện nút bấm
        self.btn_history.clicked.connect(self.open_history)
        self.btn_start.clicked.connect(self.start_camera)
        self.btn_stop.clicked.connect(self.stop_camera)
        self.btn_allow.clicked.connect(self.force_allow)
        self.btn_deny.clicked.connect(self.force_deny)
        # Layout nút bấm
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addWidget(self.btn_allow)
        btn_layout.addWidget(self.btn_deny)
        btn_layout.addWidget(self.btn_history)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        # Tập hợp toàn bộ các layout
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.image_label, 1)
        left_layout.addLayout(btn_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.plate_crop_label)
        right_layout.addLayout(info_layout)
        right_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        main_layout.addLayout(left_layout, 7)
        main_layout.addLayout(right_layout, 3)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def make_label(self, text, size, bold=False):
        lbl = QLabel(text)
        weight = "bold" if bold else "normal"
        lbl.setStyleSheet(f"font-size: {size}px; font-weight: {weight}; color: white; padding: 2px;")
        lbl.setWordWrap(True)
        return lbl
    # Xây dựng logic chính
    def start_camera(self):
        # 1. Kết nối Arduino
        self.barrier.connect_arduino()
        # 2. Mở Camera
        self.cap = cv2.VideoCapture(self.camera_url)
        if not self.cap.isOpened():
             QMessageBox.warning(self, "Lỗi", "Không kết nối được Camera!")
             return
        self.timer.start(30) 

    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.barrier.close_connection()

    def update_frame(self):
        """Hàm này chạy liên tục mỗi 30ms"""
        if not self.cap: return
        ret, frame = self.cap.read()
        if not ret: return
        # Thay đổi kích thước để hiển thị lên giao diện
        display_frame = cv2.resize(frame, (800, 600))
        self.show_image(display_frame)
        self.frame_count += 1
        # Reset tín hiệu mở cổng mỗi 5 frame
        if self.frame_count % 5 == 0:
            self.is_allowed_signal = False 
        # Bắt đầu nhận dạng (Mỗi 5 frame chạy 1 lần) 
        if self.frame_count % 5 == 0:
            # 1. Phát hiện biển số (YOLO)
            crop, _, conf = self.detector.detect_and_crop(frame)
        
            if crop is not None:
                self.no_plate_count = 0 
                self.show_plate_crop(crop)
                # Quy trình Tiền xử lí ảnh
                # B1: Nhận diện màu sắc biển (Xanh/Đỏ/Vàng/Trắng)
                plate_color, _ = self.pre.detect_plate_color(crop)
                # B2: Hiệu chỉnh hình học (Chỉnh nghiêng)
                fixed, _ = self.pre.rectify_plate(crop)
                # B3: Chuẩn hóa màu sắc 
                # Biến đổi biển Xanh/Đỏ/Vàng => thành Nền trắng chữ đen cho OCR dễ đọc
                norm_img = self.pre.normalize_plate_color(fixed, plate_color)
                # B4: Tăng nét, khử nhiễu để OCR đọc chính xác
                ocr_img, _ = self.pre.enhance_for_ocr(norm_img)
                # Kết thúc Tiền xử lý
                # 2. Đọc ký tự (OCR)
                plate, plate_type, _ = self.ocr.recognize(ocr_img, plate_color)
                if plate:
                    self.current_plate = plate
                    self.current_confidence = conf
                    # 3. Ra quyết định (Check Database/Check màu xe ưu tiên)
                    allowed = auto_decision_from_db(plate, plate_color)
                    decision = "ALLOW" if allowed else "DENY"
                    # Cập nhật giao diện
                    self.lbl_plate.setText(f"Biển số: {plate}")
                    
                    xe_text = "Ô tô" if plate_type == "car" else "Xe máy"
                    self.lbl_type.setText(f"Loại xe: {xe_text}")
                    #  Viết logic hiển thị phân loại màu
                    p_color = plate_color.lower().strip()
                    phan_loai_text = "---"
                    
                    if p_color == "blue":
                        phan_loai_text = "🟦 XE CƠ QUAN NHÀ NƯỚC"
                    elif p_color == "red":
                        phan_loai_text = "🟥 XE QUÂN ĐỘI"
                    elif p_color == "yellow":
                        phan_loai_text = "🟨 XE DỊCH VỤ / KD"
                    else:
                        if plate_type == "car":
                            phan_loai_text = "⬜ XE Ô TÔ DÂN SỰ"
                        else:
                            phan_loai_text = "⬜ XE MÁY DÂN SỰ"
                    self.lbl_color.setText(f"Phân loại: {phan_loai_text}")
                    # Trạng thái được phép/cấm
                    if allowed:
                        self.lbl_status.setText("Trạng thái: ✅ ĐƯỢC PHÉP")
                        self.lbl_status.setStyleSheet("color: #00FF00; font-weight: bold; font-size: 22px;") # Xanh lá
                        self.is_allowed_signal = True 
                    else:
                        self.lbl_status.setText("Trạng thái: ❌ KHÔNG ĐƯỢC PHÉP")
                        self.lbl_status.setStyleSheet("color: #FF3333; font-weight: bold; font-size: 22px;") # Đỏ
                    # 4. Lưu vào vào CSDL và lưu ảnh
                    if plate != self.last_logged_plate:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{plate}_{timestamp}.jpg"
                        save_folder = "captured_images"
                        if not os.path.exists(save_folder): os.makedirs(save_folder)
                        full_path = os.path.join(save_folder, filename)
                        # Lưu ảnh cắt ảnh gốc (có màu) để dễ nhìn lại
                        cv2.imwrite(full_path, crop)
                        save_plate(plate, conf, decision, full_path)
                        self.last_logged_plate = plate
            else:
                # Đối với trường hợp không phát hiện biển số xe (Xe đã đi qua hoặc chưa tới)
                self.no_plate_count += 1
                # Giảm từ 40 xuống 10 (khoảng 1.5 giây) để reset nhanh hơn
                if self.no_plate_count > 10 and "Đang chờ" not in self.lbl_status.text():
                    self.reset_ui()
                    self.is_allowed_signal = False # Ngắt lệnh mở cổng ngay
        # Gửi tín hiệu xuống Arduino (Mở/Đóng Barrier)
        self.barrier.process_logic(self.is_allowed_signal)
    def show_image(self, img):
        if not self.ui_ready: return
        # Chuyển BGR (OpenCV) -> RGB (Qt)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def show_plate_crop(self, crop):
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.plate_crop_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.plate_crop_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def open_history(self):
        self.history = HistoryWindow()
        self.history.show()

    def reset_ui(self):
        self.lbl_plate.setText("Biển số: ---")
        self.lbl_type.setText("Loại xe: ---")
        self.lbl_color.setText("Phân loại: ---")
        
        self.lbl_status.setText("Trạng thái: ⏳ Đang chờ xe...")
        self.lbl_status.setStyleSheet("color: #FFFF00; font-weight: bold; font-size: 22px;") # Vàng
        
        self.plate_crop_label.clear()
        self.plate_crop_label.setText("Biển số")
        
        self.last_logged_plate = None
        self.current_plate = None

    def force_allow(self):
        # Nút bấm mở cổng thủ công
        self.barrier.send_cmd(b'1')
        self.barrier.is_open = True
        self.barrier.last_vehicle_time = time.time()
        plate = self.current_plate if self.current_plate else "MANUAL"
        save_plate(plate, 1.0, "ALLOW (MANUAL)", "manual_open")
        self.lbl_status.setText("Trạng thái: ✅ MỞ THỦ CÔNG")
        self.lbl_status.setStyleSheet("color: #00FF00; font-weight: bold; font-size: 22px;")
        
        QTimer.singleShot(3000, self.reset_ui)

    def force_deny(self):
        # Nút bấm đóng cổng thủ công
        self.barrier.send_cmd(b'0')
        self.barrier.is_open = False
        plate = self.current_plate if self.current_plate else "MANUAL"
        save_plate(plate, 1.0, "DENY (MANUAL)", "manual_close")
        self.lbl_status.setText("Trạng thái: ❌ ĐÓNG THỦ CÔNG")
        self.lbl_status.setStyleSheet("color: #FF3333; font-weight: bold; font-size: 22px;")
        QTimer.singleShot(2000, self.reset_ui)

    def closeEvent(self, event):
        self.stop_camera()
        if hasattr(self, 'barrier') and self.barrier:
            self.barrier.close_connection()
        event.accept()