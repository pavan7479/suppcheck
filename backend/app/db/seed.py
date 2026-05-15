from app.services.vector_service import vector_service
import asyncio

initial_ingredients = [
    {
        "name": "Melatonin",
        "description": "Melatonin is an endogenous hormone that regulates circadian rhythm and sleep-wake timing. Commonly used to support sleep onset, improve sleep quality, and reduce jet lag-related disruption.",
        "category": "Sleep Support",
        "metadata": {
            "max_dosage_mg": 5,
            "benefits": ["sleep support", "circadian rhythm", "jet lag", "sleep onset"],
            "aliases": ["sleep hormone"],
            "risk_notes": ["may cause morning drowsiness at higher doses"]
        }
    },
    {
        "name": "Magnesium Glycinate",
        "description": "Magnesium glycinate is a gentle, well-absorbed chelated form of magnesium that supports neuromuscular relaxation, stress modulation, and healthy sleep quality.",
        "category": "Minerals / Sleep",
        "metadata": {
            "max_dosage_mg": 400,
            "benefits": ["muscle relaxation", "stress reduction", "sleep quality", "nervous system"],
            "aliases": ["magnesium bisglycinate"],
            "risk_notes": ["excess may cause loose stools"]
        }
    },
    {
        "name": "Caffeine Anhydrous",
        "description": "Caffeine anhydrous is a concentrated form of caffeine that stimulates the central nervous system to increase alertness, reduce perceived fatigue, and enhance reaction time.",
        "category": "Stimulants / Focus",
        "metadata": {
            "max_dosage_mg": 400,
            "benefits": ["energy", "alertness", "focus", "performance"],
            "aliases": ["caffeine"],
            "risk_notes": ["may cause jitters, rapid heart rate, or sleep disturbance"]
        }
    },
    {
        "name": "L-Theanine",
        "description": "L-Theanine is a calming amino acid from tea that promotes relaxation without drowsiness, smooths caffeine stimulation, and supports focused attention.",
        "category": "Amino Acids / Focus",
        "metadata": {
            "max_dosage_mg": 200,
            "benefits": ["relaxation", "stress modulation", "focus", "synergy with caffeine"],
            "aliases": ["theanine"],
            "risk_notes": []
        }
    },
    {
        "name": "Creatine Monohydrate",
        "description": "Creatine monohydrate increases phosphocreatine stores to enhance ATP recycling during high-intensity exercise, supporting strength, power output, and lean mass.",
        "category": "Performance / Strength",
        "metadata": {
            "max_dosage_mg": 5000,
            "benefits": ["strength", "power", "lean mass", "exercise performance"],
            "aliases": ["creatine"],
            "risk_notes": ["may cause transient water retention"]
        }
    },
    {
        "name": "Ashwagandha (KSM-66)",
        "description": "Ashwagandha is an adaptogenic herb traditionally used to support stress resilience, healthy cortisol dynamics, and calm mood; KSM-66 is a standardized root extract.",
        "category": "Adaptogens / Stress",
        "metadata": {
            "max_dosage_mg": 1000,
            "benefits": ["stress relief", "cortisol support", "calm mood", "adaptogen"],
            "aliases": ["withania somnifera"],
            "risk_notes": ["may cause drowsiness in some individuals"]
        }
    },
    {
        "name": "Glucosamine Sulfate",
        "description": "Glucosamine sulfate is a structural building block for cartilage that supports joint comfort and mobility, commonly used in osteoarthritis protocols.",
        "category": "Joint Support",
        "metadata": {
            "max_dosage_mg": 1500,
            "benefits": ["joint health", "cartilage support", "mobility"],
            "aliases": ["glucosamine"],
            "risk_notes": ["shellfish-derived forms may not suit allergies"]
        }
    },
    {
        "name": "Vitamin D3 (Cholecalciferol)",
        "description": "Vitamin D3 (cholecalciferol) supports calcium balance, bone density, immune modulation, and mood regulation; often synthesized from sun exposure.",
        "category": "Vitamins / Immunity",
        "metadata": {
            "max_dosage_mcg": 100,
            "benefits": ["bone health", "immune support", "mood", "calcium absorption"],
            "aliases": ["cholecalciferol", "vitamin d"],
            "risk_notes": ["excessive intake may increase calcium levels"]
        }
    },
    {
        "name": "Zinc Picolinate",
        "description": "Zinc picolinate is a highly bioavailable zinc form that supports immune defense, protein synthesis, and skin repair.",
        "category": "Minerals / Immunity",
        "metadata": {
            "max_dosage_mg": 40,
            "benefits": ["immune support", "skin repair", "protein synthesis"],
            "aliases": ["zinc"],
            "risk_notes": ["long-term high doses may lower copper"]
        }
    },
    {
        "name": "Omega-3 (Fish Oil)",
        "description": "Fish oil provides EPA and DHA omega-3s that support cardiovascular health, cognitive function, and a healthy inflammatory response.",
        "category": "Healthy Fats / Heart",
        "metadata": {
            "max_dosage_mg": 3000,
            "benefits": ["heart health", "brain function", "inflammation balance"],
            "aliases": ["omega-3", "epa", "dha", "fish oil"],
            "risk_notes": ["high doses may increase bleeding risk"]
        }
    },
    {
        "name": "Turmeric Curcumin",
        "description": "Curcumin, the active compound in turmeric, supports healthy inflammatory balance and antioxidant defenses; often paired with piperine to enhance absorption.",
        "category": "Herbs / Anti-inflammatory",
        "metadata": {
            "max_dosage_mg": 2000,
            "benefits": ["inflammation balance", "antioxidant", "joint comfort"],
            "aliases": ["curcuma longa", "curcumin"],
            "risk_notes": ["may interact with blood thinners"]
        }
    },
    {
        "name": "Beta-Alanine",
        "description": "Beta-alanine increases intramuscular carnosine to buffer acid, supporting high-intensity endurance and reducing fatigue sensation.",
        "category": "Performance / Endurance",
        "metadata": {
            "max_dosage_mg": 3200,
            "benefits": ["endurance", "fatigue resistance", "exercise performance"],
            "aliases": [],
            "risk_notes": ["may cause harmless tingling (paresthesia)"]
        }
    },
    {
        "name": "Rhodiola Rosea",
        "description": "Rhodiola is an adaptogen used to support stress resilience, mental endurance, and perceived energy during demanding tasks.",
        "category": "Adaptogens / Energy",
        "metadata": {
            "max_dosage_mg": 600,
            "benefits": ["stress resilience", "mental energy", "fatigue reduction"],
            "aliases": ["rhodiola", "golden root"],
            "risk_notes": []
        }
    },
    {
        "name": "Bacopa Monnieri",
        "description": "Bacopa monnieri is an Ayurvedic nootropic that supports memory consolidation, learning, and calm cognitive performance.",
        "category": "Nootropics / Memory",
        "metadata": {
            "max_dosage_mg": 300,
            "benefits": ["memory", "learning", "calm focus"],
            "aliases": ["brahmi"],
            "risk_notes": ["may cause mild digestive upset in some"]
        }
    },
    {
        "name": "Coenzyme Q10 (CoQ10)",
        "description": "Coenzyme Q10 (CoQ10) is a mitochondrial cofactor that supports cellular energy (ATP) production and antioxidant protection, with applications in heart health.",
        "category": "Antioxidants / Heart",
        "metadata": {
            "max_dosage_mg": 200,
            "benefits": ["cellular energy", "antioxidant", "heart health"],
            "aliases": ["ubiquinone", "ubiquinol", "coq10"],
            "risk_notes": []
        }
    }
]

async def seed_data():
    print("Seeding ingredient data...")
    try:
        vector_service.clear_collection()
    except Exception as e:
        print(f"Error clearing collection: {str(e)}")
    try:
        print(f"Adding {len(initial_ingredients)} curated items in batch...")
        vector_service.add_ingredients_batch(initial_ingredients)
        print("Curated items added.")
    except Exception as e:
        print(f"Batch add failed, falling back to single inserts: {e}")
        for item in initial_ingredients:
            print(f"Adding {item['name']}...")
            try:
                vector_service.add_ingredient(
                    name=item["name"],
                    description=item["description"],
                    category=item["category"],
                    metadata=item["metadata"]
                )
            except Exception as se:
                print(f"Error adding {item['name']}: {str(se)}")
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_data())
