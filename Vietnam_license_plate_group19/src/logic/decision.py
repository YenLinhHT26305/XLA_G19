from database.db import get_connection

def auto_decision_from_db(plate: str, plate_color: str) -> bool:
    if not plate: return False
    
    # 1. Ưu tiên màu: Bằng cách chuyển về chữ thường để so sánh
    color = (plate_color or "").lower().strip()
    
    # Nếu là biển số xanh hoặc đỏ, trả về True
    if color in ("blue", "red"):
        return True

    # 2. Kiểm tra Database đối với các xe còn lại
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT allowed FROM RegisteredVehicles WHERE plate = ?", plate)
        row = cursor.fetchone()
        if row and row[0] == True:
            return True
    except:
        pass
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return False