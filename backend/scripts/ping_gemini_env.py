import os
import sys
from pathlib import Path

from dotenv import load_dotenv, find_dotenv, dotenv_values
import google.generativeai as genai


def _list_key_suffixes(p: Path):
    if not p.exists():
        return []
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    import re
    toks = re.findall(r"AIza[0-9A-Za-z_\-]+", txt)
    return sorted(set(["..." + t[-4:] for t in toks if len(t) >= 4]))


def main():
    backend_dir = Path(__file__).resolve().parents[1]
    root_dir = backend_dir.parent
    backend_env = backend_dir / ".env"
    root_env = root_dir / ".env"

    # Discover which .env would be picked by load_dotenv() from current CWD
    chosen_env_path = Path(find_dotenv()) if find_dotenv() else None

    print("[ENV] Python:", sys.executable)
    print("[ENV] CWD:", os.getcwd())
    print("[ENV] SDK:", genai.__version__)
    print("[ENV] backend/.env exists:", backend_env.exists())
    print("[ENV] root/.env exists:", root_env.exists())
    print("[ENV] load_dotenv() would pick:", str(chosen_env_path) if chosen_env_path else "<none>")
    print("[ENV] backend/.env keys:", _list_key_suffixes(backend_env))
    print("[ENV] root/.env keys:", _list_key_suffixes(root_env))

    # Now actually load using default search (like GeminiClient)
    load_dotenv(override=True)
    key = os.getenv("GOOGLE_API_KEY") or ""
    print("[ENV] Loaded GOOGLE_API_KEY suffix:", ("..." + key[-4:]) if key else "<none>")

    model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    print("[TEST] Model:", model_id)

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_id)
        r = model.generate_content("ping")
        print("[TEST] OK, response length:", len(getattr(r, "text", "")))
        print((r.text or "")[:120])
    except Exception as e:
        print("[TEST] ERROR:", type(e).__name__, str(e))
        raise


if __name__ == "__main__":
    main()
