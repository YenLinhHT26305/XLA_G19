import cv2
import re
import easyocr
from collections import Counter

class PlateOCR:
    def __init__(self, gpu=True):
        self.reader = easyocr.Reader(['en'], gpu=gpu)
        self.car_pattern = re.compile(r"^[A-Z0-9]{8}$")
        self.bike_pattern = re.compile(r"^[A-Z0-9]{9}$")

    def _match_plate(self, text):
        if self.car_pattern.match(text):
            return text, "car"
        if self.bike_pattern.match(text):
            return text, "bike"
        return "", ""

    def _correct_plate_format(self, text: str) -> str:
        text = text.upper()
        text = re.sub(r"[^A-Z0-9]", "", text)

        if len(text) not in (8, 9):
            return ""

        map_to_letter = {"0": "O", "1": "I", "5": "S", "8": "B", "6": "G", "2": "Z"}
        map_to_digit  = {"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7"}

        chars = list(text)

        for i in [0, 1, 3, 4, 5, 6, 7]:
            if chars[i].isalpha():
                chars[i] = map_to_digit.get(chars[i], chars[i])

        if chars[2].isdigit():
            chars[2] = map_to_letter.get(chars[2], chars[2])

        return "".join(chars)


    def recognize(self, plate_img):
        # Gray
        if len(plate_img.shape) == 2:
            gray = plate_img
        else:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)

        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # Adaptive threshold (tốt cho 2 dòng & biển màu)
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31, 15
        )

        # Tự đảo nếu nền tối – chữ sáng
        white_ratio = cv2.countNonZero(thresh) / thresh.size
        if white_ratio < 0.4:
            thresh = cv2.bitwise_not(thresh)

        resized = cv2.resize(
            thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )

        # 🔑 LẤY BOX + TEXT
        results = self.reader.readtext(
            resized,
            detail=1,      # lấy cả bbox
            paragraph=False,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )

        if not results:
            return "", "", ""

        # 🔑 SẮP XẾP THEO TRỤC Y (dòng trên → dưới)
        results = sorted(results, key=lambda r: r[0][0][1])

        # 🔑 GHÉP ĐÚNG THỨ TỰ
        raw_text = "".join([r[1] for r in results])

        corrected = self._correct_plate_format(raw_text)
        plate, plate_type = self._match_plate(corrected)

        return plate, plate_type, raw_text

    def ocr_vote(self,texts):
        # bỏ chuỗi rỗng
        texts = [t for t in texts if t]
        if not texts:
            return ""

        # lấy độ dài phổ biến nhất
        lengths = [len(t) for t in texts]
        target_len = Counter(lengths).most_common(1)[0][0]

        # chỉ giữ text có độ dài gần target
        texts = [t for t in texts if abs(len(t) - target_len) <= 1]

        result = ""
        for i in range(target_len):
            chars = []
            for t in texts:
                if i < len(t):
                    chars.append(t[i])
            if chars:
                result += Counter(chars).most_common(1)[0][0]

        return result

# Thêm logic ép buộc: 2 ký tự đầu là số, ký tự thứ 3 là chữ.
# Tìm hàm _correct_plate_format và sửa thành:
    def _correct_plate_format(self, text: str) -> str:
        text = text.upper()
        text = re.sub(r"[^A-Z0-9]", "", text) # Xóa hết dấu chấm, gạch

        if len(text) < 7 or len(text) > 10:
            return ""

        # MAPPING SỬA LỖI (Quan trọng)
        # 0 vs O, 1 vs I, 8 vs B, ...
        map_to_letter = {"0": "O", "1": "I", "5": "S", "8": "B", "6": "G", "2": "Z", "4": "A"}
        map_to_digit  = {"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7", "A": "4"}

        chars = list(text)

        # QUY LUẬT BIỂN VN: 2 ký tự đầu luôn là SỐ (59, 61...)
        for i in [0, 1]:
            if i < len(chars) and chars[i] in map_to_digit:
                chars[i] = map_to_digit[chars[i]]

        # Ký tự thứ 3 luôn là CHỮ (A, B, C...)
        if 2 < len(chars) and chars[2] in map_to_letter:
            chars[2] = map_to_letter[chars[2]]
        
        # Các ký tự sau thường là số (trừ xe máy điện), sửa sơ bộ
        for i in range(3, len(chars)):
             if chars[i] in map_to_digit:
                 chars[i] = map_to_digit[chars[i]]

        return "".join(chars)