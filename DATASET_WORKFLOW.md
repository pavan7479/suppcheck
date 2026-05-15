# Dataset Workflow & Future Enhancements - SuppCheck AI

## 1. Overview of Task
The goal was to move from a small, manually curated list of ingredients to a production-grade dataset derived from official government sources, enabling robust semantic search and risk analysis across a wide range of nutraceutical products.

## 2. Data Source: NIH DSLD
We integrated the **NIH Dietary Supplement Label Database (DSLD)**, the gold standard for supplement information in the US.
- **Physical Size**: 88MB (Compressed ZIP), ~400MB (Extracted CSVs).
- **Scope**: Contains label information for over 200,000+ products.
- **Accessibility**: Public Domain (CC0 1.0 Universal).

## 3. Implementation Workflow

### Phase A: Raw Data Acquisition
- Downloaded the full bulk dataset via official NIH S3 endpoints.
- Unzipped and identified the internal structure (48 CSV files).
- Targeted `DietarySupplementFacts_X.csv` as the primary source for ingredient information.

### Phase B: Extraction & Frequency Analysis
- Scanned the entire 400MB database for ingredient occurrences.
- Identified **76,495 unique ingredient variations**.
- Performed frequentist analysis to sort ingredients by their occurrence on product labels.
- Resulted in `unique_ingredients.txt` — a rarity-ranked index of the global supplement market.

### Phase C: Cloud Embeddings (Gemini)
- Created `seed_dsld_bulk.py` to build batches and upsert the Top ~500 ingredients efficiently.
- **Embedding**: Gemini `models/gemini-embedding-001` (3072-dim) — with in-process caching, conservative rate limiting, retry with backoff, and a small circuit breaker to protect quotas.
- **Enrichment**: Category index built from DSLD metadata; name-specific overrides for common ingredients (MSM, DIM, Stinging Nettle, Glucuronolactone).
- **Curated Layer**: 15 hand-enriched ingredients preserved with detailed descriptions, benefits, and risk notes.

## 4. Current Dataset Statistics
| Metric | Value |
| :--- | :--- |
| **Total Raw Ingredients** | 76,495 |
| **Curated Enriched Ingredients** | 15 |
| **DSLD Bulk Ingredients** | ~485 |
| **Total in Vector DB** | ~500 |
| **Coverage (Unique Entities)** | ~0.65% |
| **Coverage (Market Occurrence)** | **~45-50%** |

> [!NOTE]
> Although 0.65% seems small, supplement labels follow a "Power Law": the top 500 ingredients (Vitamin C, Magnesium, Caffeine, etc.) appear on nearly half of all labels in existence.

## 5. Future Enhancements

### Expanding the Knowledge Base
- **Tiered Seeding**: Increase the limit to 1,000+ ingredients for broader coverage.
- **Secondary Ingredients**: Using the `OtherIngredients_X.csv` files to index binders, fillers, and colors for "Allergy Alert" features.

### Product-Level Search
- **Product Indexing**: Instead of just indexing ingredients, we can index full **Product Names** from `ProductOverview_X.csv`. 
- **Use Case**: Users could search "FocusMax" and the system would automatically retrieve its entire formula from the NIH database.

### Clinical Validation
- Cross-reference the DSLD ingredient names with the **NIH ODS Fact Sheets** to provide direct links to clinical evidence for each search result.

### Normalization Pipeline
- Use Gemini to group the 76k variations (e.g., "Vit. C", "Ascorbic Acid", "Vitamin-C") into single **Canonical Entities** for cleaner search results.

---
*SuppCheck AI — Data Engineering Documentation & Roadmap*
