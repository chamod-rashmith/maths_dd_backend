"""
Maths DD Backend Entrypoint.
Exports `app` for Uvicorn / Google Cloud Run and supports direct local execution.
"""

from app.core.config import settings
from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
