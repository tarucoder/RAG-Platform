# Groww Mutual Fund FAQ Assistant (RAG Pipeline)

A compliant, secure, facts-only financial Q&A conversational assistant powered by a local Retrieval-Augmented Generation (RAG) pipeline and the Groq LLM API. 

The assistant answers questions about 34 mutual fund schemes using ONLY official Groww and platform scheme details under strict regulatory formatting constraints.

---

## 🏛️ System Architecture

The project is structured with modular separation of concerns:
1. **Ingestion & Text Processing (Offline)**: Crawls the 34 scheme URLs, cleans webpage boilerplate using BeautifulSoup + Markdownify, chunks content recursively, and preserves markdown tables intact.
2. **Vector Indexing & Local Storage (Offline)**: Computes unit vector embeddings and stores them. Includes an **interpreter-safe fallback** using scikit-learn's `HashingVectorizer` and a custom pure-Python `LocalVectorDB` to prevent PyTorch/ChromaDB dynamic link library (DLL) crashes on Windows + Python 3.14+.
3. **Retrieval & Compliance Generation (Online)**: Intercepts user queries, retrieves top-3 matching context blocks using a similarity threshold filter ($> 0.30$), formats strict compliance instructions, and runs Groq completions (using `llama-3.3-70b-versatile`) with a local keyword-matching mock engine fallback.
4. **API Gateway & Glassmorphic UI**: Serves static client pages and coordinates chat REST APIs using FastAPI, integrating regex PII filters to drop sensitive queries at the gateway.

---

## 🚫 Core Compliance & Security Guardrails

* **PII Security Gate**: Incoming questions are scanned for Aadhaar, PAN, Indian phone numbers, email addresses, and credit cards. Any match is blocked instantly at the API Gateway with a secure user message.
* **Anti-Hallucination & Refusal**: Out-of-domain queries or queries below the similarity threshold are refused with: *"I don't have that information in my verified sources"* and redirected to the official SEBI website.
* **Prose Limits**: Responses are strictly verified and truncated to a **maximum of 3 sentences**.
* **Strict Citations**: Every factual answer must contain **exactly one** markdown citation link to the official scheme page.
* **No Advisory**: The assistant refuses to provide subjective suggestions, comparisons, or advise on scheme performance returns.

---

## 📁 Repository Directory Layout

```
Milestone - 2 RAG/
├── Doc/
│   ├── problemstatement.md      # Project specifications
│   ├── architecture.md          # Visual pipeline architectures
│   └── implementation.md        # Roadmap phases definition
│
├── data/
│   ├── raw/                     # Cached crawled HTML files
│   ├── processed/               # Cleaned scheme text chunks in JSON
│   └── vector_db/               # Persistent database index
│
├── src/
│   ├── data/
│   │   ├── crawler.py           # Scraping/crawling mutual fund pages
│   │   ├── parser.py            # HTML boilerplate cleaning & splitting
│   │   ├── vector_store.py      # Embedding generation & index database
│   │   └── ingest_runner.py     # Main ingestion orchestrator
│   │
│   ├── RAG/
│   │   ├── retriever.py         # Cosine similarity context retrieval
│   │   ├── prompt_engine.py     # Compliant system prompt constructor
│   │   ├── generator.py         # LLM connector & output validator
│   │   └── evaluator.py         # Automated compliance evaluator runner
│   │
│   └── presentation/
│       ├── api.py               # REST API Gateway (FastAPI)
│       └── web/                 # Static web client (HTML/CSS/JS)
│
├── tests/                       # Unit and integration test suite
└── requirements.txt             # Project library dependencies
```

---

## 🚀 Getting Started (Setup & Run)

### 1. Environment Installation
Ensure Python 3.10+ is installed. Set up the virtual environment and install libraries:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configuration Setup
Create a `.env` file in the root directory (based on `.env.example`):
```ini
API_HOST=127.0.0.1
API_PORT=8000
DEBUG=True

LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile

EMBEDDING_MODEL=all-MiniLM-L6-v2
SIMILARITY_THRESHOLD=0.30
TOP_K_CONTEXT=3
```
*Note: If `GROQ_API_KEY` is left blank, the assistant automatically and gracefully operates in **Offline Mock Mode**, utilizing factual query sentence-matching so all compliance checks and UI elements remain fully testable.*

### 3. run the Ingestion & Index Pipeline (Offline)
Index the mutual fund corpus:
```bash
# Step A: Crawl the 34 URLs and parse HTML to processed text chunks
python -m src.data.ingest_runner

# Step B: Build/serialize the vector database embeddings index on disk
python -m src.data.vector_store
```
*Persistent database index is saved inside [data/vector_db/local_db.json](file:///c:/Users/tarunchoudhary/OneDrive%20-%20DCM%20SHRIRAM%20limited/Documents/My%20Study%20data/Milestone%20-%202%20RAG/data/vector_db/local_db.json).*

### 4. Run the REST API & Web Client
Start the FastAPI server:
```bash
python -m uvicorn src.presentation.api:app --host 127.0.0.1 --port 8000
```
Open your browser and visit: `http://localhost:8000`.

---

## 📈 Verification & Testing

### 1. Run Automated Unit Tests
Verify data parsing, retrieval thresholds, prompt logic, API gateways, and PII filters:
```bash
python -m unittest discover tests
```

### 2. Run Compliance Evaluator Runner
Verify retrieval accuracy and formatting compliance rates against a benchmark of 10 structured queries:
```bash
python src/RAG/evaluator.py
```
This prints a structured pass/fail matrix detailing **PII Leak safety block rate**, **Retrieval accuracy rate**, and **Formatting compliance rate**.
