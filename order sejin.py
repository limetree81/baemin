import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import altair as alt

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
# 3. UI 구성 (Layout)
# ---------------------------------------------------------
st.set_page_config(page_title="점심 메뉴 취합", page_icon="🍚")

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
# [영역 B] 메뉴 담기 (Cascading Select)
st.subheader("➕ 메뉴 담기")

# ------------------------------------------------------------------
# [연동] 기존 배민 데이터 매니저 앱으로 이동하기
# ------------------------------------------------------------------
with st.expander("🙋‍♀️ 원하는 가게나 메뉴가 없으신가요? (등록하러 가기)"):
    st.info("아래 버튼을 누르면 **데이터 매니저(등록 페이지)**가 새 창에서 열립니다.\n\n등록 후 이 페이지를 **새로고침(F5)** 하시면 메뉴가 나타납니다!\n\n등록 후 이상있을 시 금경훈🧙‍♂️ 님을 찾도록.")
    
    # [중요] 두 번째 앱(데이터 매니저)이 실행 중인 주소를 적어야 합니다.
    # 보통 두 번째로 실행하면 포트가 8502가 됩니다.
    st.link_button("🚀 가게/메뉴 등록하러 이동하기", "http://172.30.1.12:8502")
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