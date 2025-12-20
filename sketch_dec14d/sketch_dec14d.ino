#include <Servo.h> 

Servo barrier; 
const int pinServo = 9;
const int pinXanh = 8;
const int pinDo = 7;

void setup() {
  Serial.begin(9600); 
  barrier.attach(pinServo);
  pinMode(pinXanh, OUTPUT);
  pinMode(pinDo, OUTPUT);
  
  // Khởi động thì đóng cổng
  dongCong();
}

void loop() {
  if (Serial.available() > 0) {
    char lenh = Serial.read();
    
    // Nhận số '1' -> Mở ngay
    if (lenh == '1') moCong();
    
    // Nhận số '0' -> Đóng ngay
    if (lenh == '0') dongCong();
  }
}

void moCong() {
  digitalWrite(pinDo, LOW);    // Tắt đỏ
  digitalWrite(pinXanh, HIGH); // Bật xanh
  barrier.write(90);           // Quay lên 90 độ
}

void dongCong() {
  barrier.write(0);            // Quay về 0 độ
  digitalWrite(pinXanh, LOW);  // Tắt xanh
  digitalWrite(pinDo, HIGH);   // Bật đỏ
}