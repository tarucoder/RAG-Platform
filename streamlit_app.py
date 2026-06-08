import streamlit as st
import time
import re
from pathlib import Path

# Add project root to path (in case it's run from subfolders)
import sys
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.infrastructure.logger import logger

# Import detect_pii directly to avoid triggering api.py's module-level Generator() instantiation
# which would lock the VectorStore singleton before Streamlit's cached version can initialize
import re as _re_pii
def detect_pii(text: str) -> bool:
    """Scans query text to block sensitive PII (Aadhaar, PAN, Card, Phone, Email)."""
    aadhaar_pattern = r'\b\d{4}[ -]?\d{4}[ -]?\d{4}\b'
    pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
    phone_pattern = r'\b(?:\+91|91)?[6-9]\d{9}\b'
    card_pattern = r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b'
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    text_upper = text.upper()
    return bool(
        _re_pii.search(aadhaar_pattern, text) or
        _re_pii.search(pan_pattern, text_upper) or
        _re_pii.search(phone_pattern, text) or
        _re_pii.search(card_pattern, text) or
        _re_pii.search(email_pattern, text)
    )

# 1. Page Configuration
st.set_page_config(
    page_title="Groww Mutual Fund FAQ Assistant",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. Sleek Custom Styling (Dark Mode & Premium Typography)
st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Elegant Sidebar */
    .stSidebar {
        background-color: #0E1117;
        border-right: 1px solid #1E293B;
    }
    
    /* Chat Bubble Enhancements */
    .user-bubble {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border-radius: 18px 18px 2px 18px;
        padding: 12px 16px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
    }
    
    .ai-bubble {
        background: #1E293B;
        color: #E2E8F0;
        border: 1px solid #334155;
        border-radius: 18px 18px 18px 2px;
        padding: 12px 16px;
        margin-bottom: 5px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Badge styling */
    .meta-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(15, 118, 110, 0.15);
        color: #2DD4BF;
        border: 1px solid rgba(45, 212, 191, 0.3);
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 2px 8px;
        margin-right: 8px;
        margin-top: 5px;
    }
    
    .source-link {
        display: inline-flex;
        align-items: center;
        color: #38BDF8 !important;
        font-size: 0.8rem;
        font-weight: 600;
        text-decoration: none !important;
        margin-top: 5px;
        transition: color 0.2s ease;
    }
    .source-link:hover {
        color: #7DD3FC !important;
    }
    
    /* Suggestion Chips Style */
    .suggestion-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
        margin-bottom: 25px;
    }
    
    /* Compliance block */
    .compliance-warning {
        background: rgba(239, 68, 68, 0.1) !important;
        color: #F87171 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/combo-chart.png", width=64)
    st.title("FAQ Companion")
    st.markdown("---")
    
    st.subheader("💡 Knowledge Base")
    st.write(
        "Powered by a facts-only retrieval-augmented generation (RAG) pipeline whitelisted over "
        "**34 target Groww mutual fund schemes**."
    )
    
    st.subheader("🛡️ Compliance Guardrails")
    st.info(
        "• Strict maximum 3-sentence responses\n"
        "• Mandatory official document citations\n"
        "• Automatic PII scanning (Aadhaar, PAN, Card details, Phone, Emails)"
    )
    
    st.subheader("⏱️ Ingestion Schedule")
    st.success("Daily cron update executed via GitHub Actions workflow.")
    
    # Diagnostic: Show vector store status
    st.markdown("---")
    st.subheader("🔍 System Diagnostics")
    try:
        from src.data.vector_store import VectorStore
        vs = VectorStore.get_instance()
        chunk_count = len(vs.collection.data) if hasattr(vs.collection, 'data') else 'N/A (ChromaDB)'
        db_path = vs.persist_dir
        has_api_key = bool(vs.__class__.__module__)  # placeholder
        from src.infrastructure.config import Config
        has_api_key = bool(Config.GROQ_API_KEY)
        st.metric("Indexed Chunks", chunk_count)
        st.caption(f"DB Path: `{db_path}`")
        st.caption(f"Fallback Mode: `{vs.use_fallback}`")
        st.caption(f"API Key Present: `{has_api_key}`")
    except Exception as diag_e:
        st.error(f"Diagnostics failed: {diag_e}")
    
    st.markdown("---")
    st.caption("© 2026 Groww Assistant. Built for SEBI compliance.")

# 4. Main Section Header
st.title("📈 Groww Mutual Fund FAQ Assistant")
st.write("Ask questions about NAVs, exit loads, risk ratings, and parameters of Groww Mutual Funds.")

# 5. Initialize RAG Generator (Cached to prevent reload overhead)
# NOTE: Do NOT reset VectorStore._instance here — it causes data loss if tests
# have poisoned the singleton, and forces re-initialization which can lose data.

@st.cache_resource
def get_generator():
    from src.data.vector_store import VectorStore
    from src.RAG.generator import Generator
    
    # Ensure we always start from a fresh singleton pointing at the production DB
    VectorStore._instance = None
    gen = Generator()
    
    # Log diagnostic info
    vs = gen.retriever.vector_store
    chunk_count = len(vs.collection.data) if hasattr(vs.collection, 'data') else 'unknown'
    logger.info(f"Streamlit Generator initialized. VectorStore has {chunk_count} chunks. Fallback={vs.use_fallback}. Mock={gen.use_mock}")
    return gen

try:
    generator = get_generator()
except Exception as e:
    st.error(f"Failed to load retrieval model: {e}")
    logger.error(f"Streamlit Generator loading failure: {e}")
    generator = None

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# 6. Suggestion Chips Logic
suggestions = [
    "What is the exit load of Groww Large Cap Fund?",
    "What is the statutory lock-in for Groww ELSS Tax Saver?",
    "Show me the fund managers for Groww Value Fund.",
    "What is the objective of Groww Aggressive Hybrid Fund?"
]

# Display suggestion chips only if chat history is empty
if len(st.session_state.messages) == 0:
    st.write("👋 Try asking one of these suggested questions:")
    cols = st.columns(2)
    for idx, suggestion in enumerate(suggestions):
        with cols[idx % 2]:
            if st.button(suggestion, use_container_width=True, key=f"sug_{idx}"):
                # Trigger sending message
                st.session_state.temp_input = suggestion

# 7. Render Chat History
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-bubble">🧑‍💻 <b>You:</b><br>{msg["content"]}</div>',
            unsafe_allow_html=True
        )
    elif msg["role"] == "ai":
        badge_html = ""
        if "source" in msg:
            badge_html += f'<a href="{msg["source"]}" target="_blank" rel="noopener" class="source-link">🔗 Official Document</a>'
            
        st.markdown(
            f'<div class="ai-bubble">🤖 <b>Assistant:</b><br>{msg["content"]}<br>{badge_html}</div>',
            unsafe_allow_html=True
        )
    elif msg["role"] == "error":
        st.markdown(
            f'<div class="compliance-warning">⚠️ <b>Compliance Warning:</b><br>{msg["content"]}</div>',
            unsafe_allow_html=True
        )

# 8. Handling User Input (Chat Input or Clicked Suggestion)
user_query = st.chat_input("Ask a question about mutual funds...")

# If suggestion chip clicked, fetch from session state
if "temp_input" in st.session_state and st.session_state.temp_input:
    user_query = st.session_state.temp_input
    st.session_state.temp_input = None  # Clear

if user_query:
    # Render user query immediately
    st.markdown(
        f'<div class="user-bubble">🧑‍💻 <b>You:</b><br>{user_query}</div>',
        unsafe_allow_html=True
    )
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    # 9. PII Guardrail Scanning
    if detect_pii(user_query):
        err_msg = "For your security, please do not share account numbers, PAN cards, Aadhaar, or contact info in your queries."
        st.markdown(
            f'<div class="compliance-warning">⚠️ <b>Compliance Warning:</b><br>{err_msg}</div>',
            unsafe_allow_html=True
        )
        st.session_state.messages.append({"role": "error", "content": err_msg})
    else:
        # 10. Generate RAG Response
        if not generator:
            st.error("RAG generator engine offline.")
        else:
            with st.spinner("Retrieving verified facts and generating compliant response..."):
                try:
                    response = generator.generate(user_query)
                    
                    answer = response.get("answer", "I don't have that information.")
                    source = response.get("source", "https://groww.in")
                    
                    # Convert markdown links to HTML links for cleaner streamlit display
                    formatted_answer = re.sub(
                        r'\[([^\]]+)\]\((https?://[^\s)]+)\)',
                        r'<a href="\2" target="_blank" rel="noopener" class="source-link">\1</a>',
                        answer
                    )
                    
                    badge_html = f'<a href="{source}" target="_blank" rel="noopener" class="source-link">🔗 Official Document</a>'
                    
                    st.markdown(
                        f'<div class="ai-bubble">🤖 <b>Assistant:</b><br>{formatted_answer}<br>{badge_html}</div>',
                        unsafe_allow_html=True
                    )
                    
                    st.session_state.messages.append({
                        "role": "ai",
                        "content": formatted_answer,
                        "source": source
                    })
                except Exception as e:
                    st.error(f"Error generating response: {e}")
                    logger.error(f"Streamlit chat query failure: {e}")
                    
    # Force streamlit rerun to display updated chat immediately
    st.rerun()
