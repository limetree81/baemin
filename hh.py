import streamlit as st
from db import *
import time
import random

@st.fragment(run_every=2)
def render_order_status():
    st.subheader("📋 현재 주문 현황")
    
    all_orders = get_current_orders()
    store_sums_all = get_store_totals()
    sorted_store_names = store_sums_all['store_name'].tolist() if not store_sums_all.empty else []
    
    col_btn2, col_filter = st.columns([1, 8])
    
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

# [영역 A] 실시간 주문 현황\
@st.fragment(run_every=2)
def render_sum_by_store():
    st.subheader("🏪 가게별 주문 가능 여부")
    
    def get_status(row):
        if row['total'] >= row['min_order_amount']:
            return "✅ 주문 가능"
        diff = row['min_order_amount'] - row['total']
        return f"❌ {int(diff):,}원 부족"

    all_orders = get_current_orders()
    store_sums_all = get_store_totals()
    
    if not store_sums_all.empty:
        display_sums = store_sums_all.copy()
        display_sums['상태'] = display_sums.apply(get_status, axis=1)
        display_sums.insert(0, "선택", False)
        display_sums.loc[display_sums['상태'].str.contains("❌"), "선택"] = None

        c_table, c_roulette = st.columns([7, 3])
        with c_table:
            edited_df = st.data_editor(
                display_sums,
                column_config={
                    "선택": st.column_config.CheckboxColumn("선택", default=False),
                    "store_name": "가게명", "total": st.column_config.NumberColumn("합계", format="%d원"),
                    "min_order_amount": st.column_config.NumberColumn("최소", format="%d원"),
                },
                disabled=["store_name", "total", "min_order_amount", "상태"],
                hide_index=True, use_container_width=True, key="roulette_selector"
            )
        with c_roulette:
            st.markdown("### 🎯 심부름 룰렛")
            sel_rows = edited_df[edited_df["선택"] == True]
            if len(sel_rows) == 1:
                target = sel_rows.iloc[0]['store_name']
                participants = all_orders[all_orders['store_name'] == target]['eater_name'].unique().tolist()
                if participants:
                    holder = st.empty()
                    if st.button("룰렛 돌리기 🎰", use_container_width=True):
                        for i in range(10):
                            holder.subheader(f"🎲 {random.choice(participants)}")
                            time.sleep(0.08)
                        winner = random.choice(participants)
                        holder.success(f"👑 {winner} 당첨!")
                        st.balloons()
                        try:
                            message = f"🎉 [룰렛 결과] **{target}** 당첨자: **{winner}**님 축하합니다! (심부름 잘 다녀오세요~ 🏃)"
                            save_chat_message("🎲 룰렛봇", message)
                            st.toast("채팅방에 결과가 공유되었습니다!")
                        except Exception as e:
                            st.error(f"결과 저장 실패: {e}")
            elif len(sel_rows) > 1:
                st.warning("한 곳만 선택하세요.")
            else:
                st.info("조건에 맞는 주문이 없습니다. 상단 체크박스를 확인하거나 메뉴를 추가해 보세요!")
