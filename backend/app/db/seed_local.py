import os
import re
import sys
from typing import List

from app.services.vector_service import vector_service


def read_top_ingredients(path: str, limit: int) -> List[str]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"(.+?)\s*\(\d+\)", line.strip())
            if m:
                items.append(m.group(1))
            if len(items) >= limit:
                break
    return items


def categorize(name: str) -> str:
    n = name.lower()
    if "blend" in n:
        return "Blend"
    if "extract" in n or "herb" in n or "botanical" in n:
        return "Herbal/Botanical"
    if n.startswith("l-") or "amino" in n or n.endswith("ine") or n.endswith("ic acid"):
        return "Amino Acid"
    if "vitamin" in n:
        return "Vitamin"
    if any(t in n for t in ["zinc", "magnesium", "iron", "calcium", "sodium", "potassium"]):
        return "Mineral"
    if any(t in n for t in ["seed", "root", "leaf", "flower", "bark"]):
        return "Plant Part"
    if "oil" in n:
        return "Oil"
    if "protein" in n or "peptide" in n or "collagen" in n:
        return "Protein/Peptide"
    return "General"


def make_description(name: str, category: str) -> str:
    base = f"{name} is a {category.lower()} ingredient commonly found in dietary supplements."
    # Light heuristics to avoid identical phrasing
    n = name.lower()
    if "extract" in n:
        base += " It is provided as an extract standardized from plant sources."
    if "vitamin" in n:
        base += " This entry reflects a vitamin used to support general wellness."
    if any(t in n for t in ["creatine", "beta alanine", "l-arginine", "l-citrulline"]):
        base += " Often referenced in performance and training contexts."
    if any(t in n for t in ["biotin", "saw palmetto", "pumpkin seed", "zinc", "horsetail"]):
        base += " Frequently discussed in hair and scalp support contexts."
    return base


def seed_local(limit: int = 500, source_file: str = "unique_ingredients.txt"):
    print(f"[LOCAL SEED] Clearing existing collection...", flush=True)
    vector_service.clear_collection()

    if not os.path.isabs(source_file):
        source_file = os.path.join(os.getcwd(), source_file)

    if not os.path.exists(source_file):
        print(f"[LOCAL SEED] Error: {source_file} not found.", flush=True)
        return

    ingredients = read_top_ingredients(source_file, limit)
    print(f"[LOCAL SEED] Seeding {len(ingredients)} ingredients with local embeddings...", flush=True)

    for idx, name in enumerate(ingredients, start=1):
        try:
            cat = categorize(name)
            desc = make_description(name, cat)
            vector_service.add_ingredient(name=name, description=desc, category=cat, metadata={})
            if idx % 50 == 0:
                print(f"[LOCAL SEED] {idx}/{len(ingredients)} indexed...", flush=True)
        except Exception as e:
            print(f"[LOCAL SEED] Failed to index '{name}': {e}", flush=True)

    print("[LOCAL SEED] Complete.", flush=True)


if __name__ == "__main__":
    # Simple CLI: python -m app.db.seed_local [limit]
    limit = 500
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except Exception:
            pass
    seed_local(limit=limit)
