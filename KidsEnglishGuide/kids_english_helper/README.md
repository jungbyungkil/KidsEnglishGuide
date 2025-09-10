# Kids English Helper (MVP) — Azure AI Search + Streamlit

## 기능
- **Search 탭**: Azure AI Search 인덱스에서 문서 검색
- **Plan 탭**: 나이·레벨·선호 기반 주간 계획(룰 기반)
- (선택) Azure OpenAI 연동 시, Search 결과로 **RAG 요약/미션/부모팁** 생성

## 설정
`.streamlit/secrets.toml` 또는 환경변수에 값 지정:

```toml
AZURE_SEARCH_ENDPOINT = "https://<your-search>.search.windows.net"
AZURE_SEARCH_KEY     = "<search-key>"
AZURE_SEARCH_INDEX   = "kids-english-index"

# Optional for RAG
AZURE_OPENAI_ENDPOINT = "https://<your-aoai>.openai.azure.com"
AZURE_OPENAI_KEY = "<aoai-key>"
AZURE_OPENAI_DEPLOYMENT = "<gpt-4o-mini>"