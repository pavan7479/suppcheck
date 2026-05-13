import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is on sys.path
BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from app.schemas.api_models import AnalyzeRequest
from app.services.analysis_service import analysis_service


def pretty(obj):
    import json
    return json.dumps(obj, indent=2, ensure_ascii=False)


async def main():
    # Ensure backend/.env is loaded
    base = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=base / ".env", override=True)

    req = AnalyzeRequest(
        product_name="Sleep Blend",
        category="Sleep Support",
        ingredients_text=(
            "Melatonin 3 mg, Ashwagandha 300 mg, Magnesium Glycinate 200 mg, Vitamin C 500 mg"
        ),
        marketing_claims=[
            "Clinically proven to improve sleep quality",
            "Reduces stress and supports relaxation",
        ],
    )

    print("[RUN] Starting sample analysis with key suffix:", (os.getenv("GOOGLE_API_KEY") or "")[-4:])
    res = await analysis_service.analyze_formulation(req)

    # Convert Pydantic model to dict for pretty print
    d = res.model_dump()

    print("\n=== Analysis Result (summary) ===")
    print("Product:", d["product_name"]) 
    print("Safety Score:", d["safety_score"]) 
    print("Observations:")
    for o in d.get("formulation_observations", [])[:4]:
        print(" -", o)
    print("\nExtracted Ingredients:")
    for it in d.get("extracted_ingredients", []):
        print(f" - {it['ingredient']} | canonical={it.get('canonical_name')} | {it['dosage']} {it['unit']} | status={it.get('status','ok')}")
    print("\nClaim Analysis:")
    for c in d.get("claim_analysis", []):
        print(f" - '{c['claim']}' -> problematic={c['is_problematic']} | {c['reason']}")

    print("\n=== Full JSON ===")
    print(pretty(d))


if __name__ == "__main__":
    asyncio.run(main())
