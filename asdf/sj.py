import streamlit as st
from db import *
import altair as alt

def popular_realtime():
    st.subheader("🔥 실시간 인기 맛집")

    popular_df = get_popular_store_stats()

    if not popular_df.empty:
        max_order = int(popular_df['order_count'].max())
        if max_order <= 10:
            tick_vals = list(range(max_order + 1))
        else:
            tick_vals = None
            
        col_info, col_chart = st.columns([1, 2])
        
        with col_info:
            top_store = popular_df.iloc[0]['store_name']
            top_count = popular_df.iloc[0]['order_count']
            st.info(f"🏆 현재 1등\n\n**{top_store}**\n\n({top_count}명)")

        with col_chart:
            chart = alt.Chart(popular_df).mark_bar().encode(
                x=alt.X('order_count', title=None, axis=alt.Axis(values=tick_vals, format='d')), 
                y=alt.Y('store_name', sort='-x', title=None), 
                color=alt.value("#FF4B4B"),
                tooltip=['store_name', 'order_count']
            ).properties(height=alt.Step(40))
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("아직 집계된 인기 순위가 없습니다.")

@st.fragment(run_every=2)
def render_multi_orderers():
    st.subheader("🕵️ 중복 참여자 점검 (문어발 단속)")
    store_sums = get_store_totals()
    if not store_sums.empty:
        valid_stores = store_sums[store_sums['total'] >= store_sums['min_order_amount']]['store_name'].tolist()
        current_orders = get_current_orders()
        if not current_orders.empty and valid_stores:
            success_orders = current_orders[current_orders['store_name'].isin(valid_stores)]
            dup_check = success_orders['eater_name'].value_counts()
            multi_eaters = dup_check[dup_check > 1].index.tolist()
            
            if multi_eaters:
                st.error(f"🚨 **비상!** 아래 분들은 성공한 파티 **2곳 이상**에 포함되어 있습니다!")
                st.write(f"대상자: **{', '.join(multi_eaters)}** (이대로 마감하면 점심값 2배 나갑니다 💸)")
                st.info("👇 아래에서 포기할 메뉴를 하나 삭제해주세요.")
                dup_orders = success_orders[success_orders['eater_name'].isin(multi_eaters)]
                for index, row in dup_orders.iterrows():
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    c1.text(row['eater_name'])
                    c2.text(row['store_name'])
                    c3.text(f"{row['menu_name']}")
                    if c4.button("삭제❌", key=f"del_{index}"):
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            sql = "DELETE FROM orders WHERE eater_name=%s AND store_name=%s AND menu_name=%s LIMIT 1"
                            cursor.execute(sql, (row['eater_name'], row['store_name'], row['menu_name']))
                        conn.commit()
                        conn.close()
                        st.toast(f"{row['store_name']} 주문을 포기하셨습니다.")
                        st.rerun()
            else:
                st.success("✅ 중복 참여자가 없습니다. (모두 1인 1메뉴 확정!)")
    else:
        st.caption("아직 최소주문금액을 달성한 파티가 없습니다.")