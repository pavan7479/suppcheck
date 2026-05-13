from fastapi import APIRouter, HTTPException
from app.schemas.api_models import AnalyzeRequest, AnalyzeResponse, SearchResponse, SearchResult
from app.services.analysis_service import analysis_service
from app.services.vector_service import vector_service

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    print(f"DEBUG: Received analyze request for {request.product_name}")
    try:
        return await analysis_service.analyze_formulation(request)
    except Exception as e:
        print(f"DEBUG: Analysis failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=SearchResponse)
async def search(q: str, limit: int = 5):
    try:
        results = vector_service.search_ingredients(q, n_results=limit)
        formatted_results = []
        for res in results:
            formatted_results.append(SearchResult(
                name=res["name"],
                description=res["description"],
                category=res["category"],
                score=res["score"],
                explanation=res.get("explanation")
            ))

        return SearchResponse(query=q, results=formatted_results)
    except Exception as e:
        print(f"DEBUG: Search failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
