#!/usr/bin/env python3
"""
DocuIntel AI - Launch Entrypoint
"""
import os
import sys
import uvicorn
from app.config import settings

def main():
    print("=" * 70)
    print(f"  {settings.PROJECT_NAME} (v{settings.VERSION})")
    print("=" * 70)
    print(f"  Web Dashboard:        http://localhost:{settings.PORT}")
    print(f"  Interactive API Docs: http://localhost:{settings.PORT}/docs")
    print(f"  Alternative Docs:     http://localhost:{settings.PORT}/redoc")
    print(f"  LLM Provider:         {settings.LLM_PROVIDER.upper()}")
    print(f"  Embedding Provider:   {settings.EMBEDDING_PROVIDER.upper()} ({settings.EMBEDDING_MODEL_NAME})")
    print(f"  API Key Configured:   {settings.is_api_key_configured()}")
    print("=" * 70)

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

if __name__ == "__main__":
    main()
