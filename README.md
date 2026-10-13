# Filysis (Flysis-AlphaReports)

An intelligent, enterprise-grade document analysis, semantic chunking, and querying platform. Filysis processes complex PDF documents, extracting clean structured text, dense financial tables, visual figures, and hierarchical outlines. Powered by an **Intelligent Hybrid Extraction Subsystem (PyMuPDF + IBM Docling 2.x)**, PostgreSQL + `pgvector` vector storage, and interactive RAG chat powered by Sarvam AI.

---

## 🌟IBM Docling Hybrid Architecture

The document extraction pipeline has been upgraded with **IBM Docling 2.x** and an **Intelligent Hybrid Router**, delivering deep transformer-powered layout analysis, state-of-the-art table structure recognition, and genuine optical character recognition (OCR) while maintaining sub-second speeds for standard documents:

- **⚡ Intelligent Hybrid Routing**: A sub-second document profiler (`DocumentProfiler`) inspects incoming PDFs for character density, vector table lines, and column layouts. Clean, single-column documents are routed to the **Fast Track (PyMuPDF)** (<1s), while complex, scanned, or tabular documents are routed to the **Deep Neural Track (Docling)**.
- **📊 Deep Table Structure Recognition (`TableFormer`)**: Dense, borderless financial tables and complex multi-row header matrices are reconstructed with high fidelity via TableFormer neural networks (`TableFormerMode.ACCURATE` / `FAST`), exporting directly to pandas DataFrames and Markdown.
- **👁️ Native OCR for Scanned Documents (`RapidOCR`)**: Rasterized and scanned PDF pages are processed through integrated ONNX-accelerated OCR (`RapidOcrOptions`), extracting real text where traditional text scrapers yield empty results.
- **🧩 Structure-Aware Semantic Hybrid Chunking (`FlysisHybridChunker`)**: Powered by Docling's `HybridChunker` and Hugging Face tokenizers (`sentence-transformers/all-MiniLM-L6-v2`). Chunks preserve section heading hierarchies (`heading_path`), page numbers, and table cell integrity without splitting mid-sentence or mid-table.
- **🛡️ Fail-Safe Circuit Breaker**: If the deep neural engine encounters an unexpected memory pressure or processing error, the system automatically triggers an instant fallback to `FastPyMuPDFEngine`, ensuring zero pipeline downtime.
- **🚀 Pre-warmed Celery Workers**: Heavy neural models and tokenizers are pre-loaded into worker RAM on startup (`worker_process_init`), eliminating cold-start latencies.
- **🧹 Lean Dependency Footprint**: Replaced brittle legacy extractors (`camelot-py`, `pdfplumber`, `ghostscript`) with clean `docling`, `docling-core`, and `rapidocr-onnxruntime`.

---

## 🚀 Key Features

### 1. Hybrid PDF Extraction Engine
- **Document Profiler & Smart Routing**: Analyzes page density, table geometries, and column distributions to choose the optimal extraction tier. Supports manual override via `force_route="fast" | "docling"`.
- **Tier 1 (Fast Track — PyMuPDF)**: Ultra-fast text and native TOC extraction for simple digital PDFs.
- **Tier 2 (Deep Track — IBM Docling 2.x)**:
  - **`DocLayNet`**: Multimodal layout segmentation for multi-column reports, resolving reading flow and hierarchical section headers.
  - **`TableFormer`**: Deep table recognition handling spanning cells, borderless grids, and nested data.
  - **`RapidOCR`**: Real optical character recognition on scanned/image-heavy pages.
- **Circuit Breaker Fallback**: Automatic recovery to Fast Track if deep conversion fails.

### 2. Structure-Aware Semantic Chunking
- Contextualized chunking respecting heading breadcrumbs (`H1 > H2 > H3`), table cell boundaries, and token budgets (`DOCLING_MAX_TOKENS`).
- Generates durable, canonical JSON extraction artifacts (`pdf-information/{python_doc_id}_data.json`) containing `text_blocks`, `tables`, `chunks_advanced`, `outline`, `markdown`, and routing metadata.

### 3. Vector Search & RAG Pipeline
- Stores chunk embeddings natively in PostgreSQL using `pgvector` and `sentence-transformers` (`all-MiniLM-L6-v2`).
- Hybrid search with source citations, page numbers, and cosine similarity relevance scoring.
- Chunk-type filtering supporting text, tables, and section headings.

### 4. LLM-Powered Summarization & Quantitative Analysis
- Executive, brief, and detailed summaries powered by the Sarvam AI API.
- Tabular data queries and natural language quantitative analysis over extracted document context.

### 5. Modern Interactive Frontend
- Built with React 19, TypeScript, Vite, Tailwind CSS, and Radix UI primitives.
- Interactive PDF Viewer (`react-pdf`) with side-by-side RAG Chat, Executive Summary cards, and outline navigation.
- Dedicated Document Data Viewer (`/document/:id/pdf-information`) for inspecting and exporting canonical Docling extraction JSON.

