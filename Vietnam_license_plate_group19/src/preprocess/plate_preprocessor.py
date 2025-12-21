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

    # Utils hình học
    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]      # Góc trên phía bên trái
        rect[2] = pts[np.argmax(s)]      # Góc dưới phía bên phải
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]   # Góc trên phía bên phải
        rect[3] = pts[np.argmax(diff)]   # Góc dưới phía bên phải
        return rect

    # Bước 0: Thực hiện nhận dạng màu biển số
    def detect_plate_color(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, w = img.shape[:2]
        total_pixels = h * w

        # 1. Định nghĩa các mặt nạ màu
        # Màu đỏ: Kết hợp 2 dải (0-10 và 170-180)
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)

        # Màu xanh dương
        lower_blue = np.array([90, 50, 50]) 
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

        # Màu vàng
        lower_yellow = np.array([15, 50, 50]) 
        upper_yellow = np.array([35, 255, 255])
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # 2. Đếm số pixel
        pixel_count = {
            "red": cv2.countNonZero(mask_red),
            "blue": cv2.countNonZero(mask_blue),
            "yellow": cv2.countNonZero(mask_yellow)
        }

        # 3. Quyết định
        detected_color = max(pixel_count, key=pixel_count.get)
        max_val = pixel_count[detected_color]

        # Nếu màu tìm được chiếm < 20% diện tích thì mình coi như là màu trắng
        if max_val < (total_pixels * 0.2):
            return "white", {}

        return detected_color, {}

    # Bước 1: Hiệu chỉnh hình học
    def rectify_plate(self, img):
        debug = {}
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Nếu không tìm thấy khung biển số, trả về ảnh gốc
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

            max_w = max(w_top, w_bot)
            if max_w == 0: return img, debug # Tránh chia cho 0

            warp_ratio = abs(w_top - w_bot) / max_w
            angle = rect[-1]
            if angle < -45: angle += 90

            if warp_ratio > self.warp_ratio_thresh:
                width = int(max_w)
                height = int(max(h_left, h_right))
                dst = np.array([[0, 0], [width-1, 0], [width-1, height-1], [0, height-1]], dtype="float32")
                M = cv2.getPerspectiveTransform(src, dst)
                fixed = cv2.warpPerspective(img, M, (width, height))
                debug["method"] = "perspective"
            else:
                if abs(angle) > self.angle_limit: angle = 0.0
                h, w = img.shape[:2]
                M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                fixed = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                debug["method"] = "deskew"

            return fixed, debug
            
        except Exception:
            # Nếu lỗi bất kỳ bước nào, trả về ảnh gốc để chương trình không bị lỗi, ảnh không bị vỡ
            return img, debug

    # Bước 2: Chuẩn hoá màu
    def normalize_plate_color(self, img, plate_color):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 1. Biểm xanh/đỏ: Chữ trắng
        if plate_color in ("blue", "red"):
            # Lọc lấy chữ trắng: Độ bảo hoà thấp (<100), Giá trị cao (>150)
            mask_text = cv2.inRange(
                hsv,
                np.array([0, 0, 150]), 
                np.array([180, 100, 255])
            )

        # 2. Biển vàng: Chữ đen
        elif plate_color == "yellow":
            # Lọc lấy chữ đen: Giá trị thấp
            mask_text = cv2.inRange(
                hsv,
                np.array([0, 0, 0]),
                np.array([180, 255, 100])
            )

        # 3. Biển xám => Chuyển xám bình thường
        else:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Tạo ảnh đầu ra: Nền trắng (255), chữ đen (0)
        # Bất kỳ điểm ảnh nào là chữ sẽ được tô màu đen
        normalized = np.ones(img.shape[:2], dtype=np.uint8) * 255
        normalized[mask_text > 0] = 0

        return normalized

    # Bước 3: Tăng cường ảnh cho OCR
    def enhance_for_ocr(self, img):
        debug = {}
        # Input có thể là ảnh xám hoặc màu, chuyển về xám 
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        # 1. Tăng kích thước x2
        up = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # 2. Tăng tương phản cục bộ
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(up)

        debug.update({"upscaled": up, "clahe": cl})
        return cl, debug