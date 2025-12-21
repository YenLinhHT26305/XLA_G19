# src/database/db.py
import pyodbc

# Cấu hình CSDL
DB_DRIVER = "{ODBC Driver 17 for SQL Server}"
DB_SERVER = r"DESKTOP-8HLP964\SQLEXPRESS" 
DB_NAME   = "ANPR_DB"
DB_USER   = "sa"
DB_PASS   = "123456"

# Tạo kết nối với CSDL
def get_connection():
    conn_str = (
        f"DRIVER={DB_DRIVER};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASS};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)



# Các thao tác với CSDL
def save_plate(plate, confidence, decision, image_path=None):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Câu lệnh này phải khớp 100% với bảng LicensePlateLog trong SQL
        sql = """
            INSERT INTO LicensePlateLog (plate, confidence, decision, image_path, time_detected)
            VALUES (?, ?, ?, ?, GETDATE())
        """
        cursor.execute(sql, (plate, confidence, decision, image_path))
        conn.commit()
        # print(f"Đã lưu DB: {plate} - {decision}")

    except Exception as e:
        print("Lỗi Database:", e)

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def fetch_all_logs():
    # Lấy 50 dòng mới nhất để tránh lag và đưa lên lịch sử trên giao diện
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 50 id, plate, confidence, decision, image_path, time_detected
        FROM LicensePlateLog
        ORDER BY time_detected DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

# Hàm kiểm tra kết nối CSDL
if __name__ == "__main__":
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT GETDATE()")
        print("Connected to SQL Server!")
        print("Server time:", cursor.fetchone()[0])

        cursor.close()
        conn.close()

    except pyodbc.Error as e:
        print("Connection failed:", e)