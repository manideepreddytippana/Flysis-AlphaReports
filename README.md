# Filysis (Flysis-AlphaReports)

An intelligent, enterprise-grade document analysis, semantic chunking, and querying platform. Filysis processes complex PDF documents (extracting text, structured tables, visual figures, and headings), builds hierarchical outlines, generates vector embeddings using PostgreSQL + `pgvector`, and provides interactive RAG (Retrieval-Augmented Generation) chat and structured analysis powered by Sarvam AI.

---

## 🚀 Features

- **Multi-Stage PDF Extraction Engine**:
  - **Heading-Aware Analyzer**: Detects document outlines, font styles, numbering patterns, and topic breaks.
  - **Table Extraction**: Multi-stage parsing via `PyMuPDF`, `pdfplumber`, and `camelot-py` into Markdown tables.
  - **OCR Fallback**: Automatically processes scanned/image-based PDF pages via PyMuPDF OCR.
- **Advanced Semantic Chunking**:
  - Logical chunking respecting heading levels, table boundaries, token limits, and topic shifts.
  - Generates exact JSON structured reports (`*_data.json`) per document.
- **Vector Search & RAG Pipeline**:
  - Stores chunk embeddings natively in PostgreSQL using `pgvector` and `sentence-transformers` (`all-MiniLM-L6-v2`).
  - Contextual RAG querying with source citations, page numbers, and relevance scores.
- **LLM-Powered Summarization & Analysis**:
  - Executive, brief, and detailed structured summaries (key findings, metrics, recommendations).
  - Quantitative analysis over extracted context and structured tabular data via Sarvam AI API.
- **Modern Interactive Frontend**:
  - Built with React 19, TypeScript, Vite, Tailwind CSS, and Radix UI.
  - Feature-rich PDF Viewer (`react-pdf`) with side-by-side RAG Chat, Executive Summary card, and metadata analysis.
- **Asynchronous Task Processing**:
  - Celery and Redis are utilized for offloading heavy PDF processing and ML model execution to background workers, keeping the API blazing fast.
  - Smart "Pre-warming" and lazy loading of ML models to eliminate cold start delays.

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS + `tailwindcss-animate`
- **UI Components**: Radix UI primitives + Lucide React icons
- **State & Data Fetching**: TanStack Query (React Query v5) + React Router v7
- **PDF & Markdown**: `react-pdf`, `react-markdown`

### Backend & Infrastructure
- **Framework**: Python 3.10+ & FastAPI
- **Database & ORM**: PostgreSQL with `pgvector` extension + SQLAlchemy (AsyncIO) + Asyncpg
- **Task Queue**: Celery + Redis
- **PDF Extraction**: PyMuPDF (`fitz`), `pdfplumber`, `camelot-py`, `pandas`, `pillow`
- **Embeddings & Search**: `sentence-transformers` + `pgvector`
- **LLM Integration**: `sarvamai` SDK
- **DevOps**: Docker & Docker Compose (Full containerized multi-service architecture)

---

## ⚙️ Prerequisites

- **Node.js**: v18.0 or higher
- **Python**: v3.10 or higher
- **Docker & Docker Compose**: (Recommended for running the full stack)
- **PostgreSQL & Redis**: (Only required if running locally without Docker)

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/manideepreddytippana/Flysis-AlphaReports.git
cd Flysis-AlphaReports
```

### 2. Configure Environment Variables
You have two options depending on how you want to run the app. Copy the appropriate configuration for your setup:

**Option A: For Docker (`.env.docker`)**
Create `.env.docker` in the root folder. Docker will use `db` and `redis` internally.
```env
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=your_db_name
DATABASE_URL=postgresql+asyncpg://your_db_user:your_db_password@db:5432/your_db_name
REDIS_URL=redis://redis:6379/0

SARVAM_API_KEY=your_sarvam_api_key
EMBEDDING_MODEL=all-MiniLM-L6-v2
UPLOADS_DIR=/app/uploads
MAX_FILE_SIZE_MB=50
OCR_ENABLED=True
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

**Option B: For Local System (`.env.local`)**
Create `.env.local` if running via manual terminal commands.
```env
DATABASE_URL=postgresql+asyncpg://your_db_user:your_db_password@localhost:5432/your_db_name
REDIS_URL=redis://localhost:6379/0
SARVAM_API_KEY=your_sarvam_api_key
EMBEDDING_MODEL=all-MiniLM-L6-v2
UPLOADS_DIR=./uploads
MAX_FILE_SIZE_MB=50
OCR_ENABLED=True
HOST=0.0.0.0
PORT=8000
DEBUG=True
```
*(Make sure you rename `.env.local` to `.env` or point your app to it when running locally!)*

---

## 🚀 Running the Application

### Option 1: Docker Compose (Highly Recommended)
You can boot the entire infrastructure (Frontend, Backend, PostgreSQL, Redis, and Celery Worker) using a single command:

```bash
docker-compose up -d --build
```
- App Dashboard: `http://localhost:3000`
- API Endpoint: `http://localhost:8000/api/v1`

### Option 2: Local Terminals (Manual Setup)
If you prefer running services manually on your Windows/Mac machine without Docker:

**1. Start the Celery Worker**
```bash
cd backend
venv\Scripts\activate
celery -A app.worker.celery_app worker --loglevel=info -P solo
```

**2. Start the Backend API**
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

**3. Start the Frontend Dev Server**
```bash
cd frontend
npm run dev
```

---

## 📂 Project Structure

```
Flysis-AlphaReports/
├── docker-compose.yml    # Full stack orchestrator
├── .env.docker           # Docker-specific environment variables
├── .env.local            # Local machine environment variables
├── backend/
│   ├── Dockerfile        # Python 3.10 Backend/Celery image
│   ├── app/
│   │   ├── main.py       # FastAPI entrypoint & lifecycle setup
│   │   ├── worker.py     # Celery App initialization and ML Pre-Warming
│   │   ├── api/          # Route handlers with modular routers (upload.py, etc)
│   │   ├── core/         # Settings (config.py), DB session (database.py)
│   │   ├── db/           # SQLAlchemy models (Document, DocumentChunk)
│   │   ├── llm/          # Sarvam AI client & RAG pipeline
│   │   ├── pdf/          # Extraction pipeline & PDFReportAnalyzer engine
│   │   └── vector/       # pgvector embeddings storage & similarity search
│   ├── uploads/          # Stored PDF uploads
│   └── requirements.txt  # Backend dependencies
├── frontend/
│   ├── Dockerfile        # Node 20 / Nginx Frontend image
│   ├── src/
│   │   ├── api/          # API client (client.ts)
│   │   ├── components/   # UI & Modular Components (PDFViewer, ChatInterface, etc)
│   │   ├── hooks/        # Custom React Hooks (useDocumentChat, usePDFExtraction)
│   │   ├── pages/        # Dashboard, Library, DocumentViewer, Analytics
│   │   ├── App.tsx       # Router configuration
│   │   └── main.tsx      # React root & QueryClient provider
│   ├── package.json      # Frontend dependencies & scripts
│   └── vite.config.ts    # Vite configuration
└── README.md
```