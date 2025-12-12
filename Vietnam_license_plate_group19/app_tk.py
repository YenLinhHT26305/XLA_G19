# app_tk.py
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np

from backend import PlateBackend


class PlateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nhận dạng biển số xe (YOLO + EasyOCR)")
        self.root.geometry("1100x600")  # kích thước cửa sổ ban đầu

        # Khởi tạo backend (YOLO + EasyOCR)
        # Nếu EasyOCR lỗi CUDA, đổi use_gpu=False
        self.backend = PlateBackend(use_gpu=True)

        # Lưu ảnh đang hiển thị
        self.current_img_bgr = None
        self.tk_img_original = None
        self.tk_img_result = None

        # Tạo giao diện
        self.create_widgets()

    def create_widgets(self):
        # ===== Thanh trên cùng: các nút =====
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

        btn_load = tk.Button(
            top_frame,
            text="Chọn ảnh",
            command=self.load_image,
            width=15,
            font=("Arial", 11),
        )
        btn_load.pack(side=tk.LEFT, padx=5)

        btn_process = tk.Button(
            top_frame,
            text="Nhận dạng biển số",
            command=self.run_recognition,
            width=18,
            font=("Arial", 11),
        )
        btn_process.pack(side=tk.LEFT, padx=5)

        # ===== Khung dưới: ảnh gốc & ảnh kết quả =====
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Khung trái: ảnh gốc
        left_frame = tk.LabelFrame(bottom_frame, text="Ảnh gốc")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.label_original = tk.Label(left_frame, bg="gray")
        self.label_original.pack(fill=tk.BOTH, expand=True)

        # Khung phải: ảnh kết quả
        right_frame = tk.LabelFrame(bottom_frame, text="Ảnh kết quả (YOLO + biển số)")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.label_result = tk.Label(right_frame, bg="gray")
        self.label_result.pack(fill=tk.BOTH, expand=True)

        # ===== Dòng dưới: text biển số =====
        self.result_text_var = tk.StringVar()
        self.result_text_var.set("Biển số: (chưa có)")

        label_plate = tk.Label(
            self.root,
            textvariable=self.result_text_var,
            font=("Arial", 14),
            fg="blue",
        )
        label_plate.pack(side=tk.BOTTOM, pady=10)

    # ---------- NÚT "Chọn ảnh" ----------
    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="Chọn ảnh",
            filetypes=[
                ("Image files", "*.jpg;*.jpeg;*.png"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        img_bgr = cv2.imread(file_path)
        if img_bgr is None:
            messagebox.showerror("Lỗi", "Không đọc được ảnh. Hãy chọn file khác.")
            return

        self.current_img_bgr = img_bgr
        self.show_image(img_bgr, which="original")

        # Reset kết quả cũ
        self.result_text_var.set("Biển số: (chưa nhận dạng)")
        self.label_result.config(image="")
        self.tk_img_result = None

    # ---------- Hàm hiển thị ảnh lên Label ----------
    def show_image(self, img_bgr, which="original"):
        """
        img_bgr: ảnh BGR (cv2)
        which: "original" hoặc "result"
        """
        # Giới hạn kích thước để không quá to
        max_w, max_h = 500, 400
        h, w = img_bgr.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)
        img_resized = cv2.resize(img_bgr, (new_w, new_h))

        # BGR -> RGB -> PIL -> ImageTk
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        tk_img = ImageTk.PhotoImage(pil_img)

        if which == "original":
            self.tk_img_original = tk_img  # giữ reference tránh bị GC
            self.label_original.config(image=self.tk_img_original)
        else:
            self.tk_img_result = tk_img
            self.label_result.config(image=self.tk_img_result)

    # ---------- NÚT "Nhận dạng biển số" ----------
    def run_recognition(self):
        if self.current_img_bgr is None:
            messagebox.showwarning("Thông báo", "Bạn chưa chọn ảnh.")
            return

        # Hiển thị con trỏ chờ để báo đang xử lý
        self.root.config(cursor="watch")
        self.root.update()

        try:
            result = self.backend.process_image(self.current_img_bgr)
        except Exception as e:
            self.root.config(cursor="")
            messagebox.showerror("Lỗi", f"Lỗi khi xử lý ảnh:\n{e}")
            return

        # Hiển thị ảnh kết quả
        annotated_bgr = result["annotated"]
        self.show_image(annotated_bgr, which="result")

        # Cập nhật text biển số
        plate_text = result["plate_text"]
        if plate_text:
            self.result_text_var.set(f"Biển số: {plate_text}")
        else:
            self.result_text_var.set("Biển số: Không đọc được biển số hợp lệ.")

        # Trả lại con trỏ chuột bình thường
        self.root.config(cursor="")


if __name__ == "__main__":
    root = tk.Tk()
    app = PlateApp(root)
    root.mainloop()