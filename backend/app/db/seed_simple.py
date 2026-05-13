import asyncio
import json
import os
import re
import sys
from app.ai.gemini_client import gemini_client
from app.services.vector_service import vector_service
from dotenv import load_dotenv

load_dotenv()

async def generate_and_seed_batch(batch):
    print(f"[SEED] Requesting data for batch: {batch}", flush=True)
    prompt = f"""
    For the following supplement ingredients/nutrients, provide a structured JSON list.
    Each object must have:
    - "name": Official common name
    - "description": 2-3 sentences explaining physical/health role.
    - "category": Primary category (e.g., Vitamin, Mineral, Amino Acid, Botanical).
    - "max_dosage_mg": Common RDA or safe daily limit in mg (numerical value only, use reasonable estimates for free nutrients like Calories=2000).
    
    Ingredients: {", ".join(batch)}
    
    Return ONLY valid JSON.
    """
    
    try:
        raw_json = await gemini_client.generate_content(prompt)
        # Clean markdown
        clean_json = re.sub(r'```json\s*|\s*```', '', raw_json).strip()
        data = json.loads(clean_json)
        
        if not isinstance(data, list):
            if isinstance(data, dict) and "ingredients" in data:
                data = data["ingredients"]
            else:
                data = [data]

        for item in data:
            name = item.get('name', 'Unknown')
            print(f"[SEED] Indexing: {name}...", flush=True)
            vector_service.add_ingredient(
                name=name,
                description=item.get("description", "No description"),
                category=item.get("category", "General"),
                metadata={"max_dosage_mg": item.get("max_dosage_mg", 0)}
            )
        return True
    except Exception as e:
        print(f"[SEED] Error in batch: {str(e)}", flush=True)
        return False

async def seed_from_file(limit=100):
    print(f"[SEED] Clearing existing collection...", flush=True)
    vector_service.clear_collection()
    
    print(f"[SEED] Reading top {limit} ingredients from unique_ingredients.txt...", flush=True)
    ingredients = []
    try:
        with open("unique_ingredients.txt", "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r"(.+?)\s*\(\d+\)", line)
                if match:
                    ingredients.append(match.group(1))
                if len(ingredients) >= limit:
                    break
    except FileNotFoundError:
        print("[SEED] Error: unique_ingredients.txt not found!", flush=True)
        return

    print(f"[SEED] Starting seeding of {len(ingredients)} ingredients...", flush=True)
    
    batch_size = 10
    for i in range(0, len(ingredients), batch_size):
        batch = ingredients[i:i+batch_size]
        print(f"[SEED] Processing Batch {i//batch_size + 1}/{(len(ingredients)//batch_size)}...", flush=True)
        success = await generate_and_seed_batch(batch)
        
        if success:
            # 10 second wait for rate limiting
            print("[SEED] Batch success. Waiting 10s for rate limits...", flush=True)
            await asyncio.sleep(10)
        else:
            print("[SEED] Batch failed. Waiting 20s before retry...", flush=True)
            await asyncio.sleep(20)
            await generate_and_seed_batch(batch)

    print("--- BULK SEEDING COMPLETE ---", flush=True)

if __name__ == "__main__":
    # Let's do 100 for a quick start as requested
    asyncio.run(seed_from_file(limit=100))
