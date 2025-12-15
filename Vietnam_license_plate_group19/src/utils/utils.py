import cv2
import numpy as np
import matplotlib.pyplot as plt

# HIỂN THỊ ẢNH
def show_bgr(ax, img, title=""):
    """
    Hiển thị ảnh màu (BGR → RGB) bằng matplotlib
    """
    ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    ax.set_title(title)
    ax.axis("off")

def show_gray(ax, img, title=""):
    """
    Hiển thị ảnh xám
    """
    ax.imshow(img, cmap="gray")
    ax.set_title(title)
    ax.axis("off")

def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Sắp xếp 4 điểm của hình chữ nhật theo thứ tự:
    top-left, top-right, bottom-right, bottom-left
    (phục vụ cho phép biến đổi phối cảnh)
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # góc trên-trái
    rect[2] = pts[np.argmax(s)]   # góc dưới-phải
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # góc trên-phải
    rect[3] = pts[np.argmax(diff)]  # góc dưới-trái
    return rect

# ==================================
# BƯỚC C: NHẬN DIỆN MÀU BIỂN SỐ
# ==================================
def detect_plate_color(img):
    """
    Nhận diện màu nền biển số (trắng / xanh / vàng / đỏ)
    Trả về: (color_name, debug_mask)
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ---- Định nghĩa dải màu HSV ----
    ranges = {
        "white": (
            np.array([0, 0, 180]),
            np.array([180, 60, 255])
        ),
        "blue": (
            np.array([90, 80, 80]),
            np.array([130, 255, 255])
        ),
        "yellow": (
            np.array([15, 80, 80]),
            np.array([35, 255, 255])
        ),
        "red": (
            np.array([0, 80, 80]),
            np.array([10, 255, 255])
        )
    }

    pixel_count = {}
    masks = {}

    for color, (lower, upper) in ranges.items():
        mask = cv2.inRange(hsv, lower, upper)
        masks[color] = mask
        pixel_count[color] = cv2.countNonZero(mask)

    # Màu có nhiều pixel nhất
    detected_color = max(pixel_count, key=pixel_count.get)

    return detected_color, masks

# ==========================================
# BƯỚC A: HIỆU CHỈNH HÌNH HỌC BIỂN SỐ (TỰ ĐỘNG)
# ==========================================
def rectify_plate_auto(img, warp_ratio_thresh=0.15, angle_limit=15):
    """
    Tự động quyết định:
    - Biến đổi phối cảnh (perspective) nếu biển số bị méo hình thang
    - Xoay nhẹ (deskew) nếu biển số chỉ nghiêng góc nhỏ

    Trả về:
      fixed_img: ảnh sau khi hiệu chỉnh
      debug: dictionary chứa ảnh trung gian để quan sát
    """
    debug = {}

    # Chuyển ảnh sang ảnh xám
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Làm mờ Gaussian để giảm nhiễu
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Nhị phân hóa bằng phương pháp Otsu
    _, thresh = cv2.threshold(
        blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    debug["gray"] = gray
    debug["blur"] = blur
    debug["thresh_otsu"] = thresh

    # Tìm contour (đường bao) trong ảnh nhị phân
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        print("[INFO] Không tìm thấy contour → bỏ qua hiệu chỉnh hình học")
        debug["decision"] = "none"
        return img, debug

    # Chọn contour có diện tích lớn nhất (giả định là biển số)
    cnt = max(contours, key=cv2.contourArea)

    # Tìm hình chữ nhật xoay nhỏ nhất bao quanh biển số
    rect = cv2.minAreaRect(cnt)               # ((cx,cy),(w,h),angle)
    box = cv2.boxPoints(rect)
    box = np.float32(box)
    src = order_points(box)

    # Tính độ dài các cạnh
    w_top = np.linalg.norm(src[0] - src[1])
    w_bot = np.linalg.norm(src[3] - src[2])
    h_left = np.linalg.norm(src[0] - src[3])
    h_right = np.linalg.norm(src[1] - src[2])

    # Tính độ méo phối cảnh (chênh lệch cạnh trên/dưới)
    warp_ratio = abs(w_top - w_bot) / max(w_top, w_bot)

    # Góc nghiêng từ minAreaRect
    raw_angle = rect[-1]
    angle = raw_angle
    if angle < -45:
        angle += 90

    # Vẽ khung biển số để quan sát
    overlay = img.copy()
    cv2.drawContours(overlay, [np.int32(src)], -1, (0, 255, 0), 2)
    debug["box_overlay"] = overlay

    # In thông tin hình học
    print("========== THÔNG TIN HÌNH HỌC BIỂN SỐ ==========")
    print(f"Chiều rộng cạnh trên : {w_top:.2f}")
    print(f"Chiều rộng cạnh dưới : {w_bot:.2f}")
    print(f"Tỉ lệ méo phối cảnh  : {warp_ratio:.3f}")
    print(f"Góc nghiêng gốc      : {raw_angle:.2f} độ")
    print(f"Góc sau hiệu chỉnh   : {angle:.2f} độ")

    # Quyết định phương pháp hiệu chỉnh
    if warp_ratio > warp_ratio_thresh:
        print("[QUYẾT ĐỊNH] Biến đổi phối cảnh (Perspective)")
        debug["decision"] = "perspective"

        width = int(max(w_top, w_bot))
        height = int(max(h_left, h_right))

        dst = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(img, M, (width, height))
        debug["fixed"] = warped
        return warped, debug

    else:
        # Chỉ xoay nếu góc nhỏ (tránh lỗi xoay 90 độ)
        if abs(angle) > angle_limit:
            print("[CẢNH BÁO] Góc quá lớn → không xoay")
            angle = 0.0
        else:
            print("[QUYẾT ĐỊNH] Xoay hiệu chỉnh (Deskew)")

        debug["decision"] = "deskew"
        debug["final_angle_used"] = angle

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        debug["fixed"] = rotated
        return rotated, debug


# ==================================
# BƯỚC B: TĂNG CƯỜNG ẢNH CHO OCR
# ==================================
def enhance_blurry_plate(img):
    """
    Tiền xử lý ảnh để cải thiện độ chính xác OCR
    (đặc biệt với ảnh mờ, ánh sáng không đều)
    """
    debug = {}

    # Chuyển sang ảnh xám
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    debug["ocr_gray"] = gray

    # Phóng to ảnh (giúp OCR đọc tốt hơn)
    up = cv2.resize(
        gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
    )
    debug["ocr_upscaled"] = up

    # Tăng tương phản cục bộ bằng CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(up)
    debug["ocr_clahe"] = cl

    # Nhị phân hóa thích nghi
    th = cv2.adaptiveThreshold(
        cl, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 15
    )
    debug["ocr_adapt_th"] = th

    # Morphology Close để nối nét ký tự
    kernel = np.ones((2, 2), np.uint8)
    closed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
    debug["ocr_morph_close"] = closed

    return closed, debug


# =========================
# CHƯƠNG TRÌNH CHÍNH
# =========================
'''
if __name__ == "__main__":
    IMG_PATH = "data/images/test.png"  # Đường dẫn ảnh test

    img = cv2.imread(IMG_PATH)
    if img is None:
        raise ValueError(f"Không đọc được ảnh: {IMG_PATH}")

    # Bước A: Hiệu chỉnh hình học
    fixed, geo_dbg = rectify_plate_auto(img)

    # Bước B: Tăng cường ảnh cho OCR
    ocr_ready, ocr_dbg = enhance_blurry_plate(fixed)

    # ===== HIỂN THỊ CÁC BƯỚC HÌNH HỌC =====
    fig1, ax1 = plt.subplots(2, 3, figsize=(15, 8))
    ax1 = ax1.ravel()

    show_bgr(ax1[0], img, "0) Ảnh gốc")
    show_gray(ax1[1], geo_dbg["gray"], "1) Ảnh xám")
    show_gray(ax1[2], geo_dbg["blur"], "2) Làm mờ Gaussian")
    show_gray(ax1[3], geo_dbg["thresh_otsu"], "3) Nhị phân Otsu")
    show_bgr(ax1[4], geo_dbg["box_overlay"], "4) Khung biển số phát hiện")
    show_bgr(ax1[5], fixed, f"5) Ảnh sau hiệu chỉnh ({geo_dbg['decision']})")

    plt.tight_layout()
    plt.show()

    # ===== HIỂN THỊ CÁC BƯỚC TĂNG CƯỜNG OCR =====
    fig2, ax2 = plt.subplots(1, 5, figsize=(18, 4))
    show_gray(ax2[0], ocr_dbg["ocr_gray"], "A) Ảnh xám")
    show_gray(ax2[1], ocr_dbg["ocr_upscaled"], "B) Phóng to x2")
    show_gray(ax2[2], ocr_dbg["ocr_clahe"], "C) CLAHE")
    show_gray(ax2[3], ocr_dbg["ocr_adapt_th"], "D) Nhị phân thích nghi")
    show_gray(ax2[4], ocr_dbg["ocr_morph_close"], "E) Morph Close (ảnh OCR)")

    plt.tight_layout()
    plt.show()
'''