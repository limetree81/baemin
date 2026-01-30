import streamlit as st
import pymysql
import pandas as pd
from datetime import time

# 1. DB 연결 함수 (경훈님 로컬 서버 설정)
def init_db():
    try:
        conn = pymysql.connect(
            host='172.30.1.12',
            user='root',          # 사용자 계정명
            password='1234',      # 비밀번호
            db='baemin',          # 데이터베이스 이름
            port=3306,            # 포트
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        st.error(f"❌ DB 접속 실패: {e}")
        return None

# SQL 결과를 DataFrame으로 안전하게 변환하는 헬퍼 함수
def fetch_to_df(sql, conn):
    try:
        conn.commit() # 최신 데이터 동기화
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            # DictCursor 결과는 [{}, {}] 형태이므로 바로 DataFrame 생성이 가능하고 가장 정확합니다.
            return pd.DataFrame(result)
    except Exception as e:
        st.error(f"데이터 조회 중 오류: {e}")
        return pd.DataFrame()

st.set_page_config(page_title="배민 데이터 매니저", layout="wide")
st.title("🏹 [로컬 서버] 배민 파티 데이터 구축 도구")

conn = init_db()

if conn:
    # --- 🏢 1. 가게 정보 입력 섹션 ---
    col_store, col_menu = st.columns([1, 1])

    with col_store:
        st.subheader("🏢 1. 가게 정보 입력")
        with st.form("store_form", clear_on_submit=True):
            st_name = st.text_input("가게명 (예: 교촌치킨 부트캠프점)")
            st_category = st.radio("카테고리", ['패스트푸드','카페·디저트','한식','찜·탕','분식','중식','돈까스·회','피자','치킨','양식','고기','아시안','족발·보쌈'], horizontal=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st_rating = st.slider("별점", 0.0, 5.0, 4.5, 0.1)
            with c2:
                st_min_order = st.number_input("최소주문금액(원)", min_value=0, step=1000, value=12000)

            days = ["월", "화", "수", "목", "금", "토", "일"]
            selected_days = []
            day_cols = st.columns(7)
            for i, day in enumerate(days):
                if day_cols[i].checkbox(day, value=(True if i < 5 else False)):
                    selected_days.append(day)
            
            working_hours = st.slider("영업시간", value=(time(10, 0), time(22, 0)))
            submit_store = st.form_submit_button("가게 등록하기")
            
            if submit_store:
                if st_name and selected_days:
                    working_days_str = ", ".join(selected_days)
                    open_t = working_hours[0].strftime("%H:%M")
                    close_t = working_hours[1].strftime("%H:%M")
                    
                    try:
                        with conn.cursor() as cursor:
                            sql = "INSERT INTO stores (name, category, rating, min_order_amount, working_days, open_time, close_time) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                            cursor.execute(sql, (st_name, st_category, st_rating, st_min_order, working_days_str, open_t, close_t))
                        conn.commit()
                        st.success(f"✅ '{st_name}' 등록 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"가게 등록 중 오류 발생: {e}")

    # --- 🍱 2. 메뉴 정보 입력 섹션 ---
    with col_menu:
        st.subheader("🍱 2. 메뉴 정보 입력")
        # 수정: fetch_to_df 함수 사용
        
        stores_df = fetch_to_df("SELECT id, name FROM stores ORDER BY id DESC", conn)
        print(stores_df)
        
        if not stores_df.empty:
            store_options = stores_df['id'].tolist()
            store_labels = {row['id']: f"{row['name']}" for index, row in stores_df.iterrows()}

            with st.form("menu_form", clear_on_submit=True):
                target_id = st.selectbox(
                    "가게 선택", 
                    options=store_options, 
                    format_func=lambda x: store_labels.get(x)
                )
                
                m_name = st.text_input("메뉴명")
                m_price = st.number_input("가격", min_value=0, step=100, value=10000)
                submit_menu = st.form_submit_button("메뉴 등록")
                
                if submit_menu and m_name:
                    try:
                        with conn.cursor() as cursor:
                            sql = "INSERT INTO menus (store_id, menu_name, price) VALUES (%s, %s, %s)"
                            cursor.execute(sql, (int(target_id), m_name, m_price))
                        conn.commit()
                        st.toast(f"'{m_name}' 추가됨!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"메뉴 등록 중 오류 발생: {e}")

            st.divider()
            # 수정: fetch_to_df 함수 사용
            menu_view = fetch_to_df(f"SELECT menu_name, price FROM menus WHERE store_id = {target_id}", conn)
            st.write(f"🔍 {store_labels[target_id]} 메뉴 목록")
            st.dataframe(menu_view, use_container_width=True)
        else:
            st.info("먼저 가게를 등록해주세요.")

    # --- 📊 전체 데이터 확인 ---
    st.divider()
    if st.checkbox("전체 저장 데이터 보기"):
        # 수정: fetch_to_df 함수 사용
        all_data_query = """
            SELECT s.id as ID, s.name as 가게명, s.category as 카테고리, s.rating as 별점, 
                   s.working_days as 영업일, CONCAT(s.open_time, '~', s.close_time) as 영업시간,
                   m.menu_name as 메뉴명, m.price as 가격
            FROM stores s 
            LEFT JOIN menus m ON s.id = m.store_id
            ORDER BY s.id DESC
        """
        all_data = fetch_to_df(all_data_query, conn)
        if not all_data.empty:
            st.dataframe(all_data, use_container_width=True)
        else:
            st.write("표시할 데이터가 없습니다.")

    conn.close()