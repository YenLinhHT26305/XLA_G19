# src/database/db.py
import pyodbc

# =========================
# Database configuration
# =========================
DB_DRIVER = "{ODBC Driver 17 for SQL Server}"
DB_SERVER = "LAPTOP-PSVNV44T\\MSSQLSERVER1"   # hoặc: LAPTOP-PSVNV44T,1433
DB_NAME   = "ANPR_DB"
DB_USER   = "sa"
DB_PASS   = "linhhtyl0"

# =========================
# Create connection
# =========================
def get_connection():
    """
    Tạo và trả về kết nối tới SQL Server
    """
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


# =========================
# Database operations
# =========================
def save_plate(plate, confidence, image_path=None):
    """
    Lưu kết quả OCR biển số vào database
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO LicensePlateLog (plate, confidence, image_path)
            VALUES (?, ?, ?)
            """,
            (plate, confidence, image_path)
        )
        conn.commit()

    except pyodbc.Error as e:
        print("❌ Database error:", e)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def fetch_all_logs():
    """
    Lấy toàn bộ lịch sử nhận dạng
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM LicensePlateLog ORDER BY time_detected DESC")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return rows


# =========================
# Test connection
# =========================
if __name__ == "__main__":
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT GETDATE()")
        print("✅ Connected to SQL Server!")
        print("Server time:", cursor.fetchone()[0])

        cursor.close()
        conn.close()

    except pyodbc.Error as e:
        print("❌ Connection failed:", e)
