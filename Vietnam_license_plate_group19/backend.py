# backend.py
import re
from typing import Dict, Any, List, Optional

import cv2
import numpy as np
import torch
from ultralytics import YOLO
import easyocr
from pathlib import Path

# Thư mục chứa file backend.py
BASE_DIR = Path(__file__).resolve().parent
# Đường dẫn model mặc định: BASE_DIR / "license_plate" / "license_plate_best.pt"
DEFAULT_MODEL_PATH = BASE_DIR / "license_plate" / "license_plate_best.pt"

# ============================================
# 1. HÀM CHUẨN HÓA BIỂN SỐ
# ============================================

PLATE_PATTERN = re.compile(r"^[0-9A-Z]{8}$")  # ví dụ: 8 ký tự [0-9A-Z]

def correct_plate_format(ocr_text: str) -> str:
    """
    Nhận chuỗi OCR (raw), chuẩn hoá về dạng 8 ký tự [0-9A-Z].
    Trả về "" nếu không hợp lệ.
    Logic dựa trên code bạn đã dùng trong notebook.
    """
    if not isinstance(ocr_text, str):
        ocr_text = str(ocr_text)

    # Viết hoa + chỉ giữ A-Z, 0-9
    ocr_text = ocr_text.upper()
    ocr_text = re.sub(r"[^A-Z0-9]", "", ocr_text)

    if len(ocr_text) != 8:
        return ""

    # Map lỗi OCR hay gặp
    map_to_letter = {"0": "O", "1": "I", "5": "S", "8": "B", "6": "G", "2": "Z"}
    map_to_digit  = {"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7"}

    chars = list(ocr_text)

    # 0–1, 3–7 phải là số
    for i in [0, 1, 3, 4, 5, 6, 7]:
        ch = chars[i]
        if ch.isalpha():
            chars[i] = map_to_digit.get(ch, ch)

    # 2 phải là chữ
    ch = chars[2]
    if ch.isdigit():
        chars[2] = map_to_letter.get(ch, ch)

    candidate = "".join(chars)
    if PLATE_PATTERN.match(candidate):
        return candidate
    return ""

# ============================================
# 2. BACKEND: LOAD MODEL + PIPELINE
# ============================================

class PlateBackend:
    """
    Backend:
      - Load YOLO model từ license_plate/license_plate_best.pt (tương đối so với backend.py)
      - Load EasyOCR
      - Cung cấp hàm process_image & process_image_path
    """

    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = True):
        """
        model_path:
          - None: tự dùng DEFAULT_MODEL_PATH (license_plate/license_plate_best.pt)
          - Nếu truyền chuỗi tương đối: tính tương đối so với BASE_DIR
          - Nếu là đường dẫn tuyệt đối: dùng luôn.
        use_gpu: True nếu muốn dùng GPU (nếu có CUDA).
        """
        if model_path is None:
            model_path_path = DEFAULT_MODEL_PATH
        else:
            mp = Path(model_path)
            if mp.is_absolute():
                model_path_path = mp
            else:
                model_path_path = BASE_DIR / mp  # đường dẫn tương đối → tính từ BASE_DIR

        if not model_path_path.exists():
            raise FileNotFoundError(f"Không tìm thấy model: {model_path_path}")

        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"

        # Load YOLO
        self.model = YOLO(str(model_path_path))
        self.model.to(self.device)

        # Load EasyOCR
        self.reader = easyocr.Reader(
            ["en"],
            gpu=(use_gpu and torch.cuda.is_available())
        )

    # -------------------------
    # HÀM XỬ LÝ ẢNH (MẢNG BGR)
    # -------------------------
    def process_image(self, img_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Nhận 1 ảnh BGR, chạy:
          1. YOLO detect biển số
          2. Chọn bbox có conf cao nhất
          3. Crop + tiền xử lý
          4. OCR + chuẩn hóa
          5. Vẽ kết quả lên ảnh

        Trả về dict:
          {
            "plate_text": str,
            "annotated": np.ndarray(BGR),
            "bbox": {x1,y1,x2,y2,conf} hoặc None,
            "debug": {
                "plate_crop": np.ndarray|None,
                "gray_blur": np.ndarray|None,
                "thresh": np.ndarray|None,
                "resized": np.ndarray|None,
                "ocr_raw": List[str],
            }
          }
        """
        h, w = img_bgr.shape[:2]

        result = {
            "plate_text": "",
            "annotated": img_bgr.copy(),
            "bbox": None,
            "debug": {
                "plate_crop": None,
                "gray_blur": None,
                "thresh": None,
                "resized": None,
                "ocr_raw": [],
            },
        }

        # 1) YOLO detect
        yolo_results = self.model(img_bgr, verbose=False, device=self.device)
        r = yolo_results[0]

        if len(r.boxes) == 0:
            return result  # không có bbox

        # 2) Chọn bbox có confidence cao nhất
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

        bbox_dict = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "conf": best_conf}
        result["bbox"] = bbox_dict

        plate_crop = img_bgr[y1:y2, x1:x2].copy()
        result["debug"]["plate_crop"] = plate_crop

        # 3) Tiền xử lý
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(
            gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        resized = cv2.resize(
            thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )

        result["debug"]["gray_blur"] = gray_blur
        result["debug"]["thresh"] = thresh
        result["debug"]["resized"] = resized

        # 4) OCR
        ocr_texts: List[str] = self.reader.readtext(
            resized,
            detail=0,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        )
        result["debug"]["ocr_raw"] = ocr_texts

        plate_final = ""
        if len(ocr_texts) > 0:
            plate_final = correct_plate_format(ocr_texts[0])

        result["plate_text"] = plate_final

        # 5) Vẽ kết quả lên ảnh gốc
        annotated = img_bgr.copy()
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
        if plate_final:
            cv2.putText(
                annotated,
                plate_final,
                (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 0),
                3,
            )

        result["annotated"] = annotated
        return result

    # -------------------------
    # HÀM XỬ LÝ TỪ ĐƯỜNG DẪN ẢNH
    # -------------------------
    def process_image_path(self, image_path: str) -> Dict[str, Any]:
        """
        image_path:
          - Nếu là đường dẫn tương đối: coi như tương đối so với BASE_DIR (thư mục chứa backend.py)
          - Nếu tuyệt đối: dùng luôn.
        """
        p = Path(image_path)
        if not p.is_absolute():
            p = BASE_DIR / p  # đường dẫn tương đối → tính từ BASE_DIR

        img_bgr = cv2.imread(str(p))
        if img_bgr is None:
            raise FileNotFoundError(f"Không đọc được ảnh: {p}")
        return self.process_image(img_bgr)