import streamlit as st
from db import *

@st.fragment(run_every=2)
def render_chat_content():
    st.header("💬 실시간 소통")
    st.caption("최근 1시간 내의 대화만 표시됩니다.")
    
    # 닉네임 입력 (세션 스테이트로 관리)
    if "chat_username" not in st.session_state:
        st.session_state.chat_username = "익명"
    
    username = st.text_input("닉네임", value=st.session_state.chat_username, key="input_username")
    st.session_state.chat_username = username
    
    # [보안] 금지된 닉네임 리스트 정의 (소문자로 비교 예정)
    RESERVED_NICKNAMES = ["system", "admin", "administrator", "root", "관리자", "운영자", "공지", "🎲 룰렛봇"]

    messages = get_recent_chat_messages()
    
    with st.container(height=600, border=True):
        if not messages:
            st.info("아직 대화가 없습니다.")
        
        for msg in messages:
            role = "user" if msg['username'] == username else "assistant"
            # 룰렛봇은 특별한 아이콘으로 표시
            avatar = "🎰" if msg['username'] == "🎲 룰렛봇" else ("👤" if role=="user" else "👥")
            
            with st.chat_message(role, avatar=avatar):
                time_str = msg['created_at'].strftime("%H:%M")
                st.markdown(f"**{msg['username']}** ({time_str})")
                st.write(msg['message'])

    if prompt := st.chat_input("메시지 입력..."):
        if not username:
            st.error("닉네임을 먼저 입력해주세요.")
        elif username.strip().lower() in RESERVED_NICKNAMES:
            # [보안] 닉네임 검증 로직
            st.error("🚫 해당 닉네임은 시스템 예약어로 사용할 수 없습니다.")
        elif "룰렛봇" in username:
             st.error("🚫 '룰렛봇'을 사칭할 수 없습니다.")
        else:
            save_chat_message(username, prompt)
            st.rerun()