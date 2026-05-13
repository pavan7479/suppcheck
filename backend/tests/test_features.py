import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_analyze():
    print("\n--- Testing /analyze endpoint ---")
    payload = {
        "product_name": "Test Pre-Workout",
        "ingredients_text": "Caffeine Anhydrous 200mg, L-Theanine 100mg, Creatine Monohydrate 5g",
        "category": "Pre-Workout",
        "marketing_claims": ["Cures fatigue", "Increases focus"]
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"Sending POST to {BASE_URL}/analyze...")
            response = await client.post(f"{BASE_URL}/analyze", json=payload)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Safety Score: {data.get('safety_score')}")
                print(f"Review Summary: {data.get('review_summary')}")
            else:
                print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"Test failed with exception: {type(e).__name__}: {str(e)}")

async def test_search():
    print("\n--- Testing /search endpoint ---")
    query = "ingredients for cognitive focus"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/search", params={"q": query, "limit": 3})
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Query: {data.get('query')}")
                results = data.get('results', [])
                print(f"Found {len(results)} results:")
                for res in results:
                    print(f"  - {res['name']} (Score: {res['score']})")
                    print(f"    {res['explanation']}")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Test failed: {str(e)}")

async def main():
    print("Starting Feature Tests...")
    # These tests require the server to be running.
    # Note: Search results will depend on whether the DB is seeded.
    await test_analyze()
    await test_search()

if __name__ == "__main__":
    asyncio.run(main())
