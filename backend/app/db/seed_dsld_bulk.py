import os
import re
import glob
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

import pandas as pd

from app.services.vector_service import vector_service

# Paths (prefer repo-relative; allow override via DATA_DIR)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.normpath(os.path.join(REPO_ROOT, "data", "raw", "extracted_data", "DSLD-full-database-CSV"))
)
UNIQUE_INGS_PATH = os.path.join(REPO_ROOT, "backend", "unique_ingredients.txt")

# Curated items to preserve (do not override if present)
CURATED_NAMES = {
    "Melatonin",
    "Magnesium Glycinate",
    "Caffeine Anhydrous",
    "L-Theanine",
    "Creatine Monohydrate",
    "Ashwagandha (KSM-66)",
    "Glucosamine Sulfate",
    "Vitamin D3 (Cholecalciferol)",
    "Zinc Picolinate",
    "Omega-3 (Fish Oil)",
    "Turmeric Curcumin",
    "Beta-Alanine",
    "Rhodiola Rosea",
    "Bacopa Monnieri",
    "Coenzyme Q10 (CoQ10)",
}

# Name-specific enrichment for common DSLD ingredients to avoid generic text
NAME_OVERRIDES: Dict[str, Dict[str, List[str] or str]] = {
    "methylsulfonylmethane": {
        "aliases": ["MSM"],
        "benefits": ["joint comfort", "connective tissue", "sulfur donor"],
        "sentence": "{name} (MSM) is a sulfur-containing compound used to support joint comfort and connective tissue.",
    },
    "diindolylmethane": {
        "aliases": ["DIM"],
        "benefits": ["estrogen metabolism", "hormonal balance"],
        "sentence": "{name} (DIM) is a compound from cruciferous vegetables that supports estrogen metabolism and hormonal balance.",
    },
    "stinging nettle": {
        "aliases": ["Urtica dioica"],
        "benefits": ["urinary tract", "seasonal support"],
        "sentence": "{name} (Urtica dioica) is a traditional herb used for urinary tract and seasonal support.",
    },
    "glucuronolactone": {
        "aliases": [],
        "benefits": ["detoxification", "energy metabolism"],
        "sentence": "{name} is a glucose metabolite involved in detoxification pathways and is commonly used in energy formulas.",
    },
}


def read_top_ingredients(path: str, limit: int) -> List[str]:
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"(.+?)\s*\(\d+\)", line.strip())
            if m:
                out.append(m.group(1))
            if len(out) >= limit:
                break
    return out


def tokenize_categories(cat: str) -> List[str]:
    if not isinstance(cat, str) or not cat.strip():
        return []
    # Split on ; or , and trim
    parts = re.split(r"[;,]", cat)
    toks = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Normalize some common patterns
        p = re.sub(r"\s+", " ", p)
        toks.append(p)
    return toks


def build_category_index(data_dir: str) -> Dict[str, Counter]:
    """Return mapping: ingredient -> Counter of category tokens from DSLD."""
    csv_files = glob.glob(os.path.join(data_dir, "DietarySupplementFacts_*.csv"))
    index: Dict[str, Counter] = defaultdict(Counter)
    if not csv_files:
        print(f"[DSLDBULK] No CSV files found under: {data_dir}")
        return index

    usecols = ["Ingredient", "DSLD Ingredient Categories"]
    print(f"[DSLDBULK] Building category index from {len(csv_files)} files...")
    for fp in csv_files:
        try:
            for chunk in pd.read_csv(fp, usecols=usecols, chunksize=50000, encoding="utf-8"):
                ing_series = chunk["Ingredient"].fillna("").astype(str)
                cat_series = chunk["DSLD Ingredient Categories"].fillna("").astype(str)
                for ing, cat in zip(ing_series, cat_series):
                    ing = ing.strip()
                    if not ing:
                        continue
                    for tok in tokenize_categories(cat):
                        index[ing][tok] += 1
        except Exception as e:
            print(f"[DSLDBULK] Skipping {os.path.basename(fp)} due to error: {e}")
    print(f"[DSLDBULK] Category index built for {len(index)} unique ingredients.")
    return index


def simple_categorize(name: str, primary_cat: str) -> str:
    n = (name or "").lower()
    c = (primary_cat or "").lower()
    if any(t in c for t in ["vitamin"]):
        return "Vitamin"
    if any(t in c for t in ["mineral", "zinc", "magnesium", "iron", "calcium", "potassium", "sodium"]):
        return "Mineral"
    if any(t in c for t in ["herb", "botanical", "plant", "extract", "root", "leaf", "fruit", "seed"]):
        return "Herbal/Botanical"
    if any(t in c for t in ["amino", "peptide"]) or n.startswith("l-") or n.endswith("ine"):
        return "Amino Acid"
    if any(t in c for t in ["omega", "fish oil", "epa", "dha"]):
        return "Healthy Fats"
    if any(t in c for t in ["probiotic", "lactobacillus", "bifidobacterium", "bacillus"]):
        return "Probiotic"
    if any(t in c for t in ["caffeine", "stimulant", "guarana", "yohimb"]):
        return "Stimulant / Focus"
    if any(t in c for t in ["enzyme", "digestive"]):
        return "Enzyme / Digestive"
    if "protein" in c or "collagen" in c:
        return "Protein/Peptide"
    return primary_cat or "General"


def benefits_from_category(cat: str, name: str) -> List[str]:
    c = (cat or "").lower()
    n = (name or "").lower()
    b: List[str] = []
    if cat == "Vitamin":
        b += ["daily nutrition", "immune support", "metabolism"]
    if cat == "Mineral":
        b += ["electrolyte balance", "bone health", "metabolism"]
    if cat == "Herbal/Botanical":
        b += ["traditional wellness", "antioxidant", "inflammation balance"]
    if cat == "Amino Acid":
        b += ["muscle support", "neurotransmitter balance", "recovery"]
    if cat == "Healthy Fats":
        b += ["heart health", "brain function", "inflammation balance"]
    if cat == "Probiotic":
        b += ["gut health", "digestive balance", "immune support"]
    if cat == "Stimulant / Focus":
        b += ["energy", "alertness", "focus"]
    if cat == "Enzyme / Digestive":
        b += ["digestion", "nutrient absorption"]
    if cat == "Protein/Peptide":
        b += ["muscle repair", "satiety"]

    # Some name-based cues
    if "sleep" in n or "melatonin" in n:
        b += ["sleep support", "circadian rhythm"]
    if "magnesium" in n:
        b += ["muscle relaxation", "stress reduction"]
    if "zinc" in n:
        b += ["skin repair"]
    if "vitamin c" in n or "ascorbic" in n:
        b += ["antioxidant"]
    if "methylsulfonylmethane" in n or n == "msm":
        b += ["joint comfort", "connective tissue", "sulfur donor"]
    if "diindolylmethane" in n or n == "dim":
        b += ["estrogen metabolism", "hormonal balance"]
    if "stinging nettle" in n:
        b += ["urinary tract", "seasonal support"]
    if "glucuronolactone" in n:
        b += ["detoxification", "energy metabolism"]

    # Deduplicate while preserving order
    seen = set()
    out = []
    for x in b:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out[:6]


def make_description(name: str, category: str, benefits: List[str], tokens: List[str] = None, override: str = "") -> str:
    core = f"{name} is commonly found in dietary supplements within the {category} category."
    token_note = ""
    if tokens:
        toks = [t for t in tokens if t and isinstance(t, str)]
        if toks:
            join = ", ".join([toks[0].lower()] + ([toks[1].lower()] if len(toks) > 1 else []))
            token_note = f" It is often associated with {join}."
    if benefits:
        lead = ", ".join(benefits[:2])
        tail = ", and ".join(benefits[2:4]) if len(benefits) > 2 else ""
        if tail:
            extra = f" It supports {lead}, and {tail}."
        else:
            extra = f" It supports {lead}."
    else:
        extra = " It is used for general wellness."
    prefix = (override.strip() + " ") if override else ""
    return (prefix + core + token_note + extra).strip()


def seed_from_dsld(limit: int = 500, data_dir: str = DEFAULT_DATA_DIR):
    print(f"[DSLDBULK] Using data directory: {data_dir}")
    top_names = read_top_ingredients(UNIQUE_INGS_PATH, limit)
    if not top_names:
        print(f"[DSLDBULK] unique_ingredients.txt not found or empty at {UNIQUE_INGS_PATH}")
        return

    cat_index = build_category_index(data_dir)

    # Build items then upsert in batches to minimize API calls
    batch: List[Dict] = []
    added = 0
    def flush_batch():
        nonlocal batch, added
        if not batch:
            return
        for attempt in range(3):
            try:
                vector_service.add_ingredients_batch(batch)
                added += len(batch)
                batch = []
                return
            except Exception as e:
                wait = 2 ** attempt
                print(f"[DSLDBULK] Batch upsert failed (attempt {attempt+1}), retrying in {wait}s: {e}")
                import time as _t
                _t.sleep(wait)

    for idx, name in enumerate(top_names, start=1):
        if name in CURATED_NAMES:
            # Preserve curated enriched entries
            continue
        try:
            name = name.strip()
            counts = cat_index.get(name, Counter())
            primary_cat = counts.most_common(1)[0][0] if counts else "General"
            simple_cat = simple_categorize(name, primary_cat)
            # Pull top category tokens to customize text
            top_tokens = [t for t, _ in counts.most_common(3)] if counts else []
            bens = benefits_from_category(simple_cat, name)
            # Apply name-specific enrichment
            nkey = name.lower()
            override = ""
            aliases: List[str] = []
            if nkey in NAME_OVERRIDES:
                data = NAME_OVERRIDES[nkey]
                override = str(data.get("sentence", "")).format(name=name)
                aliases = list(data.get("aliases", []))
                extra_b = list(data.get("benefits", []))
                # Merge and dedup benefits
                for eb in extra_b:
                    if eb not in bens:
                        bens.append(eb)
            desc = make_description(name, simple_cat, bens, tokens=top_tokens, override=override)
            metadata = {
                "benefits": bens,
                "aliases": aliases,
                "risk_notes": [],
            }
            batch.append({
                "name": name,
                "description": desc,
                "category": simple_cat,
                "metadata": metadata,
            })
            if len(batch) >= 50:
                print(f"[DSLDBULK] Upserting batch... (processed ~{idx})")
                flush_batch()
        except Exception as e:
            print(f"[DSLDBULK] Failed to prepare '{name}': {e}")

    # Flush remaining
    flush_batch()
    print(f"[DSLDBULK] Seeding complete. Added {added} items (excluding curated preserved entries).")


if __name__ == "__main__":
    seed_from_dsld(limit=500, data_dir=DEFAULT_DATA_DIR)
