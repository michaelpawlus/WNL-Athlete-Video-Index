"""FastAPI application setup."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database.connection import engine, Base
from src.api.routers import athletes, videos, processing

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="WNL Athlete Video Index",
    description="Search for ninja warrior athletes in competition videos",
    version="1.0.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(athletes.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(processing.router, prefix="/api")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "name": "WNL Athlete Video Index API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
