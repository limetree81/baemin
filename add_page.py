import streamlit as st
import pymysql
import pandas as pd
from datetime import time
from db import get_categories

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
def fetch_to_df(sql, conn, params=None):
    try:
        conn.commit() # 최신 데이터 동기화
        with conn.cursor() as cursor:
            # params가 있으면 함께 전달, 없으면 sql만 실행
            cursor.execute(sql, params)
            result = cursor.fetchall()
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

        # [수정] st.container(border=True)를 사용하여 전체 메뉴 입력 영역을 시각적으로 하나의 박스로 묶음
        with st.container(border=True):
            menu_filter_cat = st.selectbox("먼저 카테고리를 선택하세요", options=get_categories(), index=0)
            
            # 선택된 카테고리에 해당하는 식당 조회
            stores_df = fetch_to_df(
                "SELECT id, name FROM stores WHERE category = %s ORDER BY name ASC", 
                conn, 
                (menu_filter_cat,)
            )

            if not stores_df.empty:
                store_options = stores_df['id'].tolist()
                store_labels = {row['id']: f"{row['name']}" for index, row in stores_df.iterrows()}
                
                target_id = st.selectbox(
                    f"가게 선택 ({menu_filter_cat})", 
                    options=store_options, 
                    format_func=lambda x: store_labels.get(x)
                )

                # 메뉴 이름과 가격 입력은 폼으로 구성하여 깔끔하게 정리
                with st.form("menu_reg_form", clear_on_submit=True, border=False):
                    m_name = st.text_input("메뉴명")
                    m_price = st.number_input("가격", min_value=0, step=100, value=10000)
                    submit_menu = st.form_submit_button("메뉴 등록 🍱", use_container_width=True)
                    
                    if submit_menu:
                        if not m_name:
                            st.error("메뉴명을 입력해주세요!")
                        else:
                            try:
                                with conn.cursor() as cursor:
                                    sql = "INSERT INTO menus (store_id, menu_name, price) VALUES (%s, %s, %s)"
                                    cursor.execute(sql, (int(target_id), m_name, m_price))
                                conn.commit()
                                st.toast(f"✅ '{m_name}' 추가 완료!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"메뉴 등록 중 오류 발생: {e}")

                st.divider()
                # 현재 선택된 가게의 메뉴 목록 실시간 조회
                menu_view = fetch_to_df("SELECT menu_name, price FROM menus WHERE store_id = %s", conn, (target_id,))
                st.write(f"🔍 **{store_labels[target_id]}** 메뉴 목록")
                if not menu_view.empty:
                    st.dataframe(menu_view, use_container_width=True)
                else:
                    st.caption("등록된 메뉴가 없습니다.")
            else:
                st.info(f"'{menu_filter_cat}' 카테고리에 등록된 가게가 없습니다. 먼저 가게를 등록해주세요.")

    # --- 📊 전체 데이터 확인 ---
    st.divider()
    if st.checkbox("전체 저장 데이터 보기"):
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