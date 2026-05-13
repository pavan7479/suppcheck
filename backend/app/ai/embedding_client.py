import os
from sentence_transformers import SentenceTransformer


class EmbeddingClient:
    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.model = SentenceTransformer(model_name, device="cpu")
        # Probe dimension once
        test_vec = self.model.encode(["dimension probe"], normalize_embeddings=True)
        self.dim = int(test_vec.shape[1])

    def embed(self, text: str):
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        v = self.model.encode([text], normalize_embeddings=True)[0]
        return v.astype(float).tolist()


embedding_client = EmbeddingClient()
