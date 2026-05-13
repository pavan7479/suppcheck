import os
import sys
from pathlib import Path
import json
import re

import google.generativeai as genai


def find_api_keys(dotenv_path: Path):
    keys = []
    if not dotenv_path.exists():
        return keys
    seen = set()
    auto_idx = 1
    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        # Extract any AIza tokens found anywhere in the line (even if commented)
        inline_tokens = re.findall(r"AIza[0-9A-Za-z_\-]+", line)
        for tok in inline_tokens:
            if tok not in seen:
                name = f"GOOGLE_API_KEY_AUTO_{auto_idx}"
                auto_idx += 1
                keys.append((name, tok))
                seen.add(tok)
        if "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if not value:
            continue
        # Extract all AIza-like tokens from the value (handles comma/space separated lists)
        tokens = re.findall(r"AIza[0-9A-Za-z_\-]+", value)
        if tokens:
            for tok in tokens:
                if tok not in seen:
                    keys.append((f"{name}", tok))
                    seen.add(tok)
            continue
        if ("GOOGLE_API_KEY" in name) or ("GEMINI" in name) or re.match(r"^AIza[0-9A-Za-z_\-]+$", value):
            if value not in seen:
                keys.append((name, value))
                seen.add(value)
    return keys

def find_api_keys_env():
    keys = []
    seen = set()
    for name, value in os.environ.items():
        if not value:
            continue
        if ("GOOGLE_API_KEY" in name) or ("GEMINI" in name) or re.match(r"^AIza[0-9A-Za-z_\-]+$", value):
            if value not in seen:
                keys.append((name, value))
                seen.add(value)
    return keys


def test_key(name: str, value: str):
    results = {"key": name, "prefix": (value[:6] + "..."), "suffix": ("..." + value[-4:] if len(value) >= 4 else value), "tests": []}
    gen_models = [
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-8b",
        "models/gemini-flash-lite-latest",
        "models/gemini-pro",
        "models/gemini-1.5-pro",
    ]

    genai.configure(api_key=value)

    for m in gen_models:
        entry = {"type": "generate", "model": m}
        try:
            model = genai.GenerativeModel(m)
            r = model.generate_content("hi")
            ok = bool(getattr(r, "text", ""))
            entry.update({"ok": ok, "detail": (r.text[:80] + "...") if ok else None})
        except Exception as e:
            entry.update({"ok": False, "error": f"{type(e).__name__}: {str(e)}"})
        results["tests"].append(entry)

    return results


def main():
    base = Path(__file__).resolve().parent.parent
    dotenv_path = base / ".env"

    keys = find_api_keys(dotenv_path)
    # Supplement with any keys in the current environment
    for k in find_api_keys_env():
        if k[1] not in [v for (_, v) in keys]:
            keys.append(k)
    if not keys:
        single = os.getenv("GOOGLE_API_KEY")
        if single:
            keys = [("GOOGLE_API_KEY", single)]
    if not keys:
        print("No GOOGLE_API_KEY* entries found in .env or environment.")
        sys.exit(1)

    all_results = []
    for name, value in keys:
        print(f"\n== Testing {name} ({value[:6]}...) ==")
        res = test_key(name, value)
        for t in res["tests"]:
            if t["type"] == "generate":
                if t.get("ok"):
                    print(f"[GEN OK] {t['model']}")
                else:
                    print(f"[GEN ERR] {t['model']}: {t.get('error')}")
            else:
                if t.get("ok"):
                    print(f"[EMB OK] {t['model']} dim={t.get('dim')}")
                else:
                    print(f"[EMB ERR] {t['model']}: {t.get('error')}")
        all_results.append(res)

    print("\nJSON Summary:")
    print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
