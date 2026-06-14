# Filysis (AlphaReports)

An intelligent document analysis, chunking, and querying platform. Filysis allows users to upload complex documents (PDFs), extract text, tables, and figures, generate semantic embeddings, and chat with their documents using state-of-the-art LLMs and vector search.

## 🚀 Features

- **Document Processing**: Robust PDF parsing using PyMuPDF and pdfplumber.
- **Smart Chunking**: Intelligent segmentation of documents into logical chunks (text, tables, figures).
- **Semantic Search**: Native vector search using PostgreSQL + `pgvector` and `sentence-transformers`.
- **LLM Integration**: Integrated with Sarvam API (and adaptable to others) for conversational querying and structured data extraction.
- **Modern Frontend**: A responsive, fast, and accessible user interface built with React 19, Vite, TailwindCSS, and Radix UI.

## 🛠️ Tech Stack

### Frontend
- React 19 + TypeScript
- Vite (Build Tool)
- Tailwind CSS (Styling)
- Radix UI + shadcn/ui (Accessible Components)
- React Query (Data Fetching)
- React Router (Routing)

### Backend
- Python 3.10+
- FastAPI (Web Framework)
- SQLAlchemy (ORM)
- PostgreSQL with `pgvector` extension
- PyMuPDF, pdfplumber, camelot-py (Document parsing)
- sentence-transformers (Embeddings)

## ⚙️ Prerequisites

Before you begin, ensure you have met the following requirements:
* Node.js (v18 or higher)
* Python (v3.10 or higher)
* PostgreSQL database with the [`pgvector`](https://github.com/pgvector/pgvector) extension installed.

## 📦 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/filysis.git
cd filysis
```

### 2. Backend Setup
Navigate to the backend directory and set up a virtual environment:
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

Create a `.env` file in the `backend` directory with your database connection and secrets:
```env
# Example .env
DATABASE_URL=postgresql://postgres:password@localhost:5432/filysis
APP_SECRET=your-super-secret-key
```

### 3. Frontend Setup
Open a new terminal and navigate to the frontend directory:
```bash
cd frontend

# Install dependencies
npm install
```

## 🚀 Running the Application

### Start the Backend Server
Make sure your virtual environment is active, then run:
```bash
cd backend
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`. You can view the Swagger documentation at `http://localhost:8000/docs`.

### Start the Frontend Server
```bash
cd frontend
npm run dev
```
The frontend will be available at `http://localhost:5173`.

## 📂 Project Structure

```
filysis/
├── backend/          # FastAPI backend application
│   ├── app/          # Core application code (api, core, db, llm, vector)
│   ├── uploads/      # Temporary storage for uploaded documents
│   └── main.py       # Application entry point
├── frontend/         # React application
│   ├── src/          # Frontend source code
│   └── public/       # Static assets
└── docs/             # Project documentation and architecture plans
```