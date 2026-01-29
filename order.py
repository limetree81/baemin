import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# ---------------------------------------------------------
# 1. DB 연결 설정 (st.secrets 사용 권장)
# ---------------------------------------------------------
# 로컬 테스트 시 직접 입력하거나 .streamlit/secrets.toml 파일 사용
def get_db_connection():
    return pymysql.connect(
        host="172.30.1.12",      # DB 주소
        user="root",           # DB 유저명
        password="1234",   # DB 비밀번호
        database="baemin",   # DB 이름
        charset='utf8mb4'
    )
import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# ---------------------------------------------------------
# 2. 데이터 조회/저장 함수 (Query Functions)
# ---------------------------------------------------------
def get_categories():
    """stores 테이블에서 존재하는 카테고리만 중복 없이 가져오기"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM stores ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_stores(category):
    """선택된 카테고리에 해당하는 가게 가져오기"""
    conn = get_db_connection()
    # pymysql에서 딕셔너리 커서를 사용하려면 cursorclass 인자나 아래 방식을 사용
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = "SELECT id, name, min_order_amount FROM stores WHERE category = %s"
    cursor.execute(query, (category,))
    stores = cursor.fetchall()
    conn.close()
    return stores

def get_menus(store_id):
    """선택된 가게의 메뉴 가져오기"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = "SELECT id, menu_name, price FROM menus WHERE store_id = %s"
    cursor.execute(query, (store_id,))
    menus = cursor.fetchall()
    conn.close()
    return menus

def get_current_orders():
    """현재 쌓인 주문 내역 가져오기"""
    conn = get_db_connection()
    # 최신 주문이 위로 오게 정렬
    query = "SELECT eater_name, store_name, menu_name, price, quantity, (price * quantity) as total FROM orders ORDER BY created_at DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_store_totals():
    """가게별 주문 총액 및 최소주문금액 달성 여부 조회"""
    conn = get_db_connection()
    # orders 테이블에는 store_id가 없으므로 store_name으로 JOIN합니다.
    # stores 테이블에서 min_order_amount를 가져와 비교합니다.
    query = """
        SELECT 
            o.store_name, 
            SUM(o.price * o.quantity) as total,
            s.min_order_amount
        FROM orders o
        JOIN stores s ON o.store_name = s.name
        GROUP BY o.store_name, s.min_order_amount
        ORDER BY total DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def save_order(eater, store_name, menu_name, price, quantity):
    """주문 DB에 저장하기"""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO orders (eater_name, store_name, menu_name, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (eater, store_name, menu_name, price, quantity))
    conn.commit()
    conn.close()

def clear_orders():
    """주문 내역 전체 삭제 (초기화)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE orders")
    conn.commit()
    conn.close()

#주석추가

# ---------------------------------------------------------
# 3. UI 구성 (Layout)
# ---------------------------------------------------------
st.set_page_config(page_title="점심 메뉴 취합", page_icon="🍚")

st.title("오늘의 점심 메뉴 취합 🍚")

# [영역 A] 실시간 주문 현황
st.subheader("📋 현재 주문 현황")
col_refresh, col_reset = st.columns([1, 6])
with col_refresh:
    if st.button("새로고침 🔄"):
        st.rerun()
with col_reset:
    if st.button("전체 초기화 🗑️", type="primary"):
        clear_orders()
        st.success("주문 내역이 초기화되었습니다.")
        st.rerun()

orders_df = get_current_orders()

if not orders_df.empty:
    # 1. 상세 주문 내역 표시
    st.dataframe(
        orders_df, 
        column_config={
            "eater_name": "먹을 사람",
            "store_name": "가게",
            "menu_name": "메뉴",
            "price": st.column_config.NumberColumn("단가", format="%d원"),
            "quantity": "수량",
            "total": st.column_config.NumberColumn("합계", format="%d원")
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.divider()
    
    # 2. 금액 집계 (전체 총액 & 가게별 합계)
    col_total, col_store_sum = st.columns([1, 1])
    
    with col_total:
        total_amount = orders_df['total'].sum()
        st.metric(label="💰 전체 총 주문 금액", value=f"{total_amount:,}원")
        
    with col_store_sum:
        st.caption("🏪 가게별 주문 가능 여부")
        # DB에서 GROUP BY 쿼리로 집계된 데이터 가져오기 (최소주문금액 포함)
        store_sums = get_store_totals()
        
        # [NEW] 최소주문금액 비교 로직 추가
        def get_status(row):
            if row['total'] >= row['min_order_amount']:
                return "✅ 주문 가능"
            else:
                diff = row['min_order_amount'] - row['total']
                return f"❌ {diff:,}원 부족"
                
        if not store_sums.empty:
            store_sums['상태'] = store_sums.apply(get_status, axis=1)
        
            st.dataframe(
                store_sums,
                column_config={
                    "store_name": "가게명",
                    "total": st.column_config.NumberColumn("현재 합계", format="%d원"),
                    "min_order_amount": st.column_config.NumberColumn("최소주문", format="%d원"),
                    "상태": "주문 가능 여부"
                },
                hide_index=True,
                use_container_width=True
            )

else:
    st.info("아직 주문이 없습니다. 첫 번째 주문자가 되어보세요!")

st.divider()

# [영역 B] 메뉴 담기 (Cascading Select)
st.subheader("➕ 메뉴 담기")

# Step 1: 카테고리 선택
categories = get_categories()
if not categories:
    st.warning("등록된 가게/카테고리가 없습니다. DB를 확인해주세요.")
    st.stop()

selected_category = st.pills("음식점 종류", categories, selection_mode="single")

if selected_category:
    # Step 2: 가게 선택
    stores = get_stores(selected_category)
    if not stores:
        st.warning("이 카테고리에는 등록된 가게가 없습니다.")
        st.stop()
        
    store_options = {store['name']: store for store in stores}
    selected_store_name = st.selectbox("음식점 선택 🏠", list(store_options.keys()))
    selected_store_data = store_options[selected_store_name]
    
    # [NEW] 선택한 가게의 최소주문금액 정보 표시
    min_amt = selected_store_data['min_order_amount']
    st.caption(f"ℹ️ 이 가게의 최소 주문 금액은 **{min_amt:,}원**입니다.")

    # Step 3: 메뉴 선택
    menus = get_menus(selected_store_data['id'])
    if not menus:
        st.warning("이 가게에는 등록된 메뉴가 없습니다.")
        st.stop()
        
    # 메뉴명에 가격도 같이 보여주기
    menu_options = {f"{m['menu_name']} ({m['price']:,}원)": m for m in menus}
    selected_menu_label = st.selectbox("메뉴 선택 🍗", list(menu_options.keys()))
    selected_menu_data = menu_options[selected_menu_label]

    # Step 4: 주문 정보 입력
    with st.form("order_form", clear_on_submit=True):
        st.write(f"**{selected_menu_data['menu_name']}**을(를) 선택하셨습니다.")
        
        c1, c2 = st.columns(2)
        with c1:
            quantity = st.number_input("수량", min_value=1, value=1)
        with c2:
            eater_name = st.text_input("먹을 사람 (필수)")
        
        submitted = st.form_submit_button("주문 목록에 추가하기 ➕")
        
        if submitted:
            if not eater_name:
                st.error("'먹을 사람' 이름을 입력해주세요!")
            else:
                save_order(
                    eater_name,
                    selected_store_name,
                    selected_menu_data['menu_name'],
                    selected_menu_data['price'],
                    quantity
                )
                st.success(f"{eater_name}님의 주문이 저장되었습니다!")
                st.rerun()