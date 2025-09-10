import os, json, requests, streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Kids English Helper (MVP)", page_icon="🔎", layout="wide")


def get_secret(name: str, default: str = "") -> str:
    return st.secrets.get(name, os.getenv(name, default))

# Azure AI Search
SEARCH_ENDPOINT = get_secret("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = get_secret("AZURE_SEARCH_KEY")
SEARCH_INDEX = get_secret("AZURE_SEARCH_INDEX")

# (선택) Azure OpenAI for RAG
AOAI_ENDPOINT = get_secret("AZURE_OPENAI_ENDPOINT")
AOAI_KEY = get_secret("AZURE_OPENAI_KEY")
AOAI_DEPLOYMENT = get_secret("AZURE_OPENAI_DEPLOYMENT")


def azure_search(query: str, top: int = 5):
    """Simple REST call to Azure AI Search"""
    if not (SEARCH_ENDPOINT and SEARCH_KEY and SEARCH_INDEX):
        st.warning("Azure AI Search 설정이 필요합니다.")
        return []

    url = f"{SEARCH_ENDPOINT}/indexes/{SEARCH_INDEX}/docs/search?api-version=2023-11-01"
    headers = {"Content-Type": "application/json", "api-key": SEARCH_KEY}
    payload = {"search": query, "top": top, "queryType": "simple"}

    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("value", [])
    except Exception as e:
        st.error(f"검색 호출 실패: {e}")
        return []


# === Azure OpenAI (RAG) ===
def aoai_chat(messages, temperature=0.3, max_tokens=800):
    if not (AOAI_ENDPOINT and AOAI_KEY and AOAI_DEPLOYMENT):
        st.warning("Azure OpenAI 설정이 필요합니다.")
        return None

    url = f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions?api-version=2024-06-01"
    headers = {"Content-Type": "application/json", "api-key": AOAI_KEY}
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }

    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        st.error(f"AOAI 호출 실패: {e}")
        return None


def build_rag_prompt(query, docs):
    # compress docs for prompt
    snippets = []
    for d in docs:
        title = d.get("title") or d.get("id", "")
        series = d.get("series", "")
        level = d.get("level", "")
        content = (d.get("content", "") or "")[:600]
        phrases = d.get("phrases", [])
        snippets.append({
            "title": title, "series": series, "level": level,
            "phrases": phrases, "content": content
        })

    system = (
        "You are a kids English coach. Return JSON only. "
        "Make outputs short, A1~A2 friendly, and actionable for parents."
    )
    user = {
        "task": "Create child-friendly summary + key phrases + 3 missions + parent coaching for the query",
        "query": query,
        "docs": snippets,
        "output_schema": {
            "summary": "2-3 sentences for a child",
            "focus_phrases": ["...", "...", "..."],
            "missions": ["find expression", "shadowing 2x", "use at home once"],
            "parent_tips": ["praise line 1", "rule/tip 1"]
        }
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)}
    ]
    return messages


# === Rule-based weekly planner ===
def rule_based_plan(age: int, level: str, character: str, sessions_per_week: int = 4, minutes_per_session: int = 15):
    focus_bank = {
        "A0": ["Hello!", "My name is ...", "I like ..."],
        "A1": ["Can I ...?", "I want ...", "It's my turn."],
        "A2": ["Yesterday I ...", "Because ...", "Let's try ..."],
        "B1": ["In my opinion ...", "I prefer ...", "Be careful!"],
    }
    phrases = focus_bank.get(level, focus_bank["A1"])

    activities = []
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    for i in range(sessions_per_week):
        activities.append({
            "day": days[i % 7],
            "type": ["듣기","말하기","읽기","쓰기"][i % 4],
            "item": f"{character} clip/read",
            "focus_phrases": phrases,
            "missions": ["표현 스티커 찾기", "섀도잉 2회", "가정 대화 1회 사용"]
        })
    return {
        "weekly_goals": f"{sessions_per_week}회 × {minutes_per_session}분 / 회",
        "activities": activities,
        "time_per_day": minutes_per_session
    }


st.title("Kids English Helper (MVP)")
tabs = st.tabs(["🔎 Search", "🗓 Plan", "⚙️ Settings"])

# --- Search tab ---
with tabs[0]:
    st.subheader("KIDS 영어 콘텐츠 검색")
    # 검색어를 이미지로 선택하게 변경 예를 들어 블루이 페파피그 공룡등

    # 이미지와 함께 선택할 수 있는 캐릭터/주제 리스트
    search_options = [
        {"label": "Bluey", "image": "https://upload.wikimedia.org/wikipedia/en/0/0a/Bluey_%28cartoon_character%29.png"},
        {"label": "Peppa Pig", "image": "https://upload.wikimedia.org/wikipedia/en/e/e7/Peppa_Pig_character.png"},
        {"label": "Dinosaur", "image": "https://upload.wikimedia.org/wikipedia/commons/6/6e/Dinosaur.png"},
        {"label": "Disney/Pixar", "image": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Disney%2B_logo.svg"},
        {"label": "Pororo", "image": "https://upload.wikimedia.org/wikipedia/ko/2/2c/Pororo.png"},
        {"label": "기타", "image": "https://upload.wikimedia.org/wikipedia/commons/6/65/Question_mark_%28black%29.svg"},
    ]

    
    # 이미지 버튼 UI (이미지가 실제로 보이도록 st.image 사용)
    cols = st.columns(len(search_options))
    selected_idx = None
    for i, opt in enumerate(search_options):
        with cols[i]:
            st.image(opt["image"], width=80)  # 이미지 크기 동일하게
            if st.button(opt["label"], use_container_width=True, key=f"imgbtn_{i}"):
                selected_idx = i
                
    # 선택된 검색어
    if selected_idx is not None:
        q = search_options[selected_idx]["label"]
        st.success(f"선택된 검색어: {q}")
    else:
        q = st.text_input("검색어 입력 (예: Bluey, Peppa Pig, dinosaur)", "")

    # 나이 입력 하는 UI 추가 가능
    age = st.number_input("나이(age, 선택)", 3, 12, 7, step=1)
    level = st.selectbox("레벨(CEFR, 선택)", ["","A0","A1","A2","B1"], index=0)
    top = st.slider("Top N", 1, 20, 5)
    do_rag = st.checkbox("상위 검색 결과로  (Azure OpenAI 필요)", value=False)

    # ...existing code...
    if st.button("검색 실행", use_container_width=True):
        results = azure_search(q, top=top)
        if not results:
            st.info("검색 결과가 없습니다.")
        else:
            for doc in results:
                with st.container(border=True):
                    title = doc.get("title") or doc.get("id")
                    series = doc.get("series", "")
                    level = doc.get("level", "")
                    st.markdown(f"**{title}**  •  {series}  •  {level}")
                    content = doc.get("content", "")
                    if content:
                        st.write(content[:300] + ("..." if len(content) > 300 else ""))
                    phrases = doc.get("phrases", [])
                    if phrases:
                        st.caption("키 프레이즈: " + ", ".join(phrases))

            # 유튜브 영상 3개 제공
            st.markdown("---")
            st.markdown(f"### 유튜브에서 '{q}' 관련 영상 3개")
            # 유튜브 검색 쿼리 생성
            from urllib.parse import quote_plus
            yt_query = quote_plus(q + " cartoon")
            # 유튜브 검색 URL
            yt_search_url = f"https://www.youtube.com/results?search_query={yt_query}"
            # 임시로 embed, 실제로는 API 필요하지만, 대표 영상 3개만 임베드
            yt_samples = {
                "Bluey": [
                    "https://www.youtube.com/embed/9JkQOYwYv6A",
                    "https://www.youtube.com/embed/6R3NQb6pQ1w",
                    "https://www.youtube.com/embed/4b6bLr2Qb6E"
                ],
                "Peppa Pig": [
                    "https://www.youtube.com/embed/9wK6A2eA5nA",
                    "https://www.youtube.com/embed/1S9UeQnUnxw",
                    "https://www.youtube.com/embed/2pLT-olgUJs"
                ],
                "Dinosaur": [
                    "https://www.youtube.com/embed/3o5y6z5l5xw",
                    "https://www.youtube.com/embed/2pLT-olgUJs",
                    "https://www.youtube.com/embed/1S9UeQnUnxw"
                ],
                "Disney/Pixar": [
                    "https://www.youtube.com/embed/0mvM6p5oQ9A",
                    "https://www.youtube.com/embed/6Qe6p6p6p6A",
                    "https://www.youtube.com/embed/7Qe7p7p7p7A"
                ],
                "Pororo": [
                    "https://www.youtube.com/embed/8Qe8p8p8p8A",
                    "https://www.youtube.com/embed/9Qe9p9p9p9A",
                    "https://www.youtube.com/embed/0Qe0p0p0p0A"
                ],
                "기타": []
            }
            yt_videos = yt_samples.get(q, [])
            if yt_videos:
                for url in yt_videos:
                    st.video(url)
            else:
                st.markdown(f"[유튜브에서 '{q}' 영상 더 보기]({yt_search_url})")

            if do_rag:
                messages = build_rag_prompt(q, results)
                rag = aoai_chat(messages)
                if rag:
                    with st.container(border=True):
                        st.success("RAG 요약 생성됨")
                        st.markdown("**Child-friendly Summary**")
                        st.write(rag.get("summary",""))
                        st.markdown("**Focus Phrases**")
                        st.write(", ".join(rag.get("focus_phrases", [])))
                        st.markdown("**Missions (3)**")
                        for m in rag.get("missions", []):
                            st.write("- " + m)
                        st.markdown("**Parent Tips**")
                        for t in rag.get("parent_tips", []):
                            st.write("- " + t)
                        st.download_button("다운로드: RAG 결과(JSON)",
                                           data=json.dumps(rag, ensure_ascii=False, indent=2),
                                           file_name="rag_result.json",
                                           mime="application/json")
# ...existing code...

# --- Plan tab ---
with tabs[1]:
    st.subheader("주간 계획 생성 (룰 기반)")
    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.number_input("나이(age)", 3, 12, 7, step=1)
    with col2:
        level = st.selectbox("레벨(CEFR, 간이)", ["A0","A1","A2","B1"], index=1)
    with col3:
        character = st.selectbox("선호 캐릭터", ["Bluey","Peppa Pig","Disney/Pixar","Others"], index=0)
    sessions = st.slider("주간 학습 횟수", 2, 7, 4)
    minutes = st.slider("회당 분량(분)", 10, 30, 15)
    if st.button("계획 만들기", use_container_width=True):
        plan = rule_based_plan(age, level, character, sessions, minutes)
        st.success("주간 계획이 생성되었습니다.")
        for act in plan["activities"]:
            with st.container(border=True):
                st.markdown(f"**{act['day']}** — {act['item']} ({act['type']})")
                st.write("키 프레이즈:", ", ".join(act["focus_phrases"]))
                st.write("미션:", ", ".join(act["missions"]))
        st.download_button("다운로드: 주간 계획 JSON",
                           data=json.dumps(plan, ensure_ascii=False, indent=2),
                           file_name="week_plan.json",
                           mime="application/json")

# --- Settings tab ---
with tabs[2]:
    st.subheader("환경 상태")
    st.write("Search endpoint:", SEARCH_ENDPOINT or "❌ 미설정")
    st.write("Index:", SEARCH_INDEX or "❌ 미설정")
    st.write("AOAI endpoint:", AOAI_ENDPOINT or "—")
    st.write("AOAI deployment:", AOAI_DEPLOYMENT or "—")

st.caption("Powered by Azure AI Search + Streamlit")