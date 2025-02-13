import os
import streamlit as st
from streamlit_option_menu import option_menu
import mysql.connector
from mysql.connector import Error
import requests
import json
from openai import OpenAI

if 'chat_input' not in st.session_state:
    st.session_state.chat_input = ""
if 'current_page' not in st.session_state:
    st.session_state.current_page = "메인 화면"
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'competition_results' not in st.session_state:
    st.session_state.competition_results = []

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'tkwh8304*',
    'database': 'competition',
    'connection_timeout': 180
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        st.error(f"db connection error: {e}")
        return None

def search_competitions(params):
    connection = get_db_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM competition WHERE 1=1"
        conditions = []
        values = []

        if params['target'] != "전체":
            conditions.append("target = %s")
            values.append(params['target'])

        if params['period'] != "전체":
            conditions.append("period = %s")
            values.append(params['period'])

        if params['field'] != "전체":
            conditions.append("category = %s")
            values.append(params['field'])

        if params['organizer'] != "전체":
            conditions.append("org = %s")
            values.append(params['organizer'])

        if params['prize'] != "전체":
            conditions.append("award = %s")
            values.append(params['prize'])

        if conditions:
            query += " AND " + " AND ".join(conditions)

        cursor.execute(query, tuple(values))
        results = cursor.fetchall()
        return results

    except Error as e:
        st.error(f"query exec error: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def watsonx_ai_api(prompt):
    def query_perflexity(query):
        API_KEY = "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"
        messages = [
            {
                "role": "system",
                "content": (
                    "사용자가 입력한 대회의 전년도 동일 대회 또는 유사한 대회의 후기를 웹에서 검색하고 대회 준비에 도움이 될 만한 정보들을 수집하여 줄 글 형식으로 반환해. 단 사용자의 입력이 대회 또는 공모전 관련 내용이 아닌 경우 아무 응답도 하지 말고 공백만을 반환해."
                ),
            },
            {
                "role": "user",
                "content": f"{query}",
            },
        ]

        client = OpenAI(api_key=API_KEY, base_url="https://api.perplexity.ai")
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=messages,
        )
        return response.choices[0].message.content.strip()

    watsom_prompt = query_perflexity(prompt) + f"웹 검색을 통해 얻은 이 내용을 참고하여 다음 사용자의 질문에 대답해. 단, 사용자의 질문이 대회 또는 공모전에 관련된 내용이 아닌 경우 '공모전과 관련된 질문만 해주세요'라고 대답해. 질문 : {prompt}"

    try:
        payload = {"prompt": watsom_prompt}
        response = requests.post(
            "http://localhost:8304/processing",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()["text"]
    except requests.exceptions.RequestException as e:
        st.error(f"API request error: {str(e)}")
        return "죄송합니다. 응답을 생성하는 중에 오류가 발생했습니다."

def ask_chatbot(title):
    st.session_state.chat_input = f"{title}에 대해 자세히 알려줘!"
    st.session_state.current_page = "챗봇"

st.set_page_config(page_title="공모전 검색 서비스", layout="wide")

with st.sidebar:
    selected = option_menu(
        "Menu", 
        ["메인 화면", "챗봇"],
        icons=['house', 'bi bi-chat-dots'],
        menu_icon="app-indicator",
        default_index=0 if st.session_state.current_page == "메인 화면" else 1,
        styles={
            "container": {"padding": "4!important"},
            "icon": {"font-size": "25px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px"},
            "nav-link-selected": {"background-color": "#5bc0de"},
        }
    )
    
    #st.markdown("---")
    #st.markdown("#### 실시간 웹 검색을 활용한 챗봇을 이용해 해당 공모전에 대해 더 자세히 질문해보세요! \n")

    if selected != st.session_state.current_page:
        st.session_state.current_page = selected
        st.rerun()

if st.session_state.current_page == "메인 화면":
    st.title("📢 공모전 검색 서비스")
    st.write("")
    st.markdown("이 서비스는 다양한 공모전을 쉽게 검색하고 정보를 확인할 수 있도록 도와줍니다.<br>원하는 공모전을 선택하고, 🤖챗봇을 통해 추가 정보를 얻어보세요!", unsafe_allow_html=True)
    st.write("")
    st.write("")

    col1, col2, col3 = st.columns(3)
    with col1:
        target = st.selectbox("응시 대상자", ["전체", "제한없음", "일반인", "대학생", "청소년", "어린이", "기타"])
    with col2:
        period = st.selectbox("기간", ["전체", "일주일 이내", "한 달 이내", "3개월 이내", "6개월 이내", "6개월 이상"])
    with col3:
        field = st.selectbox("분야",
                             ["전체", "기획/아이디어", "광고/마케팅", "논문/리포트", "영상/UCC/사진", "디자인캐릭터웹툰", "웹/모바일/IT", "게임/소프트웨어",
                              "과학/공학", "문학/글/시나리오", "건축/건설/인테리어", "네이밍/슬로건", "예체능/미술/음악", "대외활동/서포터즈", "봉사활동", "취업/창업",
                              "해외", "기타"])

    col4, col5 = st.columns(2)
    with col4:
        organizer = st.selectbox("주최사",
                                 ["전체", "정부/공공기관", "공기업", "대기업", "신문/방송/언론", "외국계기업", "중견/중소/벤처기업", "비영리/협회/재단", "해외",
                                  "기타"])
    with col5:
        prize = st.selectbox("시상내역",
                             ["전체", "100만원 이내", "100~500만원", "500~1000만원", "1000만원 이상", "취업특전", "입사시가산점", "인턴채용",
                              "정직원채용", "기타"])

    search_button = st.button("검색")
    
    if search_button:
        params = {
            "target": target,
            "period": period,
            "field": field,
            "organizer": organizer,
            "prize": prize
        }
        st.session_state.competition_results = search_competitions(params)

    if st.session_state.competition_results:
        st.subheader("📋 공모전 목록")
        
        st.markdown("""
            <style>
            .competition-container {
                display: flex;
                align-items: stretch;
                margin: 15px 0;
                gap: 20px;
            }
            .card {
                background: #ffffff;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border-radius: 10px;
                transition: transform 0.2s;
                flex-grow: 1;
            }
            .card:hover {
                transform: scale(1.02);
            }
            .card-content {
                width: 100%;
            }
            .card-content a {
                font-size: 20px;
                color: #2B5F9E;
                text-decoration: none;
                font-weight: bold;
            }
            .card-content a:hover {
                text-decoration: underline;
            }
            .card-content ul {
                list-style: none;
                padding: 0;
                margin: 10px 0 0 0;
            }
            .card-content li {
                margin-bottom: 5px;
                font-size: 14px;
            }
            .button-container {
                display: flex;
                align-items: center;
                min-width: 150px;
            }
            </style>
            """, unsafe_allow_html=True)

        for idx, result in enumerate(st.session_state.competition_results):
            st.markdown(
                f"""
                <div class="competition-container">
                    <div class="card">
                        <div class="card-content">
                            <a href="{result["url"]}" target="_blank">{result["title"]}</a>
                            <ul>
                                <li><strong>대상:</strong> {result["target"]}</li>
                                <li><strong>분야:</strong> {result["category"]}</li>
                                <li><strong>기간:</strong> {result["period"]}</li>
                                <li><strong>주최:</strong> {result["org"]}</li>
                                <li><strong>상금:</strong> {result["award"]}</li>
                            </ul>
                        </div>
                    </div>
                    <div class="button-container">
                """, 
                unsafe_allow_html=True
            )
            
            if st.button("챗봇에게 물어보기", key=f"ask_button_{idx}"):
                ask_chatbot(result["title"])
                st.rerun()
            
            st.markdown("</div></div>", unsafe_allow_html=True)

elif st.session_state.current_page == "챗봇":
    st.title("🤖 공모전 챗봇")
    st.write("")
    st.write("챗봇을 사용해 공모전에 관한 여러 💡팁들을 얻어보세요!")
    st.write("")
    st.write("")

    chat_container = st.container()

    # ✅ 기존 대화 기록 출력 (항상 먼저 출력)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # ✅ 사용자 입력 처리
    chat_input_container = st.container()
    with chat_input_container:
        prompt = st.chat_input("무엇을 도와드릴까요?", key="chat_input_field")

        if st.session_state.chat_input:
            prompt = st.session_state.chat_input
            st.session_state.chat_input = ""

    # ✅ 새로운 메시지를 항상 대화의 끝에 추가
    if prompt:
        # 1️⃣ 사용자 메시지 먼저 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # 2️⃣ 챗봇 응답 처리
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("생각하는 중…"):
                    response = watsonx_ai_api(prompt)
                    st.markdown(response)

        # 3️⃣ 챗봇 응답 저장 (항상 마지막에 추가)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # ✅ 대화가 끝날 때마다 화면을 업데이트하여 최신 메시지가 항상 아래로 가도록 함
        st.rerun()
