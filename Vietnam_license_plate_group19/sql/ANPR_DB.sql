IF NOT EXISTS (
    SELECT name FROM sys.databases WHERE name = 'ANPR_DB'
)
BEGIN
    CREATE DATABASE ANPR_DB;
END
GO

USE ANPR_DB;
GO

-- ==============================
-- Table: License plate detection log
-- ==============================
CREATE TABLE LicensePlateLog (
    id INT IDENTITY(1,1) PRIMARY KEY,
    plate NVARCHAR(20) NOT NULL,
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),
    image_path NVARCHAR(255),
    time_detected DATETIME DEFAULT GETDATE()
);

-- ==============================
-- Optional: Registered vehicles
-- ==============================
CREATE TABLE RegisteredVehicles (
    plate NVARCHAR(20) PRIMARY KEY,
    owner_name NVARCHAR(100),
    vehicle_type NVARCHAR(50),
    allowed BIT DEFAULT 1
);


USE ANPR_DB;
GO

-- ==============================
-- Sample registered vehicles
-- ==============================
INSERT INTO RegisteredVehicles (plate, owner_name, vehicle_type, allowed)
VALUES
('48A-028.66', N'Nguyễn Văn A', N'Xe máy', 1),
('51G-517.17', N'Trần Thị B', N'Ô tô', 1),
('59X-123.45', N'Lê Văn C', N'Xe máy', 0);

-- ==============================
-- Sample OCR logs
-- ==============================
INSERT INTO LicensePlateLog (plate, confidence, image_path)
VALUES
('48A-028.66', 0.92, 'results/plate_001.jpg'),
('51G-517.17', 0.88, 'results/plate_002.jpg');



USE ANPR_DB;
GO

-- 1. Xem toàn bộ log OCR
SELECT * FROM LicensePlateLog
ORDER BY time_detected DESC;

-- 2. Kiểm tra xe có được phép ra vào không
SELECT 
    l.plate,
    l.time_detected,
    r.owner_name,
    r.allowed
FROM LicensePlateLog l
LEFT JOIN RegisteredVehicles r
    ON l.plate = r.plate;

-- 3. Xe không được phép
SELECT *
FROM RegisteredVehicles
WHERE allowed = 0;

-- 4. Thống kê số lần xuất hiện theo biển số
SELECT plate, COUNT(*) AS detect_count
FROM LicensePlateLog
GROUP BY plate;

