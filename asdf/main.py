import streamlit as st
from kh import *
from sj import *
from hh import *
from chat import *

# ---------------------------------------------------------
# 1. 페이지 설정 (가장 먼저 실행되어야 함)
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="점심 메뉴 취합 & 채팅", page_icon="🍚")

# 사이드바에 채팅 표시
with st.sidebar:
    render_chat_content()

st.title("오늘의 점심 메뉴 취합 🍚")

popular_realtime()
st.divider()
render_order_status()
st.divider()
render_choose_menu()
st.divider()
render_multi_orderers()
st.divider()
render_sum_by_store()