"""
Maths DD - Content Automation & Management Backend
Designed for deployment on Google Cloud Run.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI application
app = FastAPI(
    title="Maths DD Backend API",
    description="Backend microservice for Maths DD content management and task automation.",
    version="1.0.0",
)

# Enable CORS for local testing and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """
    Root endpoint for basic service discovery.
    """
    return {
        "service": "Maths DD Backend",
        "status": "online",
        "environment": os.environ.get("ENV", "development"),
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    """
    Liveness and readiness probe for Google Cloud Run.
    Cloud Run uses this endpoint to check if the container is healthy and ready to receive traffic.
    """
    return {"status": "healthy", "service": "maths_dd_backend"}


if __name__ == "__main__":
    import uvicorn

    # Google Cloud Run dynamically injects the port using the PORT environment variable.
    # Default is 8080 when running locally.
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
