import streamlit as st
from db import *

@st.fragment(run_every=2)
def render_order_status():
    st.subheader("📋 현재 주문 현황")
    
    all_orders = get_current_orders()
    store_sums_all = get_store_totals()
    sorted_store_names = store_sums_all['store_name'].tolist() if not store_sums_all.empty else []
    
    col_btn1, col_btn2, col_filter = st.columns([1, 1, 8])
    
    with col_btn1:
        if st.button("새로고침 🔄", use_container_width=True):
            st.rerun()
    with col_btn2:
        if st.button("전체 초기화 🗑️", type="primary", use_container_width=True):
            clear_orders()
            st.rerun()
            
    # --- [핵심 수정: 양방향 전체 선택 로직] ---
    selected_stores = []
    if sorted_store_names:
        # 1. 초기 세션 상태 설정
        if "master_checkbox" not in st.session_state:
            st.session_state.master_checkbox = True
        for s_name in sorted_store_names:
            if f"filter_{s_name}" not in st.session_state:
                st.session_state[f"filter_{s_name}"] = True

        # 2. 콜백 함수 정의
        def on_master_change():
            """전체 체크박스 변경 시 모든 개별 체크박스 동기화"""
            val = st.session_state.master_checkbox
            for s_name in sorted_store_names:
                st.session_state[f"filter_{s_name}"] = val

        def on_individual_change():
            """개별 체크박스 변경 시 전체 체크박스 상태 계산"""
            # 모든 개별 체크박스가 True인지 확인
            all_checked = all(st.session_state[f"filter_{s_name}"] for s_name in sorted_store_names)
            st.session_state.master_checkbox = all_checked
        with col_filter:
            # ▼ 여기(st.checkbox)부터 아래쪽 끝까지 전부 들여쓰기(Tab) 하세요
            st.checkbox("전체 선택/해제", key="master_checkbox", on_change=on_master_change)
            
            # 가게 목록을 4열로 배치
            num_columns = 4
            cols = st.columns(num_columns)
            
            for i, s_name in enumerate(sorted_store_names):
                with cols[i % num_columns]:
                    if st.checkbox(s_name, key=f"filter_{s_name}", on_change=on_individual_change):
                        selected_stores.append(s_name)
    # ----------------------------------------

    filtered_orders = all_orders[all_orders['store_name'].isin(selected_stores)] if not all_orders.empty else all_orders

    if not filtered_orders.empty:
        event = st.dataframe(
            filtered_orders, 
            column_config={
                "id": None, "eater_name": "먹을 사람", "store_name": "가게",
                "menu_name": "메뉴", "price": st.column_config.NumberColumn("단가", format="%d원"),
                "quantity": "수량", "total": st.column_config.NumberColumn("합계", format="%d원")
            },
            hide_index=True, use_container_width=True, on_select="rerun", selection_mode="multi-row"
        )
        
        if len(event.selection.rows) > 0:
            selected_ids = filtered_orders.iloc[event.selection.rows]['id'].tolist()
            if st.button(f"선택한 {len(selected_ids)}개 주문 삭제 🗑️"):
                delete_orders(selected_ids)
                st.rerun()
    else:
        st.info("선택된 주문이 없거나 체크박스가 모두 해제되어 있습니다.")
