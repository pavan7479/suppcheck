import chromadb
from chromadb.config import Settings
import os
import re
from dotenv import load_dotenv
from app.ai.embedding_client import embedding_client

# Ensure .env is loaded for all contexts (scripts, API, REPL)
load_dotenv()

class VectorService:
    def __init__(self):
        self.db_path = os.getenv("CHROMA_DB_PATH") or os.path.join(os.getcwd(), "chroma_db")
        print(f"[VECTOR] ChromaDB path: {self.db_path}", flush=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = None
        self._ensure_collection()
        self.min_sim = float(os.getenv("SEARCH_MIN_SIM", "0.35"))
        self.alias_map = {
            "l-leucine": "Leucine",
            "leucine": "Leucine",
            "vitamin b9": "Folate",
            "folic acid": "Folate",
            "ascorbic acid": "Vitamin C",
            "retinol": "Vitamin A",
            "vitamin b1": "Thiamine",
            "vitamin b2": "Riboflavin",
            "vitamin b3": "Niacin",
            "niacinamide": "Niacinamide",
            "vitamin b5": "Pantothenic Acid",
            "vitamin b6": "Pyridoxine",
            "vitamin b12": "Vitamin B12",
            "cyanocobalamin": "Vitamin B12",
            "riboflavin": "Riboflavin",
            "thiamine": "Thiamine",
            "calciferol": "Vitamin D",
            "cholecalciferol": "Vitamin D3",
            "coq10": "Coenzyme Q10 (CoQ10)",
            "ubiquinone": "Coenzyme Q10 (CoQ10)",
            "ubiquinol": "Coenzyme Q10 (CoQ10)",
            "ps": "Phosphatidylserine",
            "paracetamol": "Acetaminophen",
            "acetylsalicylic acid": "Aspirin",
        }
        self.intent_keywords = {
            "sleep": ["sleep", "insomnia", "circadian", "melatonin", "relaxation"],
            "stress": ["stress", "anxiety", "cortisol", "calm", "adaptogen"],
            "energy": ["energy", "fatigue", "stamina", "alertness"],
            "focus": ["focus", "attention", "concentration", "nootropic", "cognitive"],
            "recovery": ["recovery", "inflammation", "soreness", "muscle"],
            "immunity": ["immune", "immunity", "cold", "flu", "infection"],
            "digestive": ["digest", "digestion", "digestive", "enzyme", "gut", "microbiome", "probiotic", "lactobacillus", "bifid"],
        }

    def _flatten_metadata(self, metadata: dict) -> dict:
        """Chroma metadata accepts only str, int, float, bool. Convert lists to comma-separated strings."""
        if metadata is None:
            return {"benefits": "", "aliases": "", "risk_notes": ""}
        out = {}
        for k, v in metadata.items():
            if isinstance(v, list):
                out[k] = ", ".join([str(x) for x in v])
            elif isinstance(v, (str, int, float, bool)):
                out[k] = v
            elif v is None:
                out[k] = ""
            else:
                out[k] = str(v)
        out.setdefault("benefits", "")
        out.setdefault("aliases", "")
        out.setdefault("risk_notes", "")
        return out

    def _parse_list_field(self, value) -> list:
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str):
            parts = re.split(r"[,;]", value)
            return [p.strip() for p in parts if p and p.strip()]
        return []

    def _current_dim(self) -> int:
        return getattr(embedding_client, "dim", int(os.getenv("EMBEDDING_DIM", "768")))

    def _ensure_collection(self):
        dim = self._current_dim()
        self.collection = self.client.get_or_create_collection(
            name="ingredients_kb",
            metadata={"hnsw:space": "cosine", "dimension": dim}
        )
        return self.collection

    def clear_collection(self):
        """Deletes and recreates the collection to clear all data."""
        try:
            self.client.delete_collection(name="ingredients_kb")
            print("Collection 'ingredients_kb' deleted.")
        except Exception as e:
            print(f"Collection 'ingredients_kb' did not exist or could not be deleted: {e}")
        
        self._ensure_collection()
        print("Collection 'ingredients_kb' recreated.")

    def add_ingredient(self, name: str, description: str, category: str, metadata: dict = None):
        if metadata is None:
            metadata = {}
        benefits = self._parse_list_field(metadata.get("benefits", []))
        aliases = self._parse_list_field(metadata.get("aliases", []))
        risk_notes = self._parse_list_field(metadata.get("risk_notes", []))
        parts = [name, category, description]
        if benefits:
            parts.append("Benefits: " + ", ".join([str(b) for b in benefits]))
        if aliases:
            parts.append("Also known as: " + ", ".join([str(a) for a in aliases]))
        if risk_notes:
            parts.append("Risks: " + "; ".join([str(r) for r in risk_notes]))
        embed_text = ". ".join([p for p in parts if p]).strip()
        embedding = embedding_client.embed_text(embed_text, kind="document")
        if not embedding:
            print(f"[VECTOR] Skipping '{name}' due to embedding failure.", flush=True)
            return
        
        doc_id = name.lower().replace(" ", "_")
        # Use upsert to avoid duplicate ID errors when re-seeding
        coll = self._ensure_collection()
        coll.upsert(
            embeddings=[embedding],
            documents=[embed_text],
            metadatas=[{**self._flatten_metadata(metadata), "name": name, "category": category, "description": description}],
            ids=[doc_id]
        )

    def add_ingredients_batch(self, items: list):
        """Batch upsert ingredients. Each item: {name, description, category, metadata}.
        Skips items that fail to embed.
        """
        if not items:
            return
        names = []
        docs = []
        metas = []
        ids = []
        texts = []
        for it in items:
            name = it.get("name") or "Unknown"
            description = it.get("description") or ""
            category = it.get("category") or "General"
            metadata = it.get("metadata") or {}
            benefits = self._parse_list_field(metadata.get("benefits", []))
            aliases = self._parse_list_field(metadata.get("aliases", []))
            risk_notes = self._parse_list_field(metadata.get("risk_notes", []))
            parts = [name, category, description]
            if benefits:
                parts.append("Benefits: " + ", ".join([str(b) for b in benefits]))
            if aliases:
                parts.append("Also known as: " + ", ".join([str(a) for a in aliases]))
            if risk_notes:
                parts.append("Risks: " + "; ".join([str(r) for r in risk_notes]))
            embed_text = ". ".join([p for p in parts if p]).strip()
            texts.append(embed_text)
            names.append(name)
            docs.append(embed_text)
            metas.append({**self._flatten_metadata(metadata), "name": name, "category": category, "description": description})
            ids.append(name.lower().replace(" ", "_"))

        vectors = embedding_client.embed_batch(texts, kind="document")
        # Filter out failed ones (empty vectors)
        final_embs, final_docs, final_metas, final_ids = [], [], [], []
        for i, v in enumerate(vectors):
            if v:
                final_embs.append(v)
                final_docs.append(docs[i])
                final_metas.append(metas[i])
                final_ids.append(ids[i])
            else:
                print(f"[VECTOR] Skipping '{names[i]}' due to embedding failure.", flush=True)
        if not final_embs:
            return
        coll = self._ensure_collection()
        coll.upsert(
            embeddings=final_embs,
            documents=final_docs,
            metadatas=final_metas,
            ids=final_ids,
        )

    def _normalize_name(self, name: str) -> str:
        """Normalizes ingredient names to help with deduplication (e.g., L-Leucine -> Leucine)."""
        if not name:
            return "Unknown"
        
        # Lowercase and strip whitespace
        name = name.lower().strip()
        
        # Remove common prefixes/chemical forms
        name = re.sub(r'^[ld]-\s*', '', name) # L-Theanine -> theanine
        name = re.sub(r'\s+hcl$', '', name)   # Betaine HCl -> betaine
        name = re.sub(r'\s+anhydrous$', '', name)
        name = re.sub(r'\s+monohydrate$', '', name)
        name = re.sub(r'\s+extract$', '', name)
        
        # Remove anything in parentheses (e.g. "Vitamin C (as Ascorbic Acid)" -> "Vitamin C")
        name = re.sub(r'\(.*\)', '', name).strip()
        
        # Title case for consistency
        return name.title()

    def _canonicalize(self, name: str) -> str:
        if not name:
            return ""
        key = self._normalize_name(name).lower()
        return self.alias_map.get(key, self._normalize_name(name))

    def _intent_boost(self, query: str, category: str, benefits: list, document: str) -> float:
        q = (query or "").lower()
        c = (category or "").lower()
        btxt = ", ".join(benefits or []).lower()
        dtxt = (document or "").lower()
        boost = 0.0
        if any(k in q for k in self.intent_keywords.get("sleep", [])) and ("sleep" in c or "sleep" in btxt or "melatonin" in dtxt or "circadian" in dtxt):
            boost += 0.08
        if any(k in q for k in self.intent_keywords.get("stress", [])) and ("stress" in c or "stress" in btxt or "adaptogen" in dtxt or "cortisol" in dtxt):
            boost += 0.08
        if any(k in q for k in self.intent_keywords.get("energy", []) + self.intent_keywords.get("focus", [])) and ("energy" in c or "focus" in c or "nootropic" in dtxt or "alertness" in dtxt):
            boost += 0.06
        if any(k in q for k in self.intent_keywords.get("recovery", [])) and ("recovery" in c or "inflammation" in btxt or "muscle" in dtxt):
            boost += 0.05
        if any(k in q for k in self.intent_keywords.get("immunity", [])) and ("immune" in c or "immune" in btxt or "vitamin c" in dtxt or "zinc" in dtxt):
            boost += 0.06
        if any(k in q for k in self.intent_keywords.get("digestive", [])) and ("digest" in c or "digestive" in c or "digest" in btxt or "enzyme" in dtxt or "probiotic" in dtxt or "lactobacillus" in dtxt or "bifido" in dtxt or "microbiome" in dtxt or "gut" in btxt):
            boost += 0.07
        return boost

    def search_ingredients(self, query: str, n_results: int = 10):
        print(f"\n[SEARCH] Query: {query}", flush=True)
        try:
            canonical_query = self._canonicalize(query)
            query_text = canonical_query if canonical_query else query
            query_embedding = embedding_client.embed_text(query_text, kind="query")
            if not query_embedding:
                print("[SEARCH] Embedding failed for query; returning no results.", flush=True)
                return []
            
            coll = self._ensure_collection()
            results = coll.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]
            )
            
            # Process and deduplicate results
            processed_results = []
            seen_normalized_names = set()

            if not results:
                print("[SEARCH] No results returned by ChromaDB.", flush=True)
                return []

            if results.get('metadatas') and results['metadatas'] and results['metadatas'][0]:
                raw_count = len(results['metadatas'][0])
            elif results.get('documents') and results['documents'] and results['documents'][0]:
                raw_count = len(results['documents'][0])
            else:
                print("[SEARCH] No result rows present (no metadatas/documents).", flush=True)
                return []
            print(f"[SEARCH] Processing {raw_count} raw candidates...", flush=True)

            # Prepare scores first to enable relative scaling
            distances = [results['distances'][0][i] if results.get('distances') else 1.0 for i in range(raw_count)]
            sims = [max(0.0, 1.0 - float(d)) for d in distances]

            for i in range(raw_count):
                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                if not metadata:
                    metadata = {}

                # Get name from metadata or ID
                name = metadata.get('name')
                if not name:
                    # Fall back to any available id if returned; otherwise Unknown
                    if results.get('ids') and results['ids'] and len(results['ids'][0]) > i:
                        rid = results['ids'][0][i]
                        name = rid.replace("_", " ").title() if rid else 'Unknown'
                    else:
                        name = 'Unknown'

                normalized_name = self._normalize_name(name)
                alias_keys = set()
                for a in self._parse_list_field(metadata.get('aliases')):
                    try:
                        alias_keys.add(self._normalize_name(a))
                    except Exception:
                        continue

                # Simple deduplication based on normalized name
                if normalized_name in seen_normalized_names or any(a in seen_normalized_names for a in alias_keys):
                    continue
                seen_normalized_names.add(normalized_name)
                for a in alias_keys:
                    seen_normalized_names.add(a)
                abs_sim = sims[i]
                if abs_sim < self.min_sim:
                    continue

                description = metadata.get('description') if metadata.get('description') else (
                    results['documents'][0][i] if (results.get('documents') and results['documents'][0][i]) else "No description available."
                )
                category = metadata.get('category', 'General')
                benefits = self._parse_list_field(metadata.get('benefits'))
                boost = self._intent_boost(query_text, category, benefits, description)
                score = min(1.0, abs_sim + boost)
                explanation = "Matched based on semantic profile."
                if description and isinstance(description, str) and '.' in description:
                    explanation = description.split('.')[0] + '.'

                processed_results.append({
                    "name": name,
                    "description": description,
                    "category": category,
                    "score": round(score, 2),
                    "explanation": explanation
                })
                
            
            # If nothing passed the initial threshold, relax progressively to avoid empty results
            if not processed_results:
                for fallback in [max(0.30, self.min_sim - 0.05), 0.25]:
                    temp_results = []
                    seen_fallback = set()
                    for i in range(raw_count):
                        metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                        if not metadata:
                            metadata = {}

                        name = metadata.get('name') or 'Unknown'
                        normalized_name = self._normalize_name(name)
                        alias_keys = set()
                        for a in self._parse_list_field(metadata.get('aliases')):
                            try:
                                alias_keys.add(self._normalize_name(a))
                            except Exception:
                                continue

                        if normalized_name in seen_fallback or any(a in seen_fallback for a in alias_keys):
                            continue
                        abs_sim = sims[i]
                        if abs_sim < fallback:
                            continue
                        seen_fallback.add(normalized_name)
                        for a in alias_keys:
                            seen_fallback.add(a)

                        description = metadata.get('description') if metadata.get('description') else (
                            results['documents'][0][i] if (results.get('documents') and results['documents'][0][i]) else "No description available."
                        )
                        category = metadata.get('category', 'General')
                        benefits = self._parse_list_field(metadata.get('benefits'))
                        boost = self._intent_boost(query_text, category, benefits, description)
                        score = min(1.0, abs_sim + boost)
                        explanation = "Matched based on semantic profile."
                        if description and isinstance(description, str) and '.' in description:
                            explanation = description.split('.')[0] + '.'

                        temp_results.append({
                            "name": name,
                            "description": description,
                            "category": category,
                            "score": round(score, 2),
                            "explanation": explanation
                        })
                    if temp_results:
                        print(f"[SEARCH] Relaxed threshold to {fallback:.2f} and found {len(temp_results)} results.", flush=True)
                        processed_results = temp_results
                        break

            processed_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            processed_results = processed_results[:min(6, n_results)]
            print(f"[SEARCH] Returning {len(processed_results)} unique results.", flush=True)
            return processed_results
        except Exception as e:
            print(f"[SEARCH] Error during search: {str(e)}", flush=True)
            raise e

vector_service = VectorService()
