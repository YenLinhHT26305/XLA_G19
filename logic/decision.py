from database.db import get_connection


def is_registered_and_allowed(plate: str) -> bool:
    """
    Kiểm tra biển số có trong bảng RegisteredVehicles
    và được phép (allowed = 1) hay không
    """
    if not plate:
        return False

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT allowed
            FROM RegisteredVehicles
            WHERE plate = ?
            """,
            plate
        )

        row = cursor.fetchone()
        if row is None:
            return False

        return bool(row[0])  # allowed = 1 → True

    except Exception as e:
        print("❌ DB error (RegisteredVehicles):", e)
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def auto_decision_from_db(
    plate: str,
    plate_color: str
) -> bool:
    """
    RULE:
    - ALLOW nếu:
        1. Biển số có trong RegisteredVehicles và allowed = 1
        HOẶC
        2. Màu biển là xanh hoặc đỏ
    """

    if not plate:
        return False

    # Chuẩn hóa màu
    color = (plate_color or "").lower().strip()

    # Rule 1: Biển đăng ký
    if is_registered_and_allowed(plate):
        return True

    # Rule 2: Biển ưu tiên
    if color in ("blue", "red"):
        return True

    return False


'''def auto_decision_from_db(plate: str) -> bool:
    """
    Demo logic:
    - plate bắt đầu bằng '5' → cho vào
    """
    if not plate:
        return False
    return plate.startswith("5")'''
