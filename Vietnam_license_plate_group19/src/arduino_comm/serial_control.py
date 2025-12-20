import serial
import time

class BarrierController:
    def __init__(self, port='COM6', baud_rate=9600):
        self.port = port            # Lưu lại tên cổng
        self.baud_rate = baud_rate  # Lưu lại tốc độ
        self.arduino = None
        self.is_connected = False
        
        # Gọi hàm kết nối ngay khi khởi tạo
        self.connect_arduino()

        self.is_open = False
        self.last_open_time = 0
        self.safety_delay = 3.0
        self.last_vehicle_time = 0

    def connect_arduino(self):
        """Hàm riêng để thực hiện kết nối"""
        if self.is_connected:
            return # Đã kết nối rồi thì thôi

        try:
            self.arduino = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2) # Đợi Arduino khởi động lại
            print(f"✅ [PHẦN CỨNG] Đã kết nối lại tại {self.port}")
            self.is_connected = True
        except Exception as e:
            print(f"⚠️ [PHẦN CỨNG] Lỗi kết nối: {e}")
            self.is_connected = False

    def send_cmd(self, cmd):
        if self.is_connected and self.arduino:
            try: 
                self.arduino.write(cmd)
            except Exception:
                print("⚠️ Mất kết nối Arduino!")
                self.is_connected = False

    def process_logic(self, is_allowed: bool):
        # Nếu chưa kết nối thì không làm gì cả
        if not self.is_connected: return

        now = time.time()
        
        if is_allowed:
            self.last_vehicle_time = now
            if (not self.is_open) or (now - self.last_open_time > 1.0):
                self.send_cmd(b'1')
                self.is_open = True
                self.last_open_time = now
                print(">>> 🟢 MỞ CỔNG")
        else:
            if self.is_open and (now - self.last_vehicle_time > self.safety_delay):
                self.send_cmd(b'0')
                self.is_open = False
                print(">>> 🔴 ĐÓNG CỔNG")

    def close_connection(self):
        if self.is_open: 
            self.send_cmd(b'0') # Đóng cổng trước khi ngắt
        
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
            print("🛑 [PHẦN CỨNG] Đã ngắt kết nối Arduino")
        
        self.is_connected = False