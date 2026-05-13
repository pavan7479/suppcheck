from pydantic import BaseModel, Field
from typing import List, Optional

class IngredientExtraction(BaseModel):
    ingredient: str
    dosage: float
    unit: str

class ClaimAnalysis(BaseModel):
    claim: str
    is_problematic: bool
    reason: str

class AnalyzeRequest(BaseModel):
    product_name: str
    category: Optional[str] = "General Supplement"
    ingredients_text: str
    marketing_claims: List[str] = []

class IngredientAnalysisResponse(BaseModel):
    ingredient: str
    canonical_name: Optional[str] = None
    dosage: float
    unit: str
    status: str = "ok" # ok, warning, danger
    risk_note: Optional[str] = None

class AnalyzeResponse(BaseModel):
    product_name: str
    safety_score: int = 100 # 0-100
    extracted_ingredients: List[IngredientAnalysisResponse]
    formulation_observations: List[str]
    claim_analysis: List[ClaimAnalysis]
    review_summary: str

class SearchResult(BaseModel):
    name: str
    description: str
    category: str
    score: float
    explanation: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