### 6. Scalable Asynchronous Task Architecture
- Celery and Redis manage background document processing, embedding generation, and LLM calls.
- Concurrency limits, memory recycling ceilings (`--max-memory-per-child=3500000`), and neural model pre-warming for robust multi-document workloads.

---

## 🏗️ Architecture & Pipeline Flow

```mermaid
flowchart TD
    A[PDF Upload] --> B[FastAPI /documents/upload]
    B --> C[Celery Task: process_document_task]
    C --> D[DocumentProfiler: Sample & Profile PDF]
    
    D -->|Single Column Digital Text| E[Tier 1: FastPyMuPDFEngine]
    D -->|Tables / Scanned / Multi-Column| F[Tier 2: DoclingNeuralEngine]
    
    F -->|DocLayNet + TableFormer + RapidOCR| G[DoclingDocument]
    F -.->|On Exception / OOM| E
    
    E --> H[UnifiedFlysisAdapter]
    G --> H
    
    H --> I[FlysisHybridChunker]
    I --> J[Canonical Extraction Artifact: pdf-information/{id}_data.json]
    I --> K[sentence-transformers Embedding]
    K --> L[(PostgreSQL + pgvector)]
    
    L --> M[Sarvam AI RAG Chat & Summarization]
    J --> N[React 19 Frontend: Viewer, Chat & JSON Export]
```

---

## 🛠️ Tech Stack

### Backend & Machine Learning
- **Framework**: Python 3.10+ & FastAPI
- **Document Intelligence**: IBM Docling (`docling >= 2.15.0`), `docling-core[chunking] >= 2.15.0`, `rapidocr-onnxruntime >= 1.3.0`, PyMuPDF (`fitz` 1.24.11)
- **Deep Learning / NLP**: PyTorch, Hugging Face `transformers`, `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Database & Vector Search**: PostgreSQL with `pgvector` extension + SQLAlchemy 2.0 (AsyncIO) + Asyncpg
- **Task Queue & Caching**: Celery 5.4+ + Redis 7
- **LLM Provider**: Sarvam AI Python SDK (`sarvamai`)
- **Data Manipulation**: pandas 2.2+, numpy, Pillow

### Frontend
- **Framework**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS + `tailwindcss-animate`
- **UI Components**: Radix UI primitives + Lucide React icons
- **State & Routing**: TanStack Query (React Query v5) + React Router v7
- **Document Rendering**: `react-pdf`, `react-markdown`

---

## ⚙️ Prerequisites

- **Docker & Docker Compose**: (Recommended for full multi-service deployment)
- **Node.js**: v18.0 or higher (for local frontend development)
- **Python**: v3.10 or higher (for local backend development)
- **PostgreSQL with pgvector** & **Redis**: (Only required if running locally without Docker)

---

## 🔧 Environment Variables Configuration

Copy and configure the environment files according to your deployment strategy:

### Option A: Docker Deployment (`.env.docker`)
Create `.env.docker` in the repository root:

```env
# Database & Redis (Container hostnames)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=fly_db
DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password@db:5432/fly_db
REDIS_URL=redis://redis:6379/0

# LLM & Embedding Settings
SARVAM_API_KEY=your_sarvam_api_key
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Storage & Processing Limits
UPLOADS_DIR=/app/uploads
PDF_INFORMATION_DIR=/app/pdf-information
MAX_FILE_SIZE_MB=50

# Docling & Extraction Engine Settings
OCR_ENABLED=True
DOCLING_TABLE_MODE=accurate        # 'accurate' (TableFormer) or 'fast'
DOCLING_OCR_ENGINE=rapidocr        # 'rapidocr'
DOCLING_OCR_ENABLED=True
DOCLING_MAX_TOKENS=250             # Max token budget per structure-aware chunk

# Server Config
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### Option B: Local System Deployment (`.env.local` / `.env`)
Create `.env` in the root folder or backend folder:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/fly_db
REDIS_URL=redis://localhost:6379/0

SARVAM_API_KEY=your_sarvam_api_key
EMBEDDING_MODEL=all-MiniLM-L6-v2

UPLOADS_DIR=./uploads
PDF_INFORMATION_DIR=./pdf-information
MAX_FILE_SIZE_MB=50

OCR_ENABLED=True
DOCLING_TABLE_MODE=accurate
DOCLING_OCR_ENGINE=rapidocr
DOCLING_OCR_ENABLED=True
DOCLING_MAX_TOKENS=250

HOST=0.0.0.0
PORT=8000
DEBUG=True
```

---

## 🚀 Running the Application

### Option 1: Docker Compose (Recommended)

Docker Compose provisions PostgreSQL (`pgvector`), Redis, the FastAPI backend, the Celery worker (with pre-warmed Docling models and memory ceiling), and the React frontend in a unified container network:

```bash
docker-compose up -d --build
```

- **Frontend Application**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Base URL**: `http://localhost:8000/api/v1`

To view Celery worker extraction logs in real time:
```bash
docker-compose logs -f celery
```

---

### Option 2: Local Manual Setup

If running locally without Docker:

#### 1. Setup Backend Environment
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

