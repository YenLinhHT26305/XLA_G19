import cv2
import matplotlib.pyplot as plt
from detect.yolov8_detect import YoloPlateDetector
from ocr.plate_easyocr import PlateOCR
from preprocess.plate_preprocessor import PlatePreprocessor 

# Init
detector = YoloPlateDetector(
    model_path="models/yolov8/best.pt",
    device=0,
    conf_thres=0.7
)

ocr_engine = PlateOCR(gpu=True)


def run_pipeline_debug(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Không đọc được ảnh")
    
    # ========== 1. YOLO detect ==========
    plate_rectified, (x1, y1, x2, y2), best_conf = detector.detect_and_crop(img)
    
    # ========== 2. Tiền xử lý OCR ==========
    preprocessor = PlatePreprocessor()

    plate_color, _ = preprocessor.detect_plate_color(plate_rectified)

    fixed, _ = preprocessor.rectify_plate(plate_rectified)

    # OCR variant 1: grayscale + CLAHE (đã có)
    img1, _ = preprocessor.enhance_for_ocr(fixed)

    # OCR variant 2: normalize màu (rất quan trọng cho biển xanh)
    img2 = preprocessor.normalize_plate_color(fixed, plate_color)

    # OCR variant 3: blur nhẹ để giảm nhiễu halo
    img3 = cv2.GaussianBlur(img1, (3, 3), 0)

    # ========== 3. OCR ==========
    texts = []

    for idx, img_ocr in enumerate([img1, img2, img3]):
        plate_tmp, _, raw_tmp = ocr_engine.recognize(img_ocr)
        if raw_tmp:
            texts.append(raw_tmp)
    print(texts)
    voted_text = ocr_engine.ocr_vote(texts)
    plate_text, plate_type = ocr_engine._match_plate(voted_text)


    # ========== 4. Vẽ kết quả ==========
    annotated = img.copy()
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
    if plate_text:
        cv2.putText(
            annotated, plate_text, (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3
        )

    def format_plate_display(plate_text, plate_type):
        if not plate_text:
            return ""

        # Ô tô – 1 dòng – 8 ký tự
        if plate_type == "car" and len(plate_text) == 8:
            # VD: 51F67890 -> 51F-678.90
            return f"{plate_text[:3]}-{plate_text[3:6]}.{plate_text[6:]}"

        # Xe máy – 2 dòng – 9 ký tự
        if plate_type == "bike" and len(plate_text) == 9:
            # VD: 59X312345
            line1 = f"{plate_text[:2]}-{plate_text[2:4]}"
            line2 = f"{plate_text[4:7]}.{plate_text[7:]}"
            return line1 + "\n" + line2

        # Fallback
        return plate_text

    # ========== 5. Hiển thị từng bước ==========
    plt.figure(figsize=(15, 10))

    # ========== HÀNG 1 ==========
    plt.subplot(2, 2, 1)
    plt.title("Ảnh gốc")
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.axis("off")

    plt.subplot(2, 2, 2)
    plt.title("Crop biển số")
    plt.imshow(cv2.cvtColor( plate_rectified, cv2.COLOR_BGR2RGB))
    plt.axis("off")

    # ========== HÀNG 2 – OCR RESULT ==========
    plt.subplot(2, 2, (3, 4))
    plt.axis("off")

    if plate_text:
        final_text = plate_text
        final_color = "green"
        plate_type_text = plate_type.upper()
    else:
        final_text = "KHÔNG NHẬN DẠNG ĐƯỢC"
        final_color = "red"
        plate_type_text = "---"

    # Tiêu đề
    plt.text(
        0.5, 0.85,
        "KẾT QUẢ NHẬN DẠNG BIỂN SỐ",
        ha="center",
        va="center",
        fontsize=20,
        weight="bold"
    )

    # Raw OCR
    plt.text(
        0.5, 0.65,
        f"OCR raw : {voted_text}",
        ha="center",
        va="center",
        fontsize=14
    )

    # Màu biển
    plt.text(
        0.5, 0.55,
        f"Màu biển : {plate_color}",
        ha="center",
        va="center",
        fontsize=14
    )

    # Loại xe
    plt.text(
        0.5, 0.45,
        f"Loại xe : {plate_type_text}",
        ha="center",
        va="center",
        fontsize=14
    )

    display_text = format_plate_display(plate_text, plate_type)

    plt.text(
        0.5, 0.25,
        display_text,
        ha="center",
        va="center",
        fontsize=24,
        weight="bold",
        color="green"
    )

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_pipeline_debug(
        r"E:\HCMUTE\Nam3_dot2\Xulianhso\Project\Vietnam_license_plate_group19\data\images\Dieu_0013.png"
    )
    
#Dieu_0015