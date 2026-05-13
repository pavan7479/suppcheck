from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from app.api.endpoints import router as api_router

load_dotenv()

app = FastAPI(
    title="SuppCheck AI API",
    description="Backend for supplement formulation analysis",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*50, flush=True)
    print("SUPPCHECK BACKEND IS LIVE", flush=True)
    print("Listening for requests...", flush=True)
    print("="*50 + "\n", flush=True)

@app.get("/")
async def root():
    return {"message": "Welcome to SuppCheck AI API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # Use reload=False on Windows to avoid child-process stdout issues.
    # Set RELOAD=1 env var if you need auto-reload during development.
    reload_mode = os.getenv("RELOAD", "0").lower() in ("1", "true", "yes", "on")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_mode,
        log_level="info",
        access_log=True
    )
