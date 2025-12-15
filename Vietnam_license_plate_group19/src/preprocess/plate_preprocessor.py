import cv2
import numpy as np

class PlatePreprocessor:
    def __init__(self,
                 warp_ratio_thresh=0.15,
                 angle_limit=15,
                 debug=False):
        self.warp_ratio_thresh = warp_ratio_thresh
        self.angle_limit = angle_limit
        self.debug = debug

    # =========================
    # Utils hình học
    # =========================
    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]      # top-left
        rect[2] = pts[np.argmax(s)]      # bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]   # top-right
        rect[3] = pts[np.argmax(diff)]   # bottom-left
        return rect

    # ==================================
    # BƯỚC 0: NHẬN DIỆN MÀU BIỂN SỐ
    # ==================================
    def detect_plate_color(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        ranges = {
            "white":  (np.array([0, 0, 180]),   np.array([180, 60, 255])),
            "blue":   (np.array([90, 80, 80]),  np.array([130, 255, 255])),
            "yellow": (np.array([15, 80, 80]),  np.array([35, 255, 255])),
            "red":    (np.array([0, 80, 80]),   np.array([10, 255, 255]))
        }

        pixel_count = {}
        masks = {}

        for color, (lower, upper) in ranges.items():
            mask = cv2.inRange(hsv, lower, upper)
            masks[color] = mask
            pixel_count[color] = cv2.countNonZero(mask)

        detected_color = max(pixel_count, key=pixel_count.get)
        return detected_color, masks

    # ==========================================
    # BƯỚC 1: HIỆU CHỈNH HÌNH HỌC BIỂN SỐ
    # ==========================================
    def rectify_plate(self, img):
        debug = {}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        _, thresh = cv2.threshold(
            blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return img, debug

        cnt = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        src = self.order_points(np.float32(box))

        w_top = np.linalg.norm(src[0] - src[1])
        w_bot = np.linalg.norm(src[3] - src[2])
        h_left = np.linalg.norm(src[0] - src[3])
        h_right = np.linalg.norm(src[1] - src[2])

        warp_ratio = abs(w_top - w_bot) / max(w_top, w_bot)

        angle = rect[-1]
        if angle < -45:
            angle += 90

        if warp_ratio > self.warp_ratio_thresh:
            width = int(max(w_top, w_bot))
            height = int(max(h_left, h_right))

            dst = np.array([
                [0, 0],
                [width - 1, 0],
                [width - 1, height - 1],
                [0, height - 1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(src, dst)
            fixed = cv2.warpPerspective(img, M, (width, height))
            debug["method"] = "perspective"
        else:
            if abs(angle) > self.angle_limit:
                angle = 0.0

            h, w = img.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            fixed = cv2.warpAffine(
                img, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            debug["method"] = "deskew"

        debug.update({
            "gray": gray,
            "blur": blur,
            "thresh": thresh,
            "warp_ratio": warp_ratio,
            "angle": angle
        })

        return fixed, debug

    # ==========================================
    # BƯỚC 2: CHUẨN HÓA MÀU (CHỮ ĐEN – NỀN TRẮNG)
    # ==========================================
    def normalize_plate_color(self, img, plate_color):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        if plate_color in ("blue", "red"):
            # chữ trắng
            mask_text = cv2.inRange(
                hsv,
                np.array([0, 0, 200]),
                np.array([180, 50, 255])
            )

        elif plate_color == "yellow":
            # chữ đen
            mask_text = cv2.inRange(
                hsv,
                np.array([0, 0, 0]),
                np.array([180, 255, 80])
            )

        else:
            # biển trắng → grayscale
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # tạo ảnh chữ đen nền trắng
        normalized = np.ones_like(mask_text) * 255
        normalized[mask_text > 0] = 0

        return normalized

    # ==================================
    # BƯỚC 3: TĂNG CƯỜNG ẢNH CHO OCR
    # ==================================
    def enhance_for_ocr(self, img):
        debug = {}

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Phóng to để OCR đọc nét hơn
        up = cv2.resize(
            gray, None,
            fx=2, fy=2,
            interpolation=cv2.INTER_CUBIC
        )

        # Tăng tương phản cục bộ (rất tốt cho OCR)
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )
        cl = clahe.apply(up)

        debug.update({
            "gray": gray,
            "upscaled": up,
            "clahe": cl
        })

        return cl, debug
