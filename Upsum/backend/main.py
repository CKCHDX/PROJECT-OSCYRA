from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from search import router as search_router
from pathlib import Path

app = FastAPI(
    title="Upsum Backend", 
    description="API for Upsum — Project Nexus", 
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "https://upsum.oscyra.solutions",
        "http://upsum.oscyra.solutions",
        "https://oscyra.solutions",
        "*"  # Allow all for development - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(search_router)

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return JSONResponse({
        "status": "ok", 
        "message": "Upsum backend is running.",
        "version": "1.0.0",
        "features": [
            "Swedish Wikipedia integration",
            "Natural Input Language (NIL)",
            "Definiteness normalization",
            "Compound word handling"
        ]
    })

@app.get("/")
def serve_frontend():
    """Serve the frontend HTML file."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "frontend.html"
    return FileResponse(frontend_path)
