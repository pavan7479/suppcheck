import asyncio
import json
import os
from app.ai.gemini_client import gemini_client
from app.services.vector_service import vector_service
from dotenv import load_dotenv

load_dotenv()

INGREDIENTS_LIST = [
    "5-HTP", "Acai", "Activated charcoal", "Alfalfa", "Aloe vera", "Andrographis", "Ashwagandha", "Astragalus", 
    "Vitamin A", "Bacopa monnieri", "Bee pollen", "Berberine", "Beta-alanine", "Bilberry", "Biotin", "Bitter melon", 
    "Bitter orange", "Black cohosh", "Blessed thistle", "Blue-green algae", "Blueberry", "Boron", "Bromelain", 
    "Butterbur", "Thiamin (B1)", "Vitamin B12", "Riboflavin (B2)", "Niacin (B3)", "Pantothenic acid (B5)", 
    "Vitamin B6", "Vitamin C", "Vitamin D", "Vitamin E", "Vitamin K", "Calcium", "Magnesium", "Potassium", 
    "Iron", "Zinc", "Selenium", "Copper", "Manganese", "Chromium", "Molybdenum", "Iodine", "Creatine", 
    "Caffeine", "L-Theanine", "Glucosamine", "Chondroitin", "Turmeric", "Curcumin", "Garlic", "Ginseng", 
    "Ginkgo Biloba", "Echinacea", "St. John's Wort", "Saw Palmetto", "Valerian Root", "Melatonin", "CoQ10", 
    "Fish Oil", "EPA", "DHA", "Choline", "Inositol", "Biotin", "Folic Acid", "Vitamin B12", "L-Arginine", 
    "L-Carnitine", "L-Glutamine", "L-Tyrosine", "MSM", "Quercetin", "Resveratrol", "Probiotics", "Lactobacillus",
    "Bifidobacterium", "Psyllium Husk", "Milk Thistle", "Dandelion Root", "Fenugreek", "Holy Basil", "Maca Root"
]

async def generate_and_seed_batch(batch):
    prompt = f"""
    For the following supplement ingredients, provide a structured JSON list.
    Each object must have:
    - "name": Official common name
    - "description": 2-3 sentences explaining benefits and use.
    - "category": Primary health category (e.g., Sleep, Cognitive, Immunity).
    - "max_dosage_mg": Safe upper limit or common high dosage per day in mg (use numerical value only).
    
    Ingredients: {", ".join(batch)}
    
    Return ONLY valid JSON.
    """
    
    try:
        print(f"Generating data for batch of {len(batch)} ingredients...")
        raw_json = await gemini_client.generate_content(prompt)
        clean_json = raw_json.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        for item in data:
            print(f"Embedding and Seed: {item['name']}...")
            vector_service.add_ingredient(
                name=item["name"],
                description=item["description"],
                category=item["category"],
                metadata={"max_dosage_mg": item["max_dosage_mg"]}
            )
            # Small delay to keep the vector DB happy
            await asyncio.sleep(0.5)
            
        return True
    except Exception as e:
        print(f"Error in batch: {str(e)}")
        return False

async def seed_public_data():
    print(f"Starting seeding of {len(INGREDIENTS_LIST)} ingredients with Gemini extraction...")
    
    # Process in batches of 10 to avoid token limits and handle rate limits
    batch_size = 10
    for i in range(0, len(INGREDIENTS_LIST), batch_size):
        batch = INGREDIENTS_LIST[i:i+batch_size]
        success = await generate_and_seed_batch(batch)
        
        if success:
            print(f"Batch {i//batch_size + 1} complete. Waiting 5 seconds to respect free tier rate limits...")
            await asyncio.sleep(5)
        else:
            print(f"Batch {i//batch_size + 1} failed. Retrying in 10 seconds...")
            await asyncio.sleep(10)
            await generate_and_seed_batch(batch)

    print("--- FULL SEEDING COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(seed_public_data())
