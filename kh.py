import streamlit as st
from db import *

def render_choose_menu():
    st.subheader("➕ 메뉴 담기")

    with st.expander("🙋‍♀️ 원하는 가게나 메뉴가 없으신가요? (등록하러 가기)"):
        st.info("아래 버튼을 누르면 **데이터 매니저(등록 페이지)**가 새 창에서 열립니다.\n\n등록 후 이 페이지를 **새로고침(F5)** 하시면 메뉴가 나타납니다!\n\n등록 후 이상있을 시 금경훈🧙‍♂️ 님을 찾도록.")
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
            
        store_options = {s['name']: s for s in stores}
        selected_store_name = st.selectbox("음식점 선택 🏠", options=list(store_options.keys()))
        selected_store_data = store_options[selected_store_name]
        selected_store_id = selected_store_data['id'] # 선택된 이름의 진짜 ID값
        min_amt = selected_store_data['min_order_amount']
        st.caption(f"ℹ️ 이 가게의 최소 주문 금액은 **{min_amt:,}원**입니다.")

        menus = get_menus(selected_store_id)
        if not menus:
            st.warning("이 가게에는 등록된 메뉴가 없습니다.")
            st.stop()
            
        menu_options = {f"{m['menu_name']} ({m['price']:,}원)": m for m in menus}
        selected_menu_label = st.selectbox("메뉴 선택 🍗", list(menu_options.keys()))
        selected_menu_data = menu_options[selected_menu_label]
        selected_menu_id = selected_menu_data['id']    # DB의 menu_id 컬럼으로 들어갈 숫자
        selected_price = selected_menu_data['price']    # DB의 price 컬럼으로 들어갈 숫자

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
                        selected_store_id,
                        selected_menu_id,
                        selected_menu_data['price'],
                        quantity
                    )
                    st.success(f"{eater_name}님의 주문이 저장되었습니다!")
                    st.rerun()