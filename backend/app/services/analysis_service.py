import json
import re
from app.ai.gemini_client import gemini_client
from app.schemas.api_models import AnalyzeRequest, AnalyzeResponse, IngredientExtraction, ClaimAnalysis, IngredientAnalysisResponse
from app.services.vector_service import vector_service
from typing import List

class AnalysisService:
    def _normalize_ingredients_text(self, text: str) -> str:
        s = text or ""
        # Replace common list delimiters with newlines
        s = re.sub(r"[;,|\u2022\u00B7•·]+", "\n", s)
        # Normalize multiple newlines/spaces
        s = re.sub(r"\r\n?|\f|\v", "\n", s)
        s = re.sub(r"\n+", "\n", s)
        # Trim each line and drop empties
        lines = [ln.strip() for ln in s.split("\n")]
        lines = [ln for ln in lines if ln]
        return "\n".join(lines)
    def _extract_json(self, text: str):
        """Robustly extract JSON from a string that might contain other text or markdown."""
        def _find_matching(s: str, start: int, open_ch: str, close_ch: str) -> int:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(s)):
                ch = s[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == '\\':
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        return i
            return -1

        try:
            s = text or ""
            s = s.replace("```json", "```")
            s = s.strip()

            # Prefer fenced code block content if present
            fence_start = s.find("```")
            if fence_start != -1:
                fence_end = s.find("```", fence_start + 3)
                if fence_end != -1:
                    fenced = s[fence_start + 3:fence_end].strip()
                    try:
                        return json.loads(fenced)
                    except Exception:
                        pass

            # Try bracket-matching for object or array
            for open_ch, close_ch in (("{", "}"), ("[", "]")):
                start = s.find(open_ch)
                if start != -1:
                    end = _find_matching(s, start, open_ch, close_ch)
                    if end != -1:
                        candidate = s[start:end + 1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            pass

            # Last resort regex (non-greedy)
            match = re.search(r'(\{[\s\S]*?\}|\[[\s\S]*?\])', s)
            if match:
                return json.loads(match.group(1))

            return [] if "[" in s or "list" in s.lower() else {}
        except Exception:
            return [] if "list" in (text or "").lower() else {}

    async def analyze_formulation(self, request: AnalyzeRequest) -> AnalyzeResponse:
        print(f"\n{'='*50}", flush=True)
        print(f"[SERVICE] Starting full analysis for: {request.product_name}", flush=True)
        print(f"{'='*50}", flush=True)
        
        # 1. Extract ingredients
        print("\n[STEP 1] Extracting ingredients and dosages...", flush=True)
        norm_ingredients = self._normalize_ingredients_text(request.ingredients_text)
        extraction_prompt = f"""
        Extract ALL supplement ingredients and their dosages from the text below.
        - The text may contain multiple items separated by commas, semicolons, pipes (|), or new lines.
        - Treat EACH segment as a separate ingredient. Do not merge items.
        - Return ONLY valid JSON as a list of objects with keys: "ingredient", "dosage", "unit".
        - If dosage is missing, use 0. If unit is missing, use "N/A".
        Example: "A 500 mg, B 10 IU" -> [{ {"ingredient":"A","dosage":500,"unit":"mg"} , {"ingredient":"B","dosage":10,"unit":"IU"} }]
        
        Text: {norm_ingredients}
        """
        raw_extraction = await gemini_client.generate_content(extraction_prompt)
        ingredients_data = self._extract_json(raw_extraction)
        if not isinstance(ingredients_data, list):
            ingredients_data = [ingredients_data] if ingredients_data else []

        # Deterministic fallback: if AI under-extracts compared to input lines, parse each line
        input_lines = [ln.strip() for ln in norm_ingredients.split("\n") if ln.strip()]
        if len(input_lines) > 1 and len(ingredients_data) < len(input_lines):
            parsed = []
            pat = re.compile(r"^(.+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Zµμ%]+)?$")
            for ln in input_lines:
                m = pat.match(ln)
                if m:
                    name = m.group(1).strip()
                    dosage = float(m.group(2)) if "." in m.group(2) else int(m.group(2))
                    unit = (m.group(3) or "N/A").strip()
                    parsed.append({"ingredient": name, "dosage": dosage, "unit": unit})
                else:
                    parsed.append({"ingredient": ln, "dosage": 0, "unit": "N/A"})
            ingredients_data = parsed

        print(f"[STEP 1] Completed. Extracted {len(ingredients_data)} ingredients.", flush=True)
        
        # 2. Vector DB Grounding (Canonical Name & Safety Thresholds)
        print("\n[STEP 2] Grounding ingredients with Vector KB...", flush=True)
        grounded_data = []
        for item in ingredients_data:
            name = item.get("ingredient", "Unknown") if isinstance(item, dict) else str(item)
            search_results = vector_service.search_ingredients(name, n_results=1)
            
            if search_results:
                match = search_results[0]
                grounded_data.append({
                    "original": name,
                    "canonical": match["name"],
                    "category": match["category"],
                    "description": match["description"],
                    "dosage": item.get("dosage", 0) if isinstance(item, dict) else 0,
                    "unit": item.get("unit", "N/A") if isinstance(item, dict) else "N/A",
                    "match_score": match["score"]
                })
            else:
                grounded_data.append({
                    "original": name,
                    "canonical": name,
                    "category": "Unknown",
                    "description": "No local safety data found.",
                    "dosage": item.get("dosage", 0) if isinstance(item, dict) else 0,
                    "unit": item.get("unit", "N/A") if isinstance(item, dict) else "N/A",
                    "match_score": 0
                })
        print(f"[STEP 2] Completed grounding for {len(grounded_data)} ingredients.", flush=True)

        # 3. Risk analysis & Observations
        print("\n[STEP 3] Performing risk analysis and observation generation...", flush=True)
        risk_prompt = f"""
        Analyze the following supplement formulation. 
        Ingredients (with grounded KB context): {grounded_data}
        Category: {request.category}
        
        CRITICAL: Your response MUST be a SINGLE JSON OBJECT with these EXACT keys:
        - "observations": A list of 3-4 specific scientific/safety observations.
        - "summary": A 1-sentence overall verdict.
        - "safety_score": An integer from 0-100 (100 being perfectly safe).
        - "ingredient_risks": A list of objects (one for each input ingredient) with:
            - "status": 'ok', 'warning', or 'danger'
            - "note": A brief explanation of the risk or benefit.

        If an ingredient is not in the KB or has a match_score < 0.5, mention that it's unverified.
        """
        raw_risk = await gemini_client.generate_content(risk_prompt)
        risk_analysis = self._extract_json(raw_risk)
        
        # Robustly handle different response formats from AI (list vs dict)
        if isinstance(risk_analysis, list):
            observations = ["Formulation analyzed for basic safety."]
            summary = "AI analysis completed based on ingredient profiles."
            safety_score = 70
            ingredient_risks = risk_analysis
        else:
            observations = risk_analysis.get("observations", ["No specific observations generated."])
            summary = risk_analysis.get("summary", "Analysis complete.")
            safety_score = risk_analysis.get("safety_score", 100)
            ingredient_risks = risk_analysis.get("ingredient_risks", [])
            
        print("[STEP 3] Completed.", flush=True)
        
        # 3. Marketing claim analysis
        claim_analysis_results = []
        if request.marketing_claims:
            print(f"\n[STEP 3] Analyzing {len(request.marketing_claims)} marketing claims...", flush=True)
            claim_prompt = f"""
            Analyze these supplement marketing claims for problematic language (e.g., claiming to cure/treat disease).
            Claims: {request.marketing_claims}
            
            Return ONLY valid JSON as a list of objects with keys: "claim", "is_problematic", "reason".
            """
            raw_claims = await gemini_client.generate_content(claim_prompt)
            claim_analysis_results = self._extract_json(raw_claims)
            if not isinstance(claim_analysis_results, list):
                claim_analysis_results = [claim_analysis_results] if claim_analysis_results else []
            print("[STEP 3] Completed.", flush=True)
        else:
            print("\n[STEP 3] No marketing claims provided. Skipping.", flush=True)

        # Build response
        print("\n[FINAL] Assembling results...", flush=True)
        extracted_ingredients = []
        for i, item in enumerate(grounded_data):
            # Match risk info to ingredient index
            risk_info = {}
            if i < len(ingredient_risks):
                risk_info = ingredient_risks[i] if isinstance(ingredient_risks[i], dict) else {"note": str(ingredient_risks[i])}
            
            extracted_ingredients.append(IngredientAnalysisResponse(
                ingredient=item["original"],
                canonical_name=item["canonical"],
                dosage=item["dosage"],
                unit=item["unit"],
                status=risk_info.get("status", "ok"),
                risk_note=risk_info.get("note")
            ))

        print(f"{'='*50}", flush=True)
        print(f"[SERVICE] Analysis complete for: {request.product_name}", flush=True)
        print(f"{'='*50}\n", flush=True)
        
        return AnalyzeResponse(
            product_name=request.product_name,
            safety_score=safety_score,
            extracted_ingredients=extracted_ingredients,
            formulation_observations=observations if isinstance(observations, list) else [str(observations)],
            claim_analysis=claim_analysis_results,
            review_summary=summary
        )

analysis_service = AnalysisService()
