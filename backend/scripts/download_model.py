import os
from sentence_transformers import SentenceTransformer

def download_model():
    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    cache_folder = os.path.join(os.getcwd(), "model_cache")
    print(f"Downloading/Loading model: {model_name} to {cache_folder}...")
    # Force download to project directory
    model = SentenceTransformer(model_name, cache_folder=cache_folder)
    print("Model downloaded successfully!")

if __name__ == "__main__":
    download_model()
