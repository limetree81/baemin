import streamlit as st
import pandas as pd
import pymysql
import numpy as np
from datetime import datetime

# ---------------------------------------------------------
# 1. 페이지 설정 (가장 먼저 실행되어야 함)
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="점심 메뉴 취합 & 채팅", page_icon="🍚")

# ---------------------------------------------------------
# 2. [채팅] 전역 채팅 데이터 저장소 & 매니저
# ---------------------------------------------------------
@st.cache_resource
class ChatManager:
    def __init__(self):
        self.messages = []
    
    def add_message(self, user, content):
        self.messages.append({"user": user, "content": content})

chat_manager = ChatManager()

# ---------------------------------------------------------
# 3. [주문] DB 연결 및 쿼리 함수
# ---------------------------------------------------------
def get_db_connection():
    return pymysql.connect(
        host="172.30.1.12",      # DB 주소
        user="root",           # DB 유저명
        password="1234",   # DB 비밀번호
        database="baemin",   # DB 이름
        charset='utf8mb4'
    )

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
    query = "SELECT id, eater_name, store_name, menu_name, price, quantity, (price * quantity) as total FROM orders ORDER BY created_at DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_store_totals():
    conn = get_db_connection()
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
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO orders (eater_name, store_name, menu_name, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (eater, store_name, menu_name, price, quantity))
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

# ---------------------------------------------------------
# 4. [화면 구성] 왼쪽 사이드바: 채팅 영역
# ---------------------------------------------------------
@st.fragment(run_every=2)
def render_chat_content():
    st.header("💬 실시간 소통")
    st.caption("메뉴가 고민될 땐 물어보세요!")
    
    # 닉네임 입력 (기본값 설정)
    if "chat_username" not in st.session_state:
        st.session_state.chat_username = "익명"
    
    username = st.text_input("닉네임", value=st.session_state.chat_username, key="input_username")
    st.session_state.chat_username = username
    
    # 채팅 내역 표시 영역
    with st.container(height=600, border=True):
        if not chat_manager.messages:
            st.info("아직 대화가 없습니다.")
        
        for msg in chat_manager.messages:
            role = "user" if msg["user"] == username else "assistant"
            # assistant 스타일을 다른 사용자 메시지로 활용
            with st.chat_message(role, avatar="👤" if role=="user" else "👥"):
                st.markdown(f"**{msg['user']}**: {msg['content']}")

    # 입력창
    if prompt := st.chat_input("메시지 입력..."):
        chat_manager.add_message(username, prompt)
        st.rerun()

# 사이드바에 채팅 렌더링
with st.sidebar:
    render_chat_content()


# ---------------------------------------------------------
# 5. [화면 구성] 메인 영역: 주문 취합 시스템
# ---------------------------------------------------------
st.title("오늘의 점심 메뉴 취합 🍚")

# [영역 A] 실시간 주문 현황
st.subheader("📋 현재 주문 현황")
col_refresh, col_reset = st.columns([1, 8])
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
    # 1. 상세 주문 내역 표시 (체크박스 활성화)
    event = st.dataframe(
        orders_df, 
        column_config={
            "id": None, # ID 숨김
            "eater_name": "먹을 사람",
            "store_name": "가게",
            "menu_name": "메뉴",
            "price": st.column_config.NumberColumn("단가", format="%d원"),
            "quantity": "수량",
            "total": st.column_config.NumberColumn("합계", format="%d원")
        },
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="multi-row"
    )
    
    # 삭제 버튼 로직
    if len(event.selection.rows) > 0:
        selected_indices = event.selection.rows
        selected_ids = orders_df.iloc[selected_indices]['id'].tolist()
        
        if st.button(f"선택한 {len(selected_ids)}개 주문 삭제하기 🗑️", type="secondary"):
            delete_orders(selected_ids)
            st.success("선택한 주문이 삭제되었습니다.")
            st.rerun()
    
    st.divider()
    
    # 2. 가게별 합계
    st.subheader("🏪 가게별 주문 가능 여부")
    store_sums = get_store_totals()
    
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
    st.info("아직 주문이 없습니다. 채팅으로 메뉴를 상의하고 첫 번째 주문자가 되어보세요!")

st.divider()

# [영역 B] 메뉴 담기
st.subheader("➕ 메뉴 담기")

categories = get_categories()
if not categories:
    st.warning("등록된 가게/카테고리가 없습니다. DB를 확인해주세요.")
    st.stop()

selected_category = st.pills("음식점 종류", categories, selection_mode="single")

if selected_category:
    stores = get_stores(selected_category)
    if not stores:
        st.warning("이 카테고리에는 등록된 가게가 없습니다.")
        st.stop()
        
    store_options = {store['name']: store for store in stores}
    selected_store_name = st.selectbox("음식점 선택 🏠", list(store_options.keys()))
    selected_store_data = store_options[selected_store_name]
    
    min_amt = selected_store_data['min_order_amount']
    st.caption(f"ℹ️ 이 가게의 최소 주문 금액은 **{min_amt:,}원**입니다.")

    menus = get_menus(selected_store_data['id'])
    if not menus:
        st.warning("이 가게에는 등록된 메뉴가 없습니다.")
        st.stop()
        
    menu_options = {f"{m['menu_name']} ({m['price']:,}원)": m for m in menus}
    selected_menu_label = st.selectbox("메뉴 선택 🍗", list(menu_options.keys()))
    selected_menu_data = menu_options[selected_menu_label]

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