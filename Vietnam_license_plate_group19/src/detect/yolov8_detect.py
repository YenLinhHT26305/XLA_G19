import cv2
from ultralytics import YOLO
import torch

class YoloPlateDetector:
    def __init__(self, model_path, device=0, conf_thres=0.7):
        self.model = YOLO(model_path)
        self.device = device
        self.conf_thres = conf_thres

    def detect_and_crop(self, img):
        # Phát hiện biển số
        # Lấy bounding box tốt nhất
        # Crop ảnh biển số
        # Trả về kết quả cho OCR xử lý tiếp
        h, w = img.shape[:2]

        results = self.model(img, conf=self.conf_thres, device=self.device, verbose=False)
        r = results[0]

        if len(r.boxes) == 0:
            return None, None, 0.0

        best_box = None
        best_conf = 0.0
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf > best_conf:
                best_conf = conf
                best_box = box

        x1, y1, x2, y2 = map(int, best_box.xyxy.cpu().numpy()[0])
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(w, x2); y2 = min(h, y2)
        plate_crop = img[y1:y2, x1:x2].copy()
        return plate_crop, (x1, y1, x2, y2), best_conf