#### 2. Start Celery Worker (with Docling pre-warming)
```bash
# Windows (solo pool)
celery -A app.worker.celery_app worker --loglevel=info -P solo

# Linux / macOS (concurrency controlled)
celery -A app.worker.celery_app worker --loglevel=info --concurrency=2 --max-memory-per-child=3500000
```

#### 3. Start FastAPI Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Start React Frontend
```bash
cd ../frontend
npm install
npm run dev
```
Frontend will be available at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Testing

The test suite validates the intelligent router, Fast Track engine, circuit breaker fallback, and Docling integration:

```bash
cd backend
pytest tests/ -v
```

Key test suites:
- `tests/test_router.py`: Validates sub-second profiling and routing decisions (digital text vs. table/scanned).
- `tests/test_fast_engine.py`: Tests PyMuPDF extraction speed and table/outline recovery.
- `tests/test_circuit_breaker.py`: Simulates Docling runtime errors to assert automatic fallback to `FastPyMuPDFEngine`.
- `tests/test_service_integration.py`: Validates end-to-end extraction and canonical data contract generation.

---

## 📡 Core API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/documents/upload` | Upload PDF, trigger background profiling, Docling extraction, and indexing |
| `GET` | `/api/v1/documents` | List documents with pagination and processing status |
| `GET` | `/api/v1/documents/{id}` | Get document metadata, page counts, and summary |
| `GET` | `/api/v1/documents/{python_doc_id}/download` | Stream original PDF file |
| `GET` | `/api/v1/documents/{python_doc_id}/text` | Get extracted text blocks, outline, and page-grouped blocks |
| `GET` | `/api/v1/documents/{python_doc_id}/data.json` | Get durable canonical extraction JSON (`pdf-information`) |
| `POST` | `/api/v1/documents/{python_doc_id}/extract/tables` | Extract structured tables as 2D string matrices & Markdown |
| `POST` | `/api/v1/documents/{python_doc_id}/extract/summary` | Generate LLM executive, brief, or detailed summary via Sarvam AI |
| `POST` | `/api/v1/documents/{python_doc_id}/index` | Vectorize chunks into `pgvector` store |
| `POST` | `/api/v1/documents/{python_doc_id}/search` | Semantic cosine similarity search over chunks |
| `POST` | `/api/v1/chat` | RAG conversational chat with source citations |

---

## 📂 Project Structure

```
Flysis-AlphaReports/
├── docker-compose.yml              # Container orchestration (DB, Redis, API, Worker, UI)
├── .env.docker                     # Environment variables for Docker Compose
├── .env.local                      # Environment variables for local runs
├── backend/
│   ├── Dockerfile                  # Python 3.10 image with Docling model pre-cache
│   ├── requirements.txt            # Docling, PyMuPDF, FastAPI, Celery, pgvector
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory & router mounting
│   │   ├── worker.py               # Celery app, model pre-warming & async task pipelines
│   │   ├── api/                    # Route handlers (upload, documents, analytics, chat)
│   │   │   ├── upload.py           # PDF upload and validation
│   │   │   ├── documents.py        # Metadata, text, search, and JSON retrieval
│   │   │   ├── analytics.py        # Table extraction, summary generation
│   │   │   └── chat.py             # Sarvam AI RAG chat
│   │   ├── core/                   # Configuration (config.py), database connection
│   │   ├── db/                     # SQLAlchemy models (Document, DocumentChunk)
│   │   ├── llm/                    # Sarvam AI client & RAG context assembly
│   │   ├── pdf/                    # 🚀 Hybrid PDF Intelligence Subsystem
│   │   │   ├── router.py           # DocumentProfiler & ExtractionRouter
│   │   │   ├── fast_engine.py      # Tier 1: FastPyMuPDFEngine (<1s digital extractor)
│   │   │   ├── docling_engine.py   # Tier 2: DoclingNeuralEngine (DocLayNet + TableFormer + RapidOCR)
│   │   │   ├── chunker.py          # FlysisHybridChunker (Docling HybridChunker + HF tokenizer)
│   │   │   ├── adapter.py          # UnifiedFlysisAdapter (DoclingDocument to canonical contracts)
│   │   │   ├── service.py          # HybridPDFExtractionService (Orchestrator & Circuit Breaker)
│   │   │   ├── config.py           # DoclingPipelineConfig & RouterConfig
│   │   │   └── legacy_compat.py    # Dataclasses & backward compatibility contracts
│   │   └── vector/                 # PgVectorStore (pgvector embedding & similarity search)
│   ├── tests/                      # Pytest suite (router, fast engine, circuit breaker)
│   ├── uploads/                    # Persisted raw uploaded PDF files
│   └── pdf-information/            # Persisted canonical extraction JSON artifacts
└── frontend/
    ├── Dockerfile                  # Multi-stage Node/Nginx container
    ├── package.json                # React 19, Vite, TanStack Query, Radix UI
    ├── src/
    │   ├── api/                    # Typed API client
    │   ├── components/             # PDF viewer, chat, executive summary cards
    │   ├── pages/                  # Dashboard, Library, DocumentViewer, PdfInformation
    │   └── App.tsx                 # Route declarations
    └── vite.config.ts              # Vite bundler configuration
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
