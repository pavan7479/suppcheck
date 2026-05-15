# API Design - SuppCheck AI

## Base URL
`http://127.0.0.1:8000/api/v1`

## Endpoints

### 1. Formulation Analysis
`POST /analyze`

Analyzes a supplement formulation using Gemini AI + vector KB grounding.

**Request Body:**
```json
{
  "product_name": "Sleep Well Plus",
  "category": "Sleep Support",
  "ingredients_text": "Melatonin 10mg, Magnesium 200mg",
  "marketing_claims": ["Deepest sleep ever", "Instant cure for insomnia"]
}
```

**Response:**
```json
{
  "product_name": "Sleep Well Plus",
  "safety_score": 75,
  "extracted_ingredients": [
    {
      "ingredient": "Melatonin",
      "canonical_name": "Melatonin",
      "dosage": 10,
      "unit": "mg",
      "status": "warning",
      "risk_note": "Melatonin dosage exceeds common recommended range (1-5mg)."
    }
  ],
  "formulation_observations": [
    "Common sleep stack, but melatonin is high.",
    "Magnesium glycinate supports relaxation."
  ],
  "claim_analysis": [
    {
      "claim": "Instant cure for insomnia",
      "is_problematic": true,
      "reason": "Claims to 'cure' a clinical condition are generally prohibited for supplements."
    }
  ],
  "review_summary": "Overall a standard sleep formulation with one high-dose ingredient..."
}
```

### 2. Semantic Ingredient Search
`GET /search`

Searches for ingredients based on semantic meaning using Gemini embeddings + ChromaDB.

**Query Parameters:**
- `q`: Search query (e.g., "ingredients for anxiety")
- `limit`: Number of results (default: 5)

**Response:**
```json
{
  "query": "ingredients for anxiety",
  "results": [
    {
      "name": "Ashwagandha (KSM-66)",
      "score": 0.85,
      "description": "Ashwagandha is an adaptogenic herb traditionally used to support stress resilience...",
      "category": "Adaptogens / Stress",
      "explanation": "Ashwagandha is an adaptogenic herb traditionally used to support stress resilience, healthy cortisol dynamics, and calm mood."
    }
  ]
}
```

### 3. Health Check
`GET /health`

Returns the status of the backend.

## Error Handling
- `400 Bad Request`: Invalid input or schema.
- `422 Unprocessable Entity`: Pydantic validation error.
- `500 Internal Server Error`: AI service failure or database error.

## Validation Strategy
- Use FastAPI's `HTTPException` for consistent error messages.
- Use Pydantic's `BaseModel` for both request and response schemas to ensure data integrity and auto-generate OpenAPI docs (`/docs`).
- Frontend normalizes Gemini-specific errors (suspended key, permission denied, model unavailable) into user-friendly messages.
