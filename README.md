# SuppCheck AI — Supplement Formulation Review Platform

SuppCheck AI is a production-quality platform built with FastAPI and React that leverages Google Gemini AI to review nutraceutical formulations. It extracts ingredients, performs risk analysis, and provides semantic search capabilities.

## Features
- **AI Ingredient Extraction**: Converts unstructured label text into structured JSON with deterministic regex fallback.
- **Risk Analysis**: AI-powered detection of excessive dosages, stacking risks, and problematic combinations.
- **Claim Compliance**: Flags potentially misleading or prohibited marketing claims (FDA/FTC style).
- **Semantic Explorer**: Meaning-based ingredient search using Gemini embeddings + ChromaDB with intent-aware boosting.
- **Modern UI**: Tabbed dashboard (Analyze / Search) built with TailwindCSS and Lucide icons.

## Tech Stack
- **Backend**: Python 3.10+, FastAPI, Pydantic, ChromaDB, Gemini embeddings.
- **Frontend**: React 18, Vite, TailwindCSS, Lucide Icons, axios.
- **AI**: Google Gemini Flash-Lite (`gemini-3.1-flash-lite`), Gemini embeddings (`models/gemini-embedding-001`).

## Setup Instructions

### 1. Prerequisites
- Node.js & npm
- Python 3.10+
- Google Gemini API Key

### 2. Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and configure your `.env` file:
   ```env
   GOOGLE_API_KEY=your_key_here  # or GEMINI_API_KEY
   GEMINI_EMBED_MODEL=models/gemini-embedding-001
   CHROMA_DB_PATH=./chroma_db
   SEARCH_MIN_SIM=0.35
   PORT=8000
   DEBUG=true
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Seed the ingredient database (optional; can be done post-deploy in batches):
   ```bash
   # Curated enriched ingredients (15 hand-written entries)
   python -m app.db.seed

   # Bulk DSLD import (~500 top ingredients from NIH dataset)
   python -m app.db.seed_dsld_bulk
   ```
5. Start the server:
   ```bash
   python -m app.main
   ```
   The API will be available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:5173`.

## Architecture
See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design, [AI_PIPELINE.md](./AI_PIPELINE.md) for AI integration details, [API_DESIGN.md](./API_DESIGN.md) for endpoint specifications, [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) for vector DB schema, and [DATASET_WORKFLOW.md](./DATASET_WORKFLOW.md) for data engineering documentation.
