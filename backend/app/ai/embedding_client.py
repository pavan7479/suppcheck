import os
import time
from typing import List, Dict
from dotenv import load_dotenv
import httpx
from collections import deque
try:
    # Preferred new SDK
    from google import genai as genai_new
except Exception:
    genai_new = None
try:
    # Fallback deprecated SDK
    import google.generativeai as genai
except Exception:
    genai = None


class EmbeddingClient:
    def __init__(self):
        # Load env once here to support script usage as well
        load_dotenv(override=True)
        # Provider selection kept for future extension
        self.provider = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
        # Prefer new GEMINI_API_KEY, fall back to GOOGLE_API_KEY for compatibility
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        if not api_key:
            # Do not raise here to avoid blocking FastAPI startup; calls will fail gracefully
            print("[EMBEDDING] Warning: GEMINI_API_KEY/GOOGLE_API_KEY not set. Embedding calls will fail.", flush=True)
        else:
            try:
                if genai_new is not None:
                    self._client = genai_new.Client(api_key=api_key)
                    self._use_new_sdk = True
                elif genai is not None:
                    try:
                        genai.configure(api_key=api_key, client_options={"api_version": "v1"})
                    except TypeError:
                        genai.configure(api_key=api_key)
                    self._client = None
                    self._use_new_sdk = False
                else:
                    print("[EMBEDDING] No Gemini SDK available. Install 'google-genai'.", flush=True)
            except Exception as e:
                print(f"[EMBEDDING] Failed to configure Gemini SDK: {e}", flush=True)
        self._api_key = api_key

        # Model id can be overridden via GEMINI_EMBED_MODEL or (legacy) EMBEDDING_MODEL
        env_model = os.getenv("GEMINI_EMBED_MODEL", os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"))
        # Prepare candidates with and without 'models/' prefix for best compatibility
        def variants(m: str):
            m = (m or "").strip()
            if not m:
                return []
            with_prefix = m if m.startswith("models/") else f"models/{m}"
            no_prefix = m[7:] if m.startswith("models/") else m
            return [with_prefix, no_prefix]
        self._candidates = []
        for base in [env_model, "gemini-embedding-001", "embedding-001", "text-embedding-004"]:
            for v in variants(base):
                if v not in self._candidates:
                    self._candidates.append(v)
        # Selected model id is resolved lazily on first use
        self.model_id = None
        # Default dimension; prefer explicit EMBEDDING_DIM, else infer from configured model
        _dim_env = os.getenv("EMBEDDING_DIM")
        if _dim_env is not None and _dim_env.strip() != "":
            try:
                self.dim = int(_dim_env)
            except Exception:
                self.dim = 768
        else:
            if "gemini-embedding-001" in (env_model or "").lower():
                self.dim = 3072
            else:
                self.dim = 768

        # Simple in-memory cache to avoid duplicate calls (cap to control memory)
        self._cache: Dict[str, List[float]] = {}
        self._cache_cap = int(os.getenv("EMBEDDING_CACHE_CAP", "400"))
        # Rate limiting & circuit breaker (safe usage in low quota envs)
        self._rpm = int(os.getenv("EMBED_RPM", "5"))  # default cap ~300/day if sustained, fine for 100/day bursts
        self._calls = deque()
        self._fail_count = 0
        self._fail_threshold = int(os.getenv("EMBED_FAIL_THRESHOLD", "3"))
        self._cooldown_sec = int(os.getenv("EMBED_COOLDOWN_SEC", "600"))
        self._opened_until = 0.0

    def _extract_vector(self, res) -> List[float]:
        try:
            # google-generativeai may return dict-like or object with .embedding
            if res is None:
                return []
            # google-genai new SDK: object with .embeddings -> list of items with .values
            v = getattr(res, "embeddings", None)
            if isinstance(v, list) and v:
                first = v[0]
                vals = getattr(first, "values", None) or getattr(first, "embedding", None)
                if isinstance(vals, list):
                    return [float(x) for x in vals]
            # google-genai common case: object with .embedding.values
            emb_obj = getattr(res, "embedding", None)
            if emb_obj is not None:
                vals = getattr(emb_obj, "values", None)
                if isinstance(vals, list):
                    return [float(x) for x in vals]
            if isinstance(res, dict):
                v = res.get("embedding")
                if isinstance(v, dict) and "values" in v:
                    v = v.get("values")
                if isinstance(v, list):
                    return [float(x) for x in v]
                # Batch responses may use 'data' or 'embeddings'
                if "data" in res and res["data"]:
                    v = res["data"][0].get("embedding")
                    if isinstance(v, dict) and "values" in v:
                        v = v.get("values")
                    if isinstance(v, list):
                        return [float(x) for x in v]
            # Object-style
            v = getattr(res, "embedding", None)
            if isinstance(v, dict) and "values" in v:
                v = v.get("values")
            if isinstance(v, list):
                return [float(x) for x in v]
        except Exception:
            pass
        return []

    def _l2_normalize(self, vec: List[float]) -> List[float]:
        try:
            import math
            s = math.sqrt(sum((x * x) for x in vec)) or 1.0
            return [x / s for x in vec]
        except Exception:
            return vec

    def _with_retry(self, fn, *args, **kwargs):
        delay = 1.0
        for attempt in range(4):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == 3:
                    raise
                print(f"[EMBEDDING] API error, retrying in {delay:.1f}s: {type(e).__name__}: {e}", flush=True)
                time.sleep(delay)
                delay *= 2

    def _resolve_or_try_fallback(self, content: str, task: str):
        """Try the configured model; on NotFound/InvalidArgument fallback through known candidates.
        Returns (vector, model_id) or ([], None) on failure.
        """
        errs = []
        def is_model_mismatch(err: Exception) -> bool:
            msg = str(err).lower()
            return ("not found" in msg) or ("model" in msg and "available" in msg) or ("unsupported" in msg)

        # Build ordered list: currently selected -> candidates
        order = []
        if self.model_id:
            order.append(self.model_id)
        for m in self._candidates:
            if m not in order:
                order.append(m)

        for m in order:
            try:
                res = self._embed_call(m, content, task)
                vec = self._extract_vector(res)
                if vec:
                    if self.model_id != m:
                        self.model_id = m
                        print(f"[EMBEDDING] Using model: {m}", flush=True)
                        low = (m or "").lower()
                        # Auto-adjust dimension for common Gemini embedding models
                        if "gemini-embedding-001" in low:
                            self.dim = 3072
                        elif "text-embedding-004" in low or "embedding-001" in low:
                            # Keep 768 unless user overrides via EMBEDDING_DIM
                            try:
                                if int(os.getenv("EMBEDDING_DIM", str(self.dim))) == self.dim:
                                    self.dim = 768
                            except Exception:
                                self.dim = 768
                    return vec, m
            except Exception as e:
                errs.append((m, f"{type(e).__name__}: {e}"))
                # Try next candidate if looks like a model/availability mismatch
                if not is_model_mismatch(e):
                    # Non-model error (e.g., network), stop early
                    break
        # Log last error summary
        if errs:
            last = errs[-1]
            print(f"[EMBEDDING] All candidates failed; last error with {last[0]} -> {last[1]}", flush=True)
        return [], None

    def _embed_call(self, model: str, content: str, task: str):
        # Preferred new SDK
        if getattr(self, "_use_new_sdk", False) and genai_new is not None and getattr(self, "_client", None) is not None:
            # Try a few calling conventions for compatibility across versions
            last_err = None
            for call in (
                # client.embeddings.embed_content with 'content'
                lambda: self._client.embeddings.embed_content(model=model, content=content),
                # client.embeddings.embed_content with 'contents' (list)
                lambda: self._client.embeddings.embed_content(model=model, contents=[content]),
                # client.embeddings.embed_content with 'input'
                lambda: self._client.embeddings.embed_content(model=model, input=content),
                # client.models.embed_content variants (without task_type)
                lambda: self._client.models.embed_content(model=model, contents=content),
                lambda: self._client.models.embed_content(model=model, contents=[content]),
            ):
                try:
                    return call()
                except Exception as e:
                    last_err = e
            raise last_err or RuntimeError("embed_content not available in google-genai client")
        # Fallback deprecated SDK
        if genai is None:
            raise RuntimeError("No Gemini SDK available")
        try:
            return self._with_retry(genai.embed_content, model=model, content=content, task_type=task)
        except Exception as e:
            last_err = e
            # REST fallback using httpx
            model_path = model if model.startswith("models/") else f"models/{model}"
            bases = ["https://generativelanguage.googleapis.com/v1", "https://generativelanguage.googleapis.com/v1beta"]
            bodies = [
                {"model": model_path, "content": {"parts": [{"text": content}] }},
                {"model": model_path, "input": content},
            ]
            for base in bases:
                url = f"{base}/{model_path}:embedContent"
                for body in bodies:
                    try:
                        with httpx.Client(timeout=15) as client:
                            r = client.post(url, params={"key": self._api_key}, json=body)
                        r.raise_for_status()
                        return r.json()
                    except Exception as ee:
                        last_err = ee
            raise last_err

    def embed_text(self, text: str, kind: str = "query"):
        try:
            if not isinstance(text, str):
                text = str(text) if text is not None else ""
            key = text.strip()
            task = "RETRIEVAL_QUERY" if (kind or "query").lower().startswith("q") else "RETRIEVAL_DOCUMENT"
            ckey = f"{task}::{key}"
            if ckey in self._cache:
                return self._cache[ckey]
            # Circuit breaker: if open, avoid calling API
            now = time.time()
            if now < self._opened_until:
                print("[EMBEDDING] Circuit open, skipping embed call.", flush=True)
                return []
            # Rate limit per minute if configured
            if self._rpm > 0:
                # drop entries older than 60s
                while self._calls and now - self._calls[0] > 60.0:
                    self._calls.popleft()
                if len(self._calls) >= self._rpm:
                    print("[EMBEDDING] Rate limit reached; skipping embed call.", flush=True)
                    return []
                self._calls.append(now)
            # Single call to Gemini embeddings
            # Resolve model and embed with fallback if needed
            vec, used = self._resolve_or_try_fallback(key, task)
            if not vec:
                raise RuntimeError("Empty embedding returned or model unavailable")
            vec = self._l2_normalize(vec)
            # cache (bounded)
            if len(self._cache) >= self._cache_cap:
                try:
                    # Pop arbitrary item to cap memory
                    self._cache.pop(next(iter(self._cache)))
                except Exception:
                    self._cache.clear()
            self._cache[ckey] = vec
            # reset failure counter on success
            self._fail_count = 0
            return vec
        except Exception as e:
            print(f"[EMBEDDING] Failed to embed text: {type(e).__name__}: {e}", flush=True)
            # register failure and potentially open circuit
            try:
                self._fail_count += 1
                if self._fail_count >= self._fail_threshold:
                    self._opened_until = time.time() + float(self._cooldown_sec)
                    self._fail_count = 0
                    print(f"[EMBEDDING] Circuit opened for {self._cooldown_sec}s due to repeated failures.", flush=True)
            except Exception:
                pass
            # Return an empty vector to signal failure to callers (they should handle gracefully)
            return []

    def embed_batch(self, texts: List[str], kind: str = "document") -> List[List[float]]:
        out: List[List[float]] = []
        for t in texts or []:
            out.append(self.embed_text(t, kind=kind))
        return out

    # Backward compatibility
    def embed(self, text: str):
        return self.embed_text(text, kind="document")


embedding_client = EmbeddingClient()
