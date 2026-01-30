# 단체주문 취합 서버
## Database 프로젝트 어쩌구 저쩌구

---

### requirements
```
pandas
streamlit
streamlit-autorefresh
```
or maybe more

---

### Open Server

1. db 서버 열기(mysql / mariadb 권장)
db 서버를 구축하세요.
1.sql을 실행하세요.(테이블과 아이템을 추가해줍니다.)

db.py 코드에서 다음 부분을 알맞게 수정해주세요.

```
def get_db_connection():
    return pymysql.connect(
        host="172.30.1.12",      # DB 주소
        user="root",           # DB 유저명
        password="1234",   # DB 비밀번호
        database="baemin",   # DB 이름
        charset='utf8mb4'
    )
```

streamlit 실행 - 두 개의 터미널에서 각각 실행해주세요

```
streamlit run main.py
streamlit run add_page.py
```

그러면 아마 add_page로 리다이렉트 링크가 잘 안 맞을 겁니다.
여기 수정해주세요.

```
import streamlit as st
from db import *

def render_choose_menu():
    st.subheader("➕ 메뉴 담기")

    with st.expander("🙋‍♀️ 원하는 가게나 메뉴가 없으신가요? (등록하러 가기)"):
        st.info("아래 버튼을 누르면 **데이터 매니저(등록 페이지)**가 새 창에서 열립니다.\n\n등록 후 이 페이지를 **새로고침(F5)** 하시면 메뉴가 나타납니다!\n\n등록 후 이상있을 시 금경훈🧙‍♂️ 님을 찾도록.")
        st.link_button("🚀 가게/메뉴 등록하러 이동하기", "http://172.30.1.12:8502") #여기 주소 수정
```

오류 수정 제보는 (여기에 이메일 주소를 입력)로 해주세요.
미니 프로젝트 한 거 귀찮아서 고칠 생각도 없고, 이걸 누가 씀 ㅇㅇ
그거 할 거였으면 config파일이나 .env도 만들었지 ㅇㅇ

팀원 분들께는 혹시 포트폴리오로 쓰실거면 죄송하다는 말씀 드립니다.
fork하셔도 되고, 이 레포지토리에서 직접 수정하셔도 됩니다.

---

### Usage
(사진 넣기 귀찮아서 생략)
