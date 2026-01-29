import streamlit as st
import pandas as pd
import pymysql
import numpy as np
from datetime import datetime
import altair as alt
import random
import time

# ---------------------------------------------------------
# 1. 페이지 설정 (가장 먼저 실행되어야 함)
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="점심 메뉴 취합 & 채팅", page_icon="🍚")

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

def get_popular_store_stats():
    """가게별 주문 건수(인기 순위) 조회"""
    conn = get_db_connection()
    # 주문 횟수가 많은 순서대로 정렬
    query = """
        SELECT store_name, COUNT(*) as order_count 
        FROM orders 
        GROUP BY store_name 
        ORDER BY order_count DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df
# ---------------------------------------------------------
# 3. [화면 구성] 왼쪽 사이드바: 채팅 영역
# ---------------------------------------------------------
@st.fragment(run_every=2)
def render_chat_content():
    st.header("💬 실시간 소통")
    st.caption("최근 1시간 내의 대화만 표시됩니다.")
    
    # 닉네임 입력 (세션 스테이트로 관리)
    if "chat_username" not in st.session_state:
        st.session_state.chat_username = "익명"
    
    username = st.text_input("닉네임", value=st.session_state.chat_username, key="input_username")
    st.session_state.chat_username = username
    
    # DB에서 메시지 불러오기 (1시간 이내)
    messages = get_recent_chat_messages()
    
    # 채팅 내역 표시 영역
    with st.container(height=600, border=True):
        if not messages:
            st.info("아직 대화가 없습니다.")
        
        for msg in messages:
            # DB에서 가져온 데이터는 딕셔너리 형태 (username, message, created_at)
            role = "user" if msg['username'] == username else "assistant"
            
            with st.chat_message(role, avatar="👤" if role=="user" else "👥"):
                # 시간 표시 (HH:MM)
                time_str = msg['created_at'].strftime("%H:%M")
                st.markdown(f"**{msg['username']}** ({time_str})")
                st.write(msg['message'])

    # 입력창
    if prompt := st.chat_input("메시지 입력..."):
        if not username:
            st.error("닉네임을 먼저 입력해주세요.")
        else:
            save_chat_message(username, prompt)
            st.rerun()

# 사이드바에 채팅 렌더링
with st.sidebar:
    render_chat_content()


# ---------------------------------------------------------
# 4. [화면 구성] 메인 영역: 주문 취합 시스템
# ---------------------------------------------------------
st.title("오늘의 점심 메뉴 취합 🍚")
st.subheader("🔥 실시간 인기 맛집")

popular_df = get_popular_store_stats()

if not popular_df.empty:
    # -------------------------------------------------------
    # [수정 1] 축 눈금 중복(0, 1, 1, 2) 방지 계산 로직
    # -------------------------------------------------------
    max_order = int(popular_df['order_count'].max())
    
    # 주문 수가 적을 때(예: 10개 이하)는 0, 1, 2... 리스트를 강제로 만듦
    if max_order <= 10:
        tick_vals = list(range(max_order + 1))
    else:
        tick_vals = None # 많으면 자동 설정
        
    # -------------------------------------------------------
    # [수정 2] 화면 분할로 "작게" 보여주기
    # -------------------------------------------------------
    # 왼쪽(1)은 1등 강조 텍스트, 오른쪽(2)은 차트 배치
    col_info, col_chart = st.columns([1, 2])
    
    with col_info:
        # 1등 가게 정보 추출
        top_store = popular_df.iloc[0]['store_name']
        top_count = popular_df.iloc[0]['order_count']
        
        st.info(f"🏆 현재 1등\n\n**{top_store}**\n\n({top_count}명)")

    with col_chart:
        # Altair 차트 설정
        chart = alt.Chart(popular_df).mark_bar().encode(
            x=alt.X('order_count', 
                    title=None, # 차트가 작으므로 축 제목 제거 (깔끔하게)
                    axis=alt.Axis(values=tick_vals, format='d') # [핵심] 정수 눈금 강제 적용
            ), 
            y=alt.Y('store_name', 
                    sort='-x', 
                    title=None # y축 제목 제거
            ), 
            color=alt.value("#FF4B4B"),
            tooltip=['store_name', 'order_count']
        ).properties(
            # [핵심] 높이를 고정하지 않고, 데이터 1줄당 40픽셀로 자동 조절
            # 가게가 적으면 차트도 작아집니다.
            height=alt.Step(40) 
        )
        
        st.altair_chart(chart, use_container_width=True)

else:
    st.info("아직 집계된 인기 순위가 없습니다.")

st.divider()
# [영역 A] 실시간 주문 현황 (자동 새로고침 적용)
@st.fragment(run_every=2)
def render_order_status():
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
##############################################################################################################################    
        # 1. 체크박스 컬럼 추가 (주문 가능할 때만 체크박스 표시를 위해 기본값 None 활용)
        # '❌'가 포함된 행은 체크박스를 선택할 수 없도록 None(비활성화 효과) 처리
        store_sums.insert(0, "선택", False)
        store_sums.loc[store_sums['상태'].str.contains("❌"), "선택"] = None

        col_table, col_roulette = st.columns([7, 3])

        with col_table:
            st.write("📢 **주문 가능(✅)한 가게만 선택하여 룰렛을 돌릴 수 있습니다.**")
            edited_df = st.data_editor(
                store_sums,
                column_config={
                    "선택": st.column_config.CheckboxColumn("선택", default=False),
                    "store_name": "가게명",
                    "total": st.column_config.NumberColumn("현재 합계", format="%d원"),
                    "min_order_amount": st.column_config.NumberColumn("최소주문", format="%d원"),
                    "상태": "주문 가능 여부"
                },
                disabled=["store_name", "total", "min_order_amount", "상태"], 
                hide_index=True,
                use_container_width=True,
                key="store_selector"
            )

        with col_roulette:
            st.markdown("### 🎯 심부름 룰렛")
            
            selected_rows = edited_df[edited_df["선택"] == True]
            
            if len(selected_rows) > 1:
                st.warning("⚠️ 한 곳만 선택해주세요!")
            elif len(selected_rows) == 1:
                target_store = selected_rows.iloc[0]['store_name']
                
                # [추가 보안 로직] 혹시라도 체크가 되었다면 한 번 더 검사
                if "❌" in selected_rows.iloc[0]['상태']:
                    st.error("금액 미달로 주문 불가한 가게입니다.")
                else:
                    participants = orders_df[orders_df['store_name'] == target_store]['eater_name'].unique().tolist()
                    
                    if participants:
                        roulette_placeholder = st.empty()
                        roulette_placeholder.info(f"📍 {target_store} 참여자")

                        if st.button("룰렛 돌리기 🎰", use_container_width=True):
                            for i in range(12):
                                temp = random.choice(participants)
                                roulette_placeholder.subheader(f"🎲 {temp}")
                                time.sleep(0.08)
                            
                            final_winner = random.choice(participants)
                            roulette_placeholder.success(f"👑 {final_winner} 당첨!")
                            st.balloons()
                    else:
                        st.caption("해당 가게에 주문자가 없습니다.")
            else:
                st.info("가게를 선택하면 룰렛이 활성화됩니다.")
######################################################################################################################################
    else:
        st.info("아직 주문이 없습니다. 채팅으로 메뉴를 상의하고 첫 번째 주문자가 되어보세요!")

# 프래그먼트 실행
render_order_status()

st.divider()
# ------------------------------------------------------------------
# 🚨 [NEW] 문어발(중복 참여) 감지 및 정리 구역
# ------------------------------------------------------------------
st.subheader("🕵️ 중복 참여자 점검 (문어발 단속)")

# 1. 현재 성공한(최소주문금액 넘은) 가게들만 추리기
store_sums = get_store_totals()
if not store_sums.empty:
    valid_stores = store_sums[store_sums['total'] >= store_sums['min_order_amount']]['store_name'].tolist()
    
    # 2. 성공한 가게에 들어간 주문들만 필터링
    current_orders = get_current_orders()
    if not current_orders.empty and valid_stores:
        success_orders = current_orders[current_orders['store_name'].isin(valid_stores)]
        
        # 3. 이름(eater_name)별로 몇 개의 가게에 참여했는지 카운트
        # value_counts()를 쓰면 이름별 등장 횟수가 나옵니다.
        dup_check = success_orders['eater_name'].value_counts()
        
        # 2곳 이상 성공한 파티에 낀 사람 찾기
        multi_eaters = dup_check[dup_check > 1].index.tolist()
        
        if multi_eaters:
            st.error(f"🚨 **비상!** 아래 분들은 성공한 파티 **2곳 이상**에 포함되어 있습니다!")
            st.write(f"대상자: **{', '.join(multi_eaters)}** (이대로 마감하면 점심값 2배 나갑니다 💸)")
            st.info("👇 아래에서 포기할 메뉴를 하나 삭제해주세요.")
            
            # 중복된 사람들의 주문 내역만 보여주고 삭제 버튼 제공
            dup_orders = success_orders[success_orders['eater_name'].isin(multi_eaters)]
            
            for index, row in dup_orders.iterrows():
                # Streamlit 컬럼으로 내역과 삭제 버튼 배치
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.text(row['eater_name'])
                c2.text(row['store_name'])
                c3.text(f"{row['menu_name']}")
                
                # 삭제 기능 (DELETE 쿼리 필요)
                if c4.button("삭제❌", key=f"del_{index}"):
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        # ⚠️ 주의: 실제로는 id(Primary Key)로 지우는게 안전하지만, 
                        # 편의상 이름+가게+메뉴로 매칭해서 지웁니다.
                        sql = """
                            DELETE FROM orders 
                            WHERE eater_name=%s AND store_name=%s AND menu_name=%s LIMIT 1
                        """
                        cursor.execute(sql, (row['eater_name'], row['store_name'], row['menu_name']))
                    conn.commit()
                    conn.close()
                    st.toast(f"{row['store_name']} 주문을 포기하셨습니다.")
                    st.rerun()
        else:
            st.success("✅ 중복 참여자가 없습니다. (모두 1인 1메뉴 확정!)")
    else:
        st.caption("아직 최소주문금액을 달성한 파티가 없습니다.")
# [영역 B] 메뉴 담기
st.subheader("➕ 메뉴 담기")
# ------------------------------------------------------------------
# [연동] 기존 배민 데이터 매니저 앱으로 이동하기
# ------------------------------------------------------------------
with st.expander("🙋‍♀️ 원하는 가게나 메뉴가 없으신가요? (등록하러 가기)"):
    st.info("아래 버튼을 누르면 **데이터 매니저(등록 페이지)**가 새 창에서 열립니다.\n\n등록 후 이 페이지를 **새로고침(F5)** 하시면 메뉴가 나타납니다!\n\n등록 후 이상있을 시 금경훈🧙‍♂️ 님을 찾도록.")
    
    # [중요] 두 번째 앱(데이터 매니저)이 실행 중인 주소를 적어야 합니다.
    # 보통 두 번째로 실행하면 포트가 8502가 됩니다.
    st.link_button("🚀 가게/메뉴 등록하러 이동하기", "http://172.30.1.12:8502")
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