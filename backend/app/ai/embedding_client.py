import os
from sentence_transformers import SentenceTransformer


class EmbeddingClient:
    def __init__(self):
        self.model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.cache_folder = os.path.join(os.getcwd(), "model_cache")
        self._model = None
        # all-MiniLM-L6-v2 uses 384 dimensions. Hardcoding avoids the startup probe.
        self.dim = int(os.getenv("EMBEDDING_DIM", "384"))

    @property
    def model(self):
        if self._model is None:
            print(f"[EMBEDDING] Loading model {self.model_name} from {self.cache_folder}...", flush=True)
            self._model = SentenceTransformer(self.model_name, device="cpu", cache_folder=self.cache_folder)
        return self._model

    def embed(self, text: str):
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        v = self.model.encode([text], normalize_embeddings=True)[0]
        return v.astype(float).tolist()


embedding_client = EmbeddingClient()
