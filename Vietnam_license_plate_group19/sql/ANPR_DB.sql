USE master;
GO

-- 1. XÓA DB CŨ ĐỂ LÀM SẠCH (Reset toàn bộ)
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'ANPR_DB')
BEGIN
    ALTER DATABASE ANPR_DB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE ANPR_DB;
END
GO

-- 2. TẠO DB MỚI
CREATE DATABASE ANPR_DB;
GO

USE ANPR_DB;
GO

-- ====================================================
-- BẢNG 1: RegisteredVehicles (DANH SÁCH XE ĐƯỢC PHÉP - WHITELIST)
-- Tác dụng: Chứa thông tin xe đã đăng ký vé tháng/cư dân.
-- ====================================================
CREATE TABLE RegisteredVehicles (
    plate NVARCHAR(20) PRIMARY KEY, -- Biển số (Viết liền, không dấu)
    owner_name NVARCHAR(100),       -- Tên chủ xe
    vehicle_type NVARCHAR(50),      -- Loại xe (Ô tô/Xe máy)
    allowed BIT DEFAULT 1,          -- 1: Cho phép mở cổng, 0: Cấm (Blacklist)
    created_at DATETIME DEFAULT GETDATE()
);

-- ====================================================
-- BẢNG 2: LicensePlateLog (NHẬT KÝ RA VÀO)
-- Tác dụng: Lưu lại lịch sử, bằng chứng, thời gian xe qua cổng.
-- ====================================================
CREATE TABLE LicensePlateLog (
    id INT IDENTITY(1,1) PRIMARY KEY,
    plate NVARCHAR(20) NOT NULL,
    confidence FLOAT,            -- Độ tin cậy của AI (0.0 - 1.0)
    decision NVARCHAR(50),       -- Quyết định: ALLOW / DENY / MANUAL
    image_path NVARCHAR(MAX),    -- Đường dẫn file ảnh đã lưu trên máy tính
    time_detected DATETIME DEFAULT GETDATE()
);

-- Tạo Index để tìm kiếm nhanh hơn khi dữ liệu lớn
CREATE INDEX IDX_Log_Plate ON LicensePlateLog(plate);
CREATE INDEX IDX_Log_Time ON LicensePlateLog(time_detected);

GO

-- ====================================================
-- NHẬP DỮ LIỆU MẪU (DANH SÁCH BẠN YÊU CẦU)
-- Lưu ý: Dữ liệu đã được xóa dấu '-' và '.'
-- ====================================================

INSERT INTO RegisteredVehicles (plate, owner_name, vehicle_type, allowed)
VALUES
-- Xe máy
('90B245230', N'Chủ xe 61T3',  N'Xe máy', 1),
('59V179379', N'Chủ xe 59V1',  N'Xe máy', 1),
('49E164481',  N'Chủ xe 60A5',  N'Xe máy', 1),
('86B137449', N'Chủ xe 49E1',  N'Xe máy', 1),
('47K117349',   N'Chủ xe Điện',  N'Xe máy điện', 1),
('66P189575', N'Chủ xe 86B1',  N'Xe máy', 1),
('63B999999', N'Chủ xe 84B1',  N'Xe máy', 1),
('29B199999', N'Chủ xe 29B1',  N'Xe máy', 1),

-- Ô tô
('61A60573',  N'Công Ty LTTL',    N'Ô tô', 1),
('95A01379',  N'Nguyễn Văn B', N'Ô tô', 1),
('60A55655',  N'Lê Văn D',     N'Ô tô', 1),
('51H04073',  N'Phạm Văn E',   N'Ô tô', 1),
('51G68882',  N'Xe VIP F',     N'Ô tô', 1),
('50F70874',  N'Võ Văn G',     N'Ô tô', 1),
('30E92115',  N'Đặng Văn H',   N'Ô tô', 1),
('51A13883',  N'Huỳnh Yến L',   N'Ô tô', 1),
('51H59565',  N'Nguyễn Hương G',   N'Ô tô', 1),
('20A09999',  N'Đặng Văn H',   N'Ô tô', 1);

-- Xe Test Blacklist (Cấm)
INSERT INTO RegisteredVehicles (plate, owner_name, vehicle_type, allowed)
VALUES ('51F88686', N'Xe Vi Phạm', N'Ô tô', 0),
		('84B136217', N'Xe Vi Phạm',  N'Xe máy', 1);

GO

-- ====================================================
-- TRUY VẤN KIỂM TRA
-- ====================================================
PRINT N'Đã khởi tạo Database thành công!';
SELECT * FROM RegisteredVehicles;