# System Architecture - SuppCheck AI

## Overview
SuppCheck AI is a production-grade system designed to review supplement and nutraceutical formulations. It leverages Gemini AI for extraction, reasoning, and analysis, and uses a local vector database (ChromaDB) with sentence-transformers for semantic search and retrieval of safety/ingredient data.

## Component Architecture

### 1. Frontend (React + TailwindCSS)
- **User Interface**: Modern, responsive dashboard with analyze and search tabs.
- **State Management**: React Hooks (useState) for form state, results, loading, and error handling.
- **Visualization**: Color-coded risk cards, safety score display, ingredient extraction tables, and semantic search results.

### 2. Backend (FastAPI)
- **API Layer**: RESTful endpoints for formulation analysis (`/analyze`) and semantic search (`/search`).
- **Service Layer**: Decoupled `AnalysisService` (extraction, grounding, risk, claims) and `VectorService` (ChromaDB CRUD, search, dedup).
- **Validation Layer**: Pydantic models for request/response validation with auto-generated OpenAPI docs at `/docs`.

### 3. AI Pipeline
- **Extraction Engine**: Gemini Flash-Lite (`gemini-3.1-flash-lite`) for parsing unstructured supplement labels into structured JSON, with deterministic regex fallback.
- **Reasoning Engine**: Gemini Flash-Lite for generating formulation observations, safety scores, per-ingredient risk statuses, and review summaries.
- **Embedding Engine**: Local `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU) for generating semantic vectors — no cloud embedding API needed.

### 4. Vector Database (ChromaDB)
- **Storage**: Persistent local file-based storage at path controlled by `CHROMA_DB_PATH` env var.
- **Collection**: `ingredients_kb` with cosine similarity (HNSW index).
- **Search**: Fast k-NN similarity search with intent-aware boosting, alias canonicalization, deduplication, and progressive threshold fallback.

## Data Flow

1. **Submission**: User inputs a supplement formulation (free-text ingredients + optional marketing claims).
2. **Extraction**: FastAPI sends normalized text to Gemini. Gemini extracts structured ingredients/dosages. Regex fallback ensures no under-extraction.
3. **Analysis**:
   - **Vector Grounding**: Each extracted ingredient is searched against ChromaDB for canonical name, category, and description.
   - **Risk Assessment**: Gemini analyzes grounded ingredients for dosage concerns, stacking risks, and synergy.
   - **Claim Analysis**: Gemini flags problematic marketing claims (cure/treatment/prevention language).
4. **Summary**: Gemini generates a 1-sentence overall verdict with safety score (0-100).
5. **Response**: Frontend displays the comprehensive report with color-coded risk indicators.

## Vector Search Flow
1. **Indexing**: ~500 ingredients (15 curated enriched + ~485 DSLD bulk) are embedded locally and stored in ChromaDB.
2. **Querying**: User provides a phrase (e.g., "sleep support").
3. **Embedding**: The phrase is embedded using local sentence-transformers.
4. **Canonicalization**: Query normalized through alias map (e.g., "ascorbic acid" → "Vitamin C").
5. **Retrieval**: Top K similar ingredients retrieved with intent-aware category boosts.
6. **Post-processing**: Deduplication by normalized name/aliases, threshold filtering, score capping at 1.0.

## Deployment
- **Local**: Backend via `python -m app.main` (uvicorn), frontend via `npm run dev` (Vite).
- **Config**: All paths and thresholds controlled via `backend/.env` (`CHROMA_DB_PATH`, `SEARCH_MIN_SIM`, `GOOGLE_API_KEY`, `PORT`, `DEBUG`, `RELOAD`).
