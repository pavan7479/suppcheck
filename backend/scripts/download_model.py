import os
from sentence_transformers import SentenceTransformer

def download_model():
    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    print(f"Downloading/Loading model: {model_name}...")
    # This will download the model to the default cache directory (~/.cache/torch/sentence_transformers)
    # which Render preserves between build and run if configured correctly, 
    # or at least ensures it's available in the current environment's disk.
    model = SentenceTransformer(model_name)
    print("Model downloaded successfully!")

if __name__ == "__main__":
    download_model()
