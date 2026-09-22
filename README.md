# 🚗 Hệ thống Nhận dạng và Phân loại Biển số xe (ALPR)

Ứng dụng xử lý ảnh số trong nhận dạng và phân loại biển số xe tại Việt Nam, kết hợp mô hình học sâu **YOLOv8** để phát hiện biển số với các kỹ thuật xử lý ảnh cổ điển (HSV, Gaussian filter, Otsu, CLAHE) để tiền xử lý, và **EasyOCR** để nhận dạng ký tự. Hệ thống được demo trên mô hình phần cứng barrier tự động (ESP32-CAM + Arduino).

> Bài tiểu luận môn **Xử lý ảnh số** — Nhóm 19, HCMUTE
> 📄 **Báo cáo tiểu luận đầy đủ:** [Báo_cáo_tiểu_luận_XLA_G19.docx](https://docs.google.com/document/d/1t_qjr3eHH6rG60ZKfsXXshH9LL1TTMYn/edit?usp=sharing&ouid=115926746488026434084&rtpof=true&sd=true)

## 📌 Giới thiệu

Nhận dạng biển số xe tự động (Automatic License Plate Recognition – ALPR) là bài toán quan trọng trong thị giác máy tính, ứng dụng trong giám sát giao thông, thu phí tự động, quản lý bãi đỗ xe và an ninh đô thị. Tại Việt Nam, bài toán gặp nhiều thách thức do điều kiện ánh sáng, góc chụp và đặc thù biển số trong nước.

Đề tài xây dựng một hệ thống hoàn chỉnh gồm:
- **Phát hiện biển số** bằng YOLOv8
- **Tiền xử lý ảnh** (phân loại màu HSV, hiệu chỉnh hình học, chuẩn hóa màu, tăng cường tương phản CLAHE)
- **Nhận dạng ký tự** bằng EasyOCR
- **Đối chiếu cơ sở dữ liệu** để quyết định cấp phép ra/vào
- **Mô hình phần cứng demo** mô phỏng barrier tự động

## 🎯 Mục tiêu

Xây dựng hệ thống tự động phát hiện và nhận dạng nội dung biển số xe từ ảnh tĩnh với độ chính xác và độ ổn định cao, đồng thời đánh giá vai trò của từng bước xử lý (phát hiện → tiền xử lý → nhận dạng) đến kết quả cuối cùng.

**Phạm vi:** biển số xe máy và ô tô tại Việt Nam, điều kiện ánh sáng thuận lợi, góc chụp trực diện hoặc nghiêng nhẹ. Không đi sâu vào các điều kiện cực đoan (ban đêm, mưa lớn, chuyển động mạnh).

## 🧠 Kiến trúc & Pipeline xử lý

```
Camera / Ảnh đầu vào
        │
        ▼
  Phát hiện biển số (YOLOv8n)
        │  → cắt vùng ROI (padding 10–20px)
        ▼
  Tiền xử lý ảnh biển số
   ├─ Nhận dạng màu nền (không gian màu HSV)
   ├─ Hiệu chỉnh hình học (Gaussian filter → Otsu threshold → contour →
   │   perspective transform / deskew)
   ├─ Chuẩn hóa màu (chữ đen trên nền trắng)
   └─ Tăng cường ảnh (CLAHE)
        │
        ▼
  Nhận dạng ký tự (EasyOCR)
        │
        ▼
  Đối chiếu cơ sở dữ liệu (CSDL)
        │
        ▼
  Quyết định cấp phép → Gửi lệnh Arduino → Servo barrier + đèn LED
```

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python |
| Phát hiện đối tượng | YOLOv8n (Ultralytics) |
| Nhận dạng ký tự (OCR) | EasyOCR |
| Xử lý ảnh | OpenCV (HSV, Gaussian filter, Otsu thresholding, CLAHE, perspective transform) |
| Giao diện người dùng | GUI desktop (hiển thị camera, kết quả nhận dạng, lịch sử) |
| Cơ sở dữ liệu | Đối chiếu biển số đã đăng ký (whitelist/blacklist) |
| Phần cứng | ESP32-CAM (streaming MJPEG qua WiFi), Arduino Uno R3, Servo SG90, LED tín hiệu |
| Giao tiếp phần cứng | UART qua cổng COM ảo, baud rate 115200, lệnh 1 byte (`'1'` mở / `'0'` đóng) |

### Bộ dữ liệu huấn luyện
- Nguồn: Kaggle – *Vietnam License Plate Segment Datasets*
- Train: 3.433 ảnh · Validation: 1.145 ảnh
- 2 lớp: **BSD** (biển số nền đỏ) và **BSV** (biển số nền vàng)
- Cấu hình huấn luyện: `epochs=50, imgsz=640, batch=16, patience=30, optimizer=auto, AMP`

## 🔌 Phần cứng demo

Mô hình mô phỏng barrier tự động gồm 3 khối:
- **Thu nhận hình ảnh:** ESP32-CAM (streaming MJPEG qua HTTP)
- **Xử lý trung tâm:** máy tính chạy YOLOv8 + OCR, đưa ra quyết định
- **Điều khiển chấp hành:** Arduino Uno R3 điều khiển Servo SG90 (barrier) và LED xanh/đỏ báo trạng thái, có cơ chế an toàn giữ cổng mở 3 giây trước khi đóng lại

## 📊 Kết quả thực nghiệm

- **mAP@0.5:** 99,4%
- **mAP@0.5:0.95:** 91,3%
- **Thời gian suy luận trung bình:** ~2,1 ms/ảnh
- **Tốc độ xử lý:** 30–60 FPS trên GPU
- **Phản hồi phần cứng (mở barrier):** dưới ~200 ms

**Ưu điểm:** hoạt động ổn định khi biển số rõ nét, không bị che khuất; tiền xử lý cải thiện đáng kể chất lượng ảnh cho OCR.

**Hạn chế:** độ chính xác giảm với biển số nhỏ, nghiêng mạnh hoặc ánh sáng phức tạp; một số ký tự dễ nhầm lẫn hình dạng; chưa ổn định giữa các khung hình liên tiếp khi xử lý video.

**Hướng phát triển:** mở rộng tập dữ liệu, tối ưu OCR để giảm nhầm lẫn ký tự, bổ sung kỹ thuật xử lý ảnh trong điều kiện ánh sáng kém, thêm cơ chế ổn định theo chuỗi khung hình.

## 📁 Cấu trúc dự án (gợi ý)

```
.
├── data/                  # Bộ dữ liệu huấn luyện/kiểm thử YOLO
├── models/                # File trọng số best.pt / last.pt
├── src/
│   ├── detection/         # Phát hiện biển số (YOLOv8)
│   ├── preprocessing/     # HSV, hiệu chỉnh hình học, chuẩn hóa màu, CLAHE
│   ├── ocr/                # Nhận dạng ký tự (EasyOCR)
│   └── hardware/          # Giao tiếp Serial với Arduino
├── firmware/               # Code nạp cho Arduino Uno / ESP32-CAM
├── gui/                     # Giao diện người dùng
└── README.md
```

*(Cập nhật lại cấu trúc này cho khớp với mã nguồn thực tế trong repo.)*

## 👥 Nhóm thực hiện — Nhóm 19

| Thành viên | Nhiệm vụ |
|---|---|
| Lưu Thái Thanh Lâm | Thiết kế & lắp ráp phần cứng, chuẩn bị dữ liệu đầu vào, tổng hợp code, hỗ trợ tiền xử lý ảnh và OCR |
| Huỳnh Thị Yến Linh | Huấn luyện mô hình YOLOv8, tiền xử lý ảnh, nhận dạng ký tự OCR |
| Nguyễn Hương Giang | Xây dựng giao diện, chuẩn bị Database, so khớp biển số với Database, đánh giá kết quả |

## 📚 Tài liệu tham khảo

- Terven, J., Córdova-Esparza, D.-M., & Romero-González, J.-A. (2023). *A Comprehensive Review of YOLO Architectures in Computer Vision: From YOLOv1 to YOLOv8 and YOLO-NAS.* Machine Learning and Knowledge Extraction, 5(4), 1680–1716. https://doi.org/10.3390/make5040083
- *Optimized YOLOv8 for automatic license plate recognition on resource constrained devices.* Engineering, Technology & Applied Science Research.

## 📄 Giấy phép

Dự án phục vụ mục đích học thuật (bài tiểu luận cuối kỳ môn Xử lý ảnh số).
