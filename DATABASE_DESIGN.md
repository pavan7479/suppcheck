# Database Design - SuppCheck AI

## Data Strategy
A curated local dataset of supplement ingredients powers both semantic search and AI-assisted risk analysis. The dataset combines hand-enriched curated entries with bulk data from the NIH DSLD.

## Vector Schema (ChromaDB)

**Collection Name**: `ingredients_kb`

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | String | Slug from ingredient name (e.g., "melatonin") |
| `name` | String (metadata) | Ingredient name (e.g., "Melatonin") |
| `description` | String (metadata) | Enriched summary of the ingredient's use |
| `category` | String (metadata) | Primary category (e.g., "Sleep Support") |
| `benefits` | String (metadata) | Comma-separated benefit keywords |
| `aliases` | String (metadata) | Comma-separated alternative names |
| `risk_notes` | String (metadata) | Comma-separated risk/warning notes |
| `embedding` | Vector(384) | Local sentence-transformers embedding |
| `document` | String | Combined text of name + category + description + benefits + aliases + risk notes |

## Structured Ingredient Schema (Curated Seed)
Used for the 15 hand-enriched curated entries in `app/db/seed.py`.

```json
{
  "name": "Melatonin",
  "description": "Melatonin is an endogenous hormone that regulates circadian rhythm...",
  "category": "Sleep Support",
  "metadata": {
    "max_dosage_mg": 5,
    "benefits": ["sleep support", "circadian rhythm", "jet lag"],
    "aliases": ["sleep hormone"],
    "risk_notes": ["may cause morning drowsiness at higher doses"]
  }
}
```

## Dataset Preprocessing Strategy
1. **Source**: NIH Dietary Supplement Label Database (DSLD) — `DietarySupplementFacts_*.csv` files.
2. **Frequency Analysis**: `unique_ingredients.txt` contains ~76k ingredients ranked by occurrence count.
3. **Category Index**: Built from DSLD's `DSLD Ingredient Categories` column for each ingredient.
4. **Enrichment**:
   - Curated entries (15): Hand-written descriptions, benefits, aliases, and risk notes.
   - DSLD bulk (~485): Auto-generated descriptions with category tokens, name-specific overrides for common ingredients (MSM, DIM, Stinging Nettle, Glucuronolactone), and inferred benefits from category.
5. **Indexing**: 
   - Combine `name` + `category` + `description` + `benefits` + `aliases` + `risk_notes` into a single text block.
   - Embed locally using `sentence-transformers/all-MiniLM-L6-v2` (384-dim).
   - Upsert to ChromaDB with flattened metadata (lists → comma-separated strings).

## Storage Requirements
- **Vector DB**: Persistent local ChromaDB at path set by `CHROMA_DB_PATH` env var.
- **Raw Data**: DSLD CSVs in `data/raw/extracted_data/DSLD-full-database-CSV/`.
- **Processed**: `unique_ingredients.txt` in backend root.
