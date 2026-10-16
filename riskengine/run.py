"""RiskEngine Platform Runner.

Starts the FastAPI backend and serves the compiled frontend single-page application.
Visit: http://localhost:8000
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("  RiskEngine: Financial AI/NLP Risk Quantification Platform")
    print("  Endpoints:")
    print("    - Web Application: http://localhost:8000")
    print("    - Interactive API Docs: http://localhost:8000/docs")
    print("    - Health Check: http://localhost:8000/health")
    print("=" * 70)

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
