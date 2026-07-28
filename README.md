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

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS + `tailwindcss-animate`
- **UI Components**: Radix UI primitives + Lucide React icons
- **State & Data Fetching**: TanStack Query (React Query v5) + React Router v7
- **PDF & Markdown**: `react-pdf`, `react-markdown`

### Backend
- **Framework**: Python 3.10+ & FastAPI
- **Database & ORM**: PostgreSQL with `pgvector` extension + SQLAlchemy (AsyncIO) + Asyncpg
- **PDF Extraction**: PyMuPDF (`fitz`), `pdfplumber`, `camelot-py`, `pandas`, `pillow`
- **Embeddings & Search**: `sentence-transformers` + `pgvector`
- **LLM Integration**: `sarvamai` SDK

---

## ⚙️ Prerequisites

- **Node.js**: v18.0 or higher
- **Python**: v3.10 or higher
- **PostgreSQL**: v14+ with the [`pgvector`](https://github.com/pgvector/pgvector) extension enabled

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/manideepreddytippana/Flysis-AlphaReports.git
cd Flysis-AlphaReports
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/your_db_name

# AI / LLM Configuration
SARVAM_API_KEY=your_sarvam_api_key
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Storage & Upload Settings
UPLOADS_DIR=./uploads
MAX_FILE_SIZE_MB=file_size
OCR_ENABLED=true

# Server Settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

### 3. Backend Setup
Navigate to the `backend` directory and set up a virtual environment:

```bash
cd backend
python -m venv .venv

# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Frontend Setup
Open a new terminal and navigate to the `frontend` directory:

```bash
cd frontend
npm install or npm i
```

---

## 🚀 Running the Application

### 1. Start the Backend Server
Ensure your PostgreSQL instance is running and your virtual environment is active:

```bash
cd backend
uvicorn main:app --reload
```
- API Endpoint: `http://localhost:8000/api/v1`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 2. Start the Frontend Development Server
```bash
cd frontend
npm run dev
```
- App Dashboard: `http://localhost:5173`

---

## 🔗 Key API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health status |
| `POST` | `/api/v1/documents/upload` | Upload PDF and trigger background extraction & indexing |
| `GET` | `/api/v1/documents` | List documents with pagination and filtering |
| `GET` | `/api/v1/documents/{id}` | Get metadata for a specific document |
| `DELETE`| `/api/v1/documents/{id}` | Delete document, PDF file, vector chunks, and cache |
| `POST` | `/api/v1/documents/{doc_id}/extract/full` | Full PDF re-extraction with metadata & outline |
| `POST` | `/api/v1/documents/{doc_id}/extract/tables` | Extract tables only |
| `POST` | `/api/v1/documents/{doc_id}/extract/summary`| Generate structured executive summary |
| `POST` | `/api/v1/documents/{doc_id}/index` | Custom re-indexing into `pgvector` |
| `POST` | `/api/v1/documents/{doc_id}/search` | Semantic vector search |
| `POST` | `/api/v1/llm/chat` | RAG Chat / LLM completion with source citations |
| `POST` | `/api/v1/llm/analyze` | Quantitative statistical analysis |

---

## 📂 Project Structure

```
Flysis-AlphaReports/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers (routes.py)
│   │   ├── core/         # Settings (config.py), DB session (database.py), Pydantic schemas (models.py)
│   │   ├── db/           # SQLAlchemy models (Document, DocumentChunk)
│   │   ├── llm/          # Sarvam AI client & RAG pipeline
│   │   ├── pdf/          # Extraction pipeline & PDFReportAnalyzer engine
│   │   └── vector/       # pgvector embeddings storage & similarity search
│   ├── uploads/          # Stored PDF uploads
│   ├── main.py           # FastAPI entrypoint & lifecycle setup
│   └── requirements.txt  # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── api/          # API client (client.ts)
│   │   ├── components/   # UI & Layout components
│   │   ├── pages/        # Dashboard, Library, DocumentViewer, PdfInformation, Analytics
│   │   ├── App.tsx       # Router configuration
│   │   └── main.tsx      # React root & QueryClient provider
│   ├── package.json      # Frontend dependencies & scripts
│   └── vite.config.ts    # Vite configuration
└── README.md
```