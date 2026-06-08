# Phase-Wise Implementation Plan: Mutual Fund FAQ Assistant (RAG Pipeline)

This implementation plan breaks down the development of the **Mutual Fund FAQ Assistant** into **7 phases**, designed to go from environment setup to a fully production-ready, compliant RAG application.

---

## 📅 Roadmap Overview

```
Phase 1: Bootstrap  ──▶  Phase 2: Scraper  ──▶  Phase 3: Vector DB & Embeddings
(Weeks 1 - Scaffolding)   (Crawl & Clean Text)      (Local Chroma persistent store)
                                                           │
Phase 5: Frontend & API ◀──  Phase 4: Retrieval  ◀─────────┘
(Sleek UI, PII filters)      (RAG & Groq LLM API)
       │
       ▼
Phase 6: Testing & E2E  ──▶  Phase 7: Daily Scheduler
(Compliance verification)     (Automated daily updates)
```

---

## 🛠️ Detailed Phase Breakdown

### Phase 1: Project Bootstrap & Environment Setup
**Target Timeline**: 1–2 Days  
**Goal**: Scaffold the folder architecture, configure development tools, and verify environmental sanity.

#### Tasks:
* **Task 1.1**: Create project directories according to the mapping specified in `architecture.md`.
* **Task 1.2**: Initialize python virtual environment (`venv/`) and write `requirements.txt`.
* **Task 1.3**: Configure the environment manager (`src/infrastructure/config.py`) to parse `.env` files.
* **Task 1.4**: Establish logging configurations (`src/infrastructure/logger.py`) to output structured execution logs.
* **Task 1.5**: Set up custom domain exceptions (`src/infrastructure/exceptions.py`) for handling API errors, scraping blocks, and validation failures.

#### Deliverables:
* Scaffolded Python workspace.
* `requirements.txt` with all target versions (`ChromaDB`, `groq`, `beautifulsoup4`, `markdownify`, `APScheduler`).
* Verified configuration loading from `.env` parameters.

---

### Phase 2: Ingestion & Text Processing Layer (Offline)
**Target Timeline**: 3 Days  
**Goal**: Crawl the designated 34 mutual fund URLs and parse high-density text, stripping out webpage boilerplate.

#### Tasks:
* **Task 2.1**: Implement Scraper (`src/data/crawler.py`) capable of executing clean `HTTP GET` operations with random user-agent emulation to fetch the 34 URLs.
* **Task 2.2**: Write HTML Cleaner (`src/data/parser.py`) using `BeautifulSoup` and `Markdownify` to remove boilerplate tags (`<nav>`, `<footer>`, `<script>`, advertising links).
* **Task 2.3**: Implement Text Chunker inside `parser.py` using a Recursive Character Text Splitter (target size: **800 characters**, overlap: **150 characters**).

#### Verification:
* Run unit tests confirming that scraped HTML pages are output as raw cleaned text files in `data/processed/`.
* Confirm that paragraphs and scheme specifications tables are chunked properly without losing logical coherence.

---

### Phase 3: Embedding & Local Vector Database Indexing (Offline)
**Target Timeline**: 3 Days  
**Goal**: Generate vector embeddings for text chunks and initialize a local, persistent Vector DB.

#### Tasks:
* **Task 3.1**: Initialize ChromaDB client in `src/data/vector_store.py`.
* **Task 3.2**: Configure the embedding generator using `BAAI/bge-small-en-v1.5` (384 dimensions).
* **Task 3.3**: Write the indexing script to parse processed text files, embed chunks, and persist the database index in `data/vector_db/`.

#### Verification:
* Run simple vector search queries inside a shell command to ensure correct Approximate Nearest Neighbor (ANN) matches:
  ```bash
  python -c "from src.data.vector_store import VectorStore; print(VectorStore.query('what is ELSS lock-in?'))"
  ```
* Verify database folder size and persistence on disk.

---

### Phase 4: Retrieval Engine & LLM Execution Pipeline (Online)
**Target Timeline**: 4 Days  
**Goal**: Implement the core RAG execution loop combining retrieved contexts, guardrails, and Groq-powered completions.

