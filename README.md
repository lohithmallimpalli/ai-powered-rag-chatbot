# DocuIntel AI — Enterprise Document Intelligence RAG Platform

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.114-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-red.svg)](https://www.trychroma.com/)
[![LangChain](https://img.shields.io/badge/Orchestration-LangChain-orange.svg)](https://www.langchain.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, full-stack **Retrieval-Augmented Generation (RAG)** application designed for high-accuracy document intelligence, strict anti-hallucination factual grounding, and verifiable citation tracking.

Built with **FastAPI**, **LangChain**, **ChromaDB**, **Sentence-Transformers**, and native support for both **Google Gemini** and **OpenAI**.

---

## 📑 Table of Contents

1. [Project Overview](#-project-overview)
2. [Key Features](#-key-features)
3. [Technology Stack](#-technology-stack)
4. [System Architecture & RAG Pipeline](#-system-architecture--rag-pipeline)
5. [Project Structure](#-project-structure)
6. [Prerequisites & Quick Start](#-prerequisites--quick-start)
7. [Environment Configuration](#-environment-configuration)
8. [Running the Application](#-running-the-application)
9. [Automated Test Suite](#-automated-test-suite)
10. [REST API Documentation](#-rest-api-documentation)
11. [Deployment Guide (Render, Railway, Docker)](#-deployment-guide)
12. [Sample Documents & Testing Guide](#-sample-documents--testing-guide)
13. [Security & Production Hardening](#-security--production-hardening)
14. [Future Enhancements](#-future-enhancements)

---

## 🎯 Project Overview

Conventional chatbots generate answers based on static pretraining weights, resulting in hallucinations, outdated facts, and zero provenance. 

**DocuIntel AI** solves this by implementing an end-to-end deterministic RAG architecture:
- Users ingest enterprise files (**PDF**, **DOCX**, **TXT**).
- The system cleans, splits, and embeds document chunks into a persistent vector database (**ChromaDB** using **HNSW cosine indexing**).
- User queries trigger semantic similarity searches. Only top-ranked chunks meeting relevance thresholds are passed to the LLM.
- An advanced, few-shot prompt with strict refusal instructions guarantees that the LLM generates answers strictly from verified document chunks and provides verifiable citations (document name, page number, relevance score, and source excerpt).

---

## ✨ Key Features

- **Multi-Format Document Parsing**: Full extraction pipeline for `.pdf` (with page tracking via PyPDF), `.docx` (including tables and headings), and `.txt` (with multi-encoding fallback).
- **Persistent Vector Store**: Managed ChromaDB collection with persistent storage on disk and cosine similarity ranking.
- **Offline / Local Vector Embeddings**: Uses `sentence-transformers/all-MiniLM-L6-v2` locally — free, fast, and 100% immune to embedding API rate limits or quota errors.
- **Configurable Multi-LLM Support**: Seamlessly switch between **Google Gemini** (`gemini-1.5-flash`, `gemini-1.5-pro`) and **OpenAI** (`gpt-4o`, `gpt-4o-mini`) via `.env` or the live UI Settings modal.
- **Strict Hallucination Prevention & Refusal**: When context is absent or irrelevant, the model explicitly responds:
  > *"I couldn't find this information in the uploaded documents. Please upload a relevant document or ask a question related to the available knowledge base."*
- **Clickable Source Provenance & Inspection**: Every generated answer displays its source file, page number, similarity match percentage, and context snippet.
- **Duplicate Upload Prevention**: Detects existing document names and prevents vector database pollution.
- **Document Management**: Real-time listing of indexed files, chunk counts, page counts, human-readable file sizes, and single-click deletion.
- **Multi-Turn Conversational Memory**: Maintains session-aware chat history while strictly prioritizing fresh document context.
- **Premium 3-Panel Dark Dashboard**: Built with glassmorphism, responsive collapsible sidebars, copy-to-clipboard buttons, live progress tracking, and toast notifications.

---

## 🛠 Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Framework** | Python 3.12+, FastAPI, Uvicorn, Gunicorn |
| **RAG Orchestration** | LangChain Core, LangChain Community, LangChain Text Splitters |
| **Vector Database** | ChromaDB (HNSW Index with Cosine Metric) |
| **Embedding Engine** | Sentence-Transformers (`all-MiniLM-L6-v2`, 384 dimensions) |
| **Document Parsers** | PyPDF (PDF with page metadata), python-docx (DOCX & Tables), ReportLab |
| **LLM Inference** | Google Generative AI (Gemini 1.5 Flash/Pro), OpenAI API (GPT-4o/mini) |
| **Frontend UI/UX** | HTML5, Modern CSS3 (Dark Navy Glassmorphism), Vanilla JavaScript (ES6+), Marked.js, FontAwesome |
| **Configuration** | Pydantic v2 Settings, python-dotenv |
| **Testing** | Pytest, Pytest-Asyncio, HTTPX / TestClient |

---

## 🏛 System Architecture & RAG Pipeline

```
                                      ┌─────────────────────────────────┐
                                      │   Client Web Dashboard (HTML5)  │
                                      └────────────────┬────────────────┘
                                                       │ HTTP / JSON
                                                       ▼
                                      ┌─────────────────────────────────┐
                                      │    FastAPI Application Layer    │
                                      │        (app/main.py)            │
                                      └───────┬─────────────────┬───────┘
                                              │                 │
                   ┌──────────────────────────┘                 └─────────────────────────┐
                   │ Document Ingestion                                                   │ Conversational RAG Query
                   ▼                                                                      ▼
        ┌───────────────────────┐                                              ┌───────────────────────┐
        │   DocumentLoader      │                                              │      RAGPipeline      │
        │  (PDF / DOCX / TXT)   │                                              │   (app/core/rag.py)   │
        └──────────┬────────────┘                                              └──────────┬────────────┘
                   │ Clean text & metadata                                                │
                   ▼                                                                      ▼
        ┌───────────────────────┐                                              ┌───────────────────────┐
        │   DocumentChunker     │                                              │ Similarity Search     │
        │ (Recursive Character) │                                              │ (Top-K Cosine Filter) │
        └──────────┬────────────┘                                              └──────────┬────────────┘
                   │ Chunks & page numbers                                                │
                   ▼                                                                      │ Retrieved chunks
        ┌───────────────────────┐                                                         │ with metadata
        │  SentenceTransformer  │                                                         │
        │   Embedding Engine    │                                                         ▼
        └──────────┬────────────┘                                              ┌───────────────────────┐
                   │ 384-d vectors                                             │ Prompt Synthesizer    │
                   ▼                                                           │  - Few-Shot System    │
        ┌───────────────────────┐                                              │  - Strict Grounding   │
        │   ChromaDB Persistent │ ◄────────────────────────────────────────────┤  - Refusal Mechanism  │
        │      Vector Store     │                                              └──────────┬────────────┘
        └───────────────────────┘                                                         │ Grounded prompt
                                                                                          ▼
                                                                               ┌───────────────────────┐
                                                                               │ Unified LLM Provider  │
                                                                               │ (Gemini 1.5 / GPT-4o) │
                                                                               └──────────┬────────────┘
                                                                                          │
                                                                                          ▼
                                                                               ┌───────────────────────┐
                                                                               │ Grounded Answer with  │
                                                                               │ Verifiable Citations  │
                                                                               └───────────────────────┘
```

---

## 📁 Project Structure

```
ai-powered-rag-chatbot/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Pydantic environment configuration & directory setup
│   ├── main.py                   # FastAPI routing, middleware, lifecycle & endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── document_loader.py    # Multi-format document parser (PDF, DOCX, TXT)
│   │   ├── text_splitter.py      # Recursive character chunker with metadata tracking
│   │   ├── vector_store.py       # Persistent ChromaDB client, embeddings & registry
│   │   ├── llm_provider.py       # Unified LLM provider (Google Gemini & OpenAI)
│   │   └── rag_chain.py          # RAG orchestration, prompt engineering & citation builder
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic request & response schemas
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css        # Enterprise dark-theme CSS & responsive layout
│   │   └── js/
│   │       └── app.js            # Frontend controller, drag-drop upload, chat & UI
│   └── templates/
│       └── index.html            # 3-panel dashboard (Sidebar, Main Chat, Document Inspector)
├── data/
│   ├── uploads/                  # Raw uploaded document storage
│   └── chroma_db/                # Persistent vector database files
├── sample_documents/             # Pre-built realistic test documents (PDF, DOCX, TXT)
│   ├── Global_AI_Security_Policy.txt
│   ├── Q3_Financial_Performance_Report.docx
│   └── Cloud_Architecture_and_SLA.pdf
├── scripts/
│   └── generate_sample_docs.py   # Script to regenerate multi-page test documents
├── tests/
│   ├── __init__.py
│   ├── test_document_processing.py # Unit tests for parsers, chunking & validation
│   ├── test_rag_pipeline.py      # Vector DB indexing, search & refusal tests
│   └── test_api_endpoints.py     # HTTP integration tests for all FastAPI endpoints
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git ignore rules for virtualenv, data, and cache
├── Dockerfile                    # Multi-stage production container build
├── Procfile                      # Process configuration for Render / Railway
├── railway.json                  # Railway deployment descriptor
├── render.yaml                   # Render deployment blueprint
├── requirements.txt              # Production Python package requirements
├── run.py                        # Standalone application entrypoint
└── README.md                     # Comprehensive documentation
```

---

## 🚀 Prerequisites & Quick Start

### 1. Prerequisites
- **Python 3.12+**
- Git
- A Google Gemini API Key ([Get here](https://aistudio.google.com/)) or an OpenAI API Key ([Get here](https://platform.openai.com/api-keys))

### 2. Clone Repository
```bash
git clone https://github.com/your-username/ai-powered-rag-chatbot.git
cd ai-powered-rag-chatbot
```

### 3. Create & Activate Virtual Environment
```bash
python3.12 -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the project root by copying `.env.example`:

```bash
cp .env.example .env
```

Configure your credentials in `.env`:

```ini
# ==============================================================================
# DOCUINTEL AI - ENVIRONMENT CONFIGURATION
# ==============================================================================

# Active LLM Provider: "gemini" or "openai"
LLM_PROVIDER=gemini

# Google Gemini API Key (https://aistudio.google.com/)
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# OpenAI API Key (https://platform.openai.com/api-keys)
OPENAI_API_KEY=your_actual_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Embeddings (Local Sentence-Transformers runs on CPU/GPU, offline & 0 quota needed)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# RAG Hyperparameters
CHUNK_SIZE=800
CHUNK_OVERLAP=150
TOP_K_RETRIEVAL=4
SIMILARITY_THRESHOLD=0.25

# Server & Network Settings
HOST=0.0.0.0
PORT=8000
DEBUG=True
MAX_UPLOAD_SIZE_MB=25
```

> **Note**: Even without an API key configured at boot, the application starts gracefully. You can enter or update your API key directly inside the web UI by clicking **Settings** in the bottom-left sidebar.

---

## 💻 Running the Application

### Method 1: Using the Runner Script
```bash
python run.py
```

### Method 2: Using Uvicorn Directly
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: Using Gunicorn (Production Mode)
```bash
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Once running, navigate to:
- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Redoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Automated Test Suite

The project includes 14 comprehensive unit and integration tests covering document extraction, chunking, metadata propagation, ChromaDB indexing, semantic search, refusal logic, and API endpoints.

Execute the test suite with:

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_api_endpoints.py::test_health_endpoint PASSED                 [  7%]
tests/test_api_endpoints.py::test_api_health_endpoint PASSED             [ 14%]
tests/test_api_endpoints.py::test_stats_endpoint PASSED                  [ 21%]
tests/test_api_endpoints.py::test_upload_invalid_file_extension PASSED   [ 28%]
tests/test_api_endpoints.py::test_upload_and_delete_document_workflow PASSED [ 35%]
tests/test_api_endpoints.py::test_chat_without_api_key_returns_informative_error PASSED [ 42%]
tests/test_api_endpoints.py::test_settings_update PASSED                 [ 50%]
tests/test_document_processing.py::test_file_validator PASSED            [ 57%]
tests/test_document_processing.py::test_txt_extraction PASSED            [ 64%]
tests/test_document_processing.py::test_docx_extraction PASSED           [ 71%]
tests/test_document_processing.py::test_pdf_extraction_and_pages PASSED  [ 78%]
tests/test_document_processing.py::test_text_chunking_with_metadata PASSED [ 85%]
tests/test_rag_pipeline.py::test_vector_store_indexing_and_search PASSED [ 92%]
tests/test_rag_pipeline.py::test_rag_pipeline_empty_knowledge_base PASSED [100%]

======================= 14 passed in 2.86s =======================
```

---

## 🔌 REST API Documentation

| Method | Endpoint | Description | Request Body / Params |
|---|---|---|---|
| `GET` | `/` | Web Dashboard UI | — |
| `POST` | `/api/upload` | Upload & index file (`.pdf`, `.docx`, `.txt`) | `multipart/form-data` with `file` |
| `GET` | `/api/documents` | List all indexed documents with metrics | — |
| `DELETE` | `/api/documents/{doc_id}` | Remove document and its vectors from ChromaDB | `doc_id` path param |
| `POST` | `/api/chat` | Query RAG pipeline and receive grounded answer | `{"message": str, "session_id": str}` |
| `GET` | `/api/history` | Retrieve conversation history for session | `?session_id=default` |
| `DELETE` | `/api/history` | Clear conversation history for session | `?session_id=default` |
| `GET` | `/api/health` | System health, vector stats, provider status | — |
| `GET` | `/api/stats` | Vector DB chunk and document statistics | — |
| `POST` | `/api/settings` | Update LLM provider, API key, model dynamically | `{"provider": str, "api_key": str, "model": str}` |

---

## 🚢 Deployment Guide

### Option 1: Deploy to Railway

1. Push your repository to GitHub.
2. Sign in to [Railway](https://railway.app/) and click **New Project** > **Deploy from GitHub repo**.
3. Select your repository. Railway automatically reads `railway.json` and `Procfile`.
4. In your Railway service settings under **Variables**, add:
   - `GEMINI_API_KEY`: Your Gemini API Key
   - `LLM_PROVIDER`: `gemini`
   - `PORT`: `8000`
5. Click **Deploy**. Railway will build the application and provide a live public URL.

### Option 2: Deploy to Render

1. Fork or push this repository to GitHub.
2. Log in to [Render](https://render.com/) and click **New** > **Blueprint**.
3. Connect your repository. Render automatically reads `render.yaml`.
4. Fill in the secret `GEMINI_API_KEY` in the Render dashboard.
5. A persistent disk (`docuintel-data`) is provisioned to keep uploaded files and ChromaDB vectors across deploys.

### Option 3: Deploy with Docker

Build and run using Docker:

```bash
# Build Docker image
docker build -t docuintel-rag:latest .

# Run container with environment file and persistent volume
docker run -d \
  --name docuintel-rag \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  docuintel-rag:latest
```

Open [http://localhost:8000](http://localhost:8000) to access the service.

---

## 📂 Sample Documents & Testing Guide

Three realistic sample documents are included in `sample_documents/`:

1. **`Global_AI_Security_Policy.txt`**:
   - Covers enterprise AI governance, role-based access control, password requirements (14 characters, 90-day rotation), and incident response.
   - *Sample Query*: `"What is the company password policy and is MFA required?"`

2. **`Q3_Financial_Performance_Report.docx`**:
   - Covers Apex Global Enterprises Q3 revenue ($142.8M, +28% YoY), segment revenue breakdowns, operating margin (+420 bps to 24.6%), and Q4 guidance.
   - *Sample Query*: `"What was the enterprise software segment revenue and YoY growth in Q3?"`

3. **`Cloud_Architecture_and_SLA.pdf` (3 Pages)**:
   - Page 1: Cloudflare ingress, Kubernetes autoscaling, persistent storage.
   - Page 2: Service Level Agreement (99.95% uptime), service credit brackets, incident severity levels (Severity 1: 15-minute response).
   - Page 3: Disaster recovery guarantee (RTO: 30 minutes, RPO: 5 minutes) and AES-256 encryption.
   - *Sample Query*: `"What is the Disaster Recovery Recovery Time Objective (RTO) and Recovery Point Objective (RPO)?"`
   - *Hallucination Test Query*: `"Who won the 2022 World Cup?"` -> Returns the refusal message.

---

## 🔒 Security & Production Hardening

- **Zero API Key Leakage**: API keys are never rendered in client HTML or JavaScript bundles.
- **Strict File Type Whitelisting**: Only `.pdf`, `.docx`, and `.txt` MIME types and extensions are accepted.
- **Payload Size Caps**: Uploads are restricted to 25MB to prevent memory exhaustion.
- **Text Decontamination**: Extracted text strips binary null bytes, unprintable control characters, and malformed UTF-8 sequences.
- **Duplicate Prevention**: Files are checked against the metadata registry to eliminate duplicate indexing overhead.
- **Safe Environment Fallback**: If an API key is missing or expires, the system returns descriptive HTTP 401/429 diagnostics rather than crashing.

---

## 🔮 Future Enhancements

- [ ] **Hybrid Search**: Combine BM25 keyword search with dense HNSW vector search using Reciprocal Rank Fusion (RRF).
- [ ] **Hierarchical Multi-Document Cross-Referencing**: Support graph-based relationships between related contracts and reports.
- [ ] **OCR Engine**: Integrate Tesseract or AWS Textract for scanned image-only PDFs.
- [ ] **Streaming Responses (SSE)**: Enable token-by-token streaming to the UI.
- [ ] **Multi-User RBAC**: Add OAuth2/JWT authentication to partition vector collections per enterprise organization.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
