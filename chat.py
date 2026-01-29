import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="협업 대시보드")

# 2. 전역 채팅 데이터 저장소
@st.cache_resource
class ChatManager:
    def __init__(self):
        self.messages = []
    
    def add_message(self, user, content):
        self.messages.append({"user": user, "content": content})

chat_manager = ChatManager()

# 3. 채팅 영역 함수 (수정됨!)
# 주의: 이 함수 안에서는 'st.sidebar'를 쓰지 않고 그냥 'st'를 씁니다.
# 나중에 이 함수 자체를 사이드바 안에 넣을 것이기 때문입니다.
@st.fragment(run_every=2)
def render_chat_content():
    st.title("💬 팀 채팅")
    
    # 닉네임 입력
    username = st.text_input("닉네임", value="익명", key="chat_username")
    
    # 채팅 내역 표시 영역
    # 높이를 지정하여 이 영역 안에서만 스크롤되게 함
    with st.container(height=500, border=True):
        for msg in chat_manager.messages:
            role = "user" if msg["user"] == username else "assistant"
            with st.chat_message(role):
                st.write(f"**{msg['user']}**: {msg['content']}")

    # 입력창
    # 여기서도 st.sidebar.chat_input이 아니라 그냥 st.chat_input입니다.
    if prompt := st.chat_input("메시지 입력..."):
        chat_manager.add_message(username, prompt)
        st.rerun()

# ==========================================
# 4. 화면 배치 (여기가 핵심 변경 사항입니다)
# ==========================================

# 사이드바 컨텍스트를 열고, 그 안에서 프래그먼트 함수를 실행합니다.
with st.sidebar:
    render_chat_content()

# ==========================================
# 5. 메인 작업 영역 (채팅과 무관한 공간)
# ==========================================

st.title("📊 데이터 분석 대시보드")
st.info("왼쪽 사이드바 채팅창은 2초마다 자동 갱신되지만, 이 메인 화면은 멈추거나 깜빡이지 않습니다.")

tab1, tab2 = st.tabs(["매출 분석", "데이터 편집"])

with tab1:
    st.subheader("실시간 매출 현황")
    chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["A", "B", "C"])
    st.line_chart(chart_data)

with tab2:
    st.subheader("데이터 프레임")
    st.data_editor(pd.DataFrame({'Product': ['A', 'B'], 'Price': [100, 200]}))