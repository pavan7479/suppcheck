import asyncio
import json
import os
import re
from app.ai.gemini_client import gemini_client
from app.services.vector_service import vector_service
from dotenv import load_dotenv

load_dotenv()

async def generate_and_seed_batch(batch):
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
        
        for item in data:
            print(f"Index: {item['name']}...")
            vector_service.add_ingredient(
                name=item["name"],
                description=item["description"],
                category=item["category"],
                metadata={"max_dosage_mg": item["max_dosage_mg"]}
            )
            await asyncio.sleep(0.5)
        return True
    except Exception as e:
        print(f"Error in batch: {str(e)}")
        return False

async def seed_from_file(limit=200):
    print("Clearing existing collection...")
    vector_service.clear_collection()
    
    print(f"Reading top {limit} ingredients from NIH dataset...")
    ingredients = []
    with open("unique_ingredients.txt", "r", encoding="utf-8") as f:
        for line in f:
            # Extract just the name using regex: "Name (Count)"
            match = re.match(r"(.+?)\s*\(\d+\)", line)
            if match:
                ingredients.append(match.group(1))
            if len(ingredients) >= limit:
                break

    print(f"Starting seeding of {len(ingredients)} ingredients (Top {limit} most frequent)...")
    
    batch_size = 10
    for i in range(0, len(ingredients), batch_size):
        batch = ingredients[i:i+batch_size]
        print(f"Processing Batch {i//batch_size + 1}/{(limit//batch_size)}...")
        success = await generate_and_seed_batch(batch)
        
        if success:
            # 10 second wait for 6 RPM (very safe for the 15 RPM free tier limit)
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(15)
            await generate_and_seed_batch(batch)

    print("--- BULK SEEDING COMPLETE ---")

if __name__ == "__main__":
    # Reduced to 200 for safe free tier execution
    asyncio.run(seed_from_file(limit=200))