#### Tasks:
* **Task 4.1**: Implement Query Vectorizer and Retriever (`src/RAG/retriever.py`) to query the vector database and retrieve top-K (K=3) matching context chunks.
* **Task 4.2**: Draft the strict prompt template in `src/RAG/prompt_engine.py` incorporating system instructions, contextual rules, and compliance guardrails.
* **Task 4.3**: Set up Groq LLM API Client (`src/RAG/generator.py`) using `llama-3.3-70b-versatile` to process prompts and yield completions.
* **Task 4.4**: Write the compliance validator parser: intercepts raw LLM outputs to verify sentence length constraints (max 3 sentences), exactly one citation link, and footer presence.

#### Prompt Engineering & Guardrails Blueprint:
```markdown
System Prompt:
"You are a compliant Mutual Fund FAQ Assistant for Groww. Your task is to answer user queries using ONLY the retrieved context. 
Rules:
- Speak strictly objectively. Never recommend any scheme or offer financial advice.
- Limit answers to a maximum of 3 sentences.
- Cite exactly one official source link from the context metadata.
- If the answer cannot be found in the context, politely refuse (say: 'I don't have that information in my verified sources') and provide a general SEBI link."
```

#### Verification:
* Run unit tests verifying semantic search logic, similarity thresholds, and compliance outputs.

---

### Phase 5: REST API Gateway & Web Interface (Presentation)
**Target Timeline**: 4 Days  
**Goal**: Build a secure Python REST API and a premium, responsive glassmorphic single-page client.

#### Tasks:
* **Task 5.1**: Implement API Gateway endpoints in `src/presentation/api.py` (Flask/FastAPI) including `POST /api/chat`, `GET /api/health`, and CORS configurations.
* **Task 5.2**: Integrate gateway input sanitization filters to scrub credit cards, PAN, Aadhaar numbers, and phone numbers.
* **Task 5.3**: Scaffold the HTML5 structure in `src/presentation/web/index.html` with visible disclaimer banners: *"Facts-only. No investment advice."*
* **Task 5.4**: Style the interface in `src/presentation/web/style.css` using modern premium palettes (HSL colors, dark mode toggles, subtle box shadows, hover zoom states, and loading keyframes).
* **Task 5.5**: Implement client-side JavaScript in `src/presentation/web/app.js` to manage chat history state, loading displays, and result rendering cards.

---

### Phase 6: Verification, Compliance Testing & Launch
**Target Timeline**: 3 Days  
**Goal**: Run end-to-end integration tests, sanity checks, and verify perfect formatting compliance.

#### Tasks:
* **Task 6.1**: Write automated unit tests for chunking logic, PII filters, and citation parsers.
* **Task 6.2**: Perform mock query evaluations against the 34-link corpus to measure retrieval accuracy.
* **Task 6.3**: Test compliance guardrails by entering malicious prompts (e.g., *"Which scheme is better?"*, *"What is my PAN?"*) and checking for correct refusal handling.
* **Task 6.4**: Final walkthrough and document deployment instructions in `README.md`.

---

### Phase 7: Daily Ingestion Scheduler Component (Offline)
**Target Timeline**: 2 Days  
**Goal**: Set up automated, daily background indexing to keep fund manager information and NAV metrics updated.

#### Tasks:
* **Task 7.1**: Implement the daily background scheduler in `src/data/scheduler.py` using `APScheduler` or native cron trigger.
* **Task 7.2**: Implement checksum/diff matching logic: when crawling, calculate hash of fetched page and compare it to previous versions to skip indexing unmodified URLs.
* **Task 7.3**: Integrate logging within the scheduler to report index update logs (number of new chunks added, updated, or purged).

#### Verification:
* Configure scheduler to run on a 1-minute interval for local sanity checks; verify crawl trigger, hash parsing, and vector DB update flow without duplicate embeddings.

---

## 📈 Success Criteria & Validation Matrix

| Target Metric | Measurement Method | Success Threshold |
| :--- | :--- | :--- |
| **Scraping Density** | Count of URLs loaded vs parsed text chunks | 100% of the 34 URLs successfully scraped and indexed |
| **Response Clarity** | Text parser length split | 100% of LLM replies are $\le$ 3 sentences |
| **Citation Precision** | Regex match on output | 100% of factual answers include exactly one valid citation link |
| **Advisory Refusal** | Evaluator query testing | 100% of investment recommendations are gracefully refused |
| **PII Data Security** | Security probe query injection | Zero PII data accepted or forwarded to DB/LLM |
