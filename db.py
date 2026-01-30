import pymysql
import pandas as pd

# ---------------------------------------------------------
# 2. [주문 & 채팅] DB 연결 및 쿼리 함수
# ---------------------------------------------------------
def get_db_connection():
    return pymysql.connect(
        host="172.30.1.12",      # DB 주소
        user="root",           # DB 유저명
        password="1234",   # DB 비밀번호
        database="baemin",   # DB 이름
        charset='utf8mb4'
    )

# --- 채팅 관련 DB 함수 ---

def get_recent_chat_messages():
    """최근 1시간 이내의 채팅 내역만 가져오기"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = """
        SELECT username, message, created_at 
        FROM chat_messages 
        WHERE created_at >= NOW() - INTERVAL 1 HOUR 
        ORDER BY created_at ASC
    """
    cursor.execute(query)
    messages = cursor.fetchall()
    conn.close()
    return messages

def save_chat_message(username, message):
    """채팅 메시지 DB 저장"""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO chat_messages (username, message) VALUES (%s, %s)"
    cursor.execute(query, (username, message))
    conn.commit()
    conn.close()

# --- 주문 관련 DB 함수 ---

def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM stores ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_stores(category):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = "SELECT id, name, min_order_amount FROM stores WHERE category = %s"
    cursor.execute(query, (category,))
    stores = cursor.fetchall()
    conn.close()
    return stores

def get_menus(store_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = "SELECT id, menu_name, price FROM menus WHERE store_id = %s"
    cursor.execute(query, (store_id,))
    menus = cursor.fetchall()
    conn.close()
    return menus

def get_current_orders():
    conn = get_db_connection()
    query = """
        SELECT 
            o.id, 
            o.eater_name, 
            s.name as store_name, 
            m.menu_name, 
            o.price, 
            o.quantity, 
            (o.price * o.quantity) as total 
        FROM orders o
        JOIN stores s ON o.store_id = s.id
        JOIN menus m ON o.menu_id = m.id
        ORDER BY o.created_at DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_store_totals():
    conn = get_db_connection()
    query = """
        SELECT 
            s.name as store_name, 
            SUM(o.price * o.quantity) as total,
            s.min_order_amount
        FROM orders o
        JOIN stores s ON o.store_id = s.id
        GROUP BY s.id, s.name, s.min_order_amount
        ORDER BY total DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def save_order(eater, store_id, menu_id, price, quantity):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO orders (eater_name, store_id, menu_id, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (eater, store_id, menu_id, price, quantity))
    conn.commit()
    conn.close()

def delete_orders(order_ids):
    if not order_ids:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    format_strings = ','.join(['%s'] * len(order_ids))
    query = f"DELETE FROM orders WHERE id IN ({format_strings})"
    cursor.execute(query, tuple(order_ids))
    conn.commit()
    conn.close()

def clear_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE orders")
    conn.commit()
    conn.close()

def get_popular_store_stats():
    """가게별 주문 건수(인기 순위) 조회"""
    conn = get_db_connection()
    # 주문 횟수가 많은 순서대로 정렬
    query = """
        SELECT s.name as store_name, COUNT(*) as order_count 
        FROM orders o
        JOIN stores s ON o.store_id = s.id
        GROUP BY s.id, s.name 
        ORDER BY order_count DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df