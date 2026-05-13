# AI Pipeline Design - SuppCheck AI

## Gemini Usage Strategy

### 1. Ingredient Extraction (Gemini Flash-Lite)
- **Goal**: Convert unstructured text into structured JSON.
- **Model**: `gemini-3.1-flash-lite` (configurable via `GEMINI_MODEL` env var).
- **Prompt**: Extracts ingredients, dosages, and units from free-text labels. Includes few-shot examples for accuracy.
- **Validation**: Deterministic regex fallback parses each line if AI under-extracts vs input count.

### 2. Risk Analysis & Observations (Gemini Flash-Lite)
- **Goal**: Provide nuanced reasoning combining vector KB grounding with AI analysis.
- **Context**: Passes grounded ingredient data (canonical names, categories, match scores) to Gemini.
- **Output**: Returns observations list, safety score (0-100), per-ingredient risk statuses (ok/warning/danger), and a 1-sentence summary.

### 3. Claim Analysis (Gemini Flash-Lite)
- **Goal**: Identify regulatory red flags (FDA/FTC style).
- **Prompt**: Flags claims implying cure, treatment, or prevention of disease, or those scientifically unsupported.

### 4. Semantic Embedding (Local Sentence Transformers)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU).
- **Config**: Overridable via `EMBEDDING_MODEL` and `EMBEDDING_DIM` env vars.
- **Usage**:
  - **Index Time**: Embed combined text of name + category + description + benefits + aliases + risk notes.
  - **Search Time**: Embed user query, perform cosine similarity search via ChromaDB.

## Retrieval Flow
1. **Query**: "ingredients for cognitive enhancement"
2. **Canonicalization**: Normalize query through alias map (e.g., "ascorbic acid" → "Vitamin C").
3. **Vector Search**: Retrieve top K ingredients via cosine similarity.
4. **Intent-Aware Boosting**: Apply category/keyword boosts (sleep, stress, energy, focus, recovery, immunity, digestive).
5. **Deduplication**: Remove duplicates by normalized name and aliases.
6. **Threshold Filtering**: Filter by `SEARCH_MIN_SIM` (default 0.35) with progressive fallback relaxation.

## Prompt Engineering Principles
- **Few-Shot Prompting**: Provide examples of correct extraction to improve accuracy.
- **Output Control**: Explicitly demand JSON format with specific keys to ensure backend stability.
- **Robust Parsing**: Bracket-matching JSON extractor handles markdown fences, malformed responses, and list-vs-dict variations.
