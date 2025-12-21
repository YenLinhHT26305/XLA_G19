import re
import easyocr

class PlateOCR:
    def __init__(self, gpu=True):
        # Khởi tạo EasyOCR
        self.reader = easyocr.Reader(['en'], gpu=gpu)

    def _match_plate(self, text):
        # Thực hiện bước phân loại dựa trên độ dài và kí tự
        # Biển đỏ có 6 hoặc 7 ký tự
        # Biển dân sự có 8 tới 9 kí tự
        # Độ dài kí tự <=7 nên sẽ là xe quân đội (biển đỏ)
        if len(text) <= 7 and text[:2].isalpha():
            return text, "military" 
        
        # Độ dài kí tự >=8 nên sẽ là xe dân sự (ô tô và xe máy)
        if len(text) >= 8:
            return text, "car" 

        return text, "unknown"

    # Hàm nhận diện màu sắc
    def _correct_plate_format(self, text: str, plate_color: str) -> str:
        # 1. Làm sạch
        text = text.upper()
        text = re.sub(r"[^A-Z0-9]", "", text)

        # 2. Kiểm tra độ dài (Mở rộng cho biển đỏ 6 ký tự)
        if len(text) < 6 or len(text) > 10:
            return ""
        chars = list(text)

        # 3. Định nghĩa bảng Mapping
        map_to_letter = { "0": "O", "1": "I", "5": "S", "8": "B", "6": "G", "2": "Z", "4": "A", "7": "T" }
        map_to_digit  = { "O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7", "A": "4" }

        # 4. Phân loại biển đỏ (quân sự) hay biển trắng (dân sự)
        is_military = False
        # Ưu tiên 1: Dựa vào màu sắc
        # Nếu Preprocessor.py bảo là màu Đỏ => Chắc chắn là quân sự
        if plate_color == "red":
            is_military = True
            
        # Ưu tiên 2: Dựa vào kí tự (Đề phòng)
        elif len(chars) > 0:
            first_char = chars[0]
            # Nếu ký tự đầu là CHỮ CÁI (K, P, T...) => Vẫn coi là quân sự
            if first_char.isalpha() and first_char not in ['O', 'I', 'Z', 'S', 'G', 'B']:
                is_military = True

        # 5. Áp dụng các sửa đổi như:
        if is_military:
            # Qui luật biển đỏ: Chữ - chữ - số
            # Tại vị trí 0 và 1: Ta ép thành chữ
            for i in [0, 1]:
                if i < len(chars) and chars[i] in map_to_letter:
                    chars[i] = map_to_letter[chars[i]]
            
            # Các vị trí còn lại: Ta ép thành số
            for i in range(2, len(chars)):
                if chars[i] in map_to_digit:
                    chars[i] = map_to_digit[chars[i]]

        else:
            # Qui luật biển trắng: Số - số - biển - Còn lại là số
            # Tại vị trí 0 và 1: Ta ép thành số
            for i in [0, 1]:
                if i < len(chars) and chars[i] in map_to_digit:
                    chars[i] = map_to_digit[chars[i]]

            # Tại vị trí 2: Ta ép thành chữ (Lưu ý: Xe máy điện **MĐ* thì vị trí 3 mới là chữ)
            # Nhưng mà ta ưu tiên áp dụng với xe máy phổ thông
            if len(chars) > 2 and chars[2] in map_to_letter:
                chars[2] = map_to_letter[chars[2]]
            # Vị trí còn lại: Ép thành SỐ
            for i in range(3, len(chars)):
                if chars[i] in map_to_digit:
                    chars[i] = map_to_digit[chars[i]]

        return "".join(chars)

    # Hàm nhận diện chính
    def recognize(self, plate_img, plate_color="white"):
        
        # 1. Đọc text + bounding box
        results = self.reader.readtext(
            plate_img,
            detail=1,
            paragraph=False,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
        if not results:
            return "", "", ""
        # 2. Sắp xếp kết quả theo dòng
        results = sorted(results, key=lambda r: r[0][0][1])
        # 3. Nối các đoạn text lại
        raw_text = "".join([r[1] for r in results])
        # 4. Sửa lỗi chính tả & Định dạng 
        corrected = self._correct_plate_format(raw_text, plate_color)
        # 5. Phân loại xe (thô)
        plate, plate_type = self._match_plate(corrected)
        return plate, plate_type, raw_text