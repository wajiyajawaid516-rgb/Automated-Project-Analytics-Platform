"""
FastAPI Application Entry Point.

This is the main backend server for the Business Operations Platform.
It provides REST API endpoints for managing construction projects,
stakeholder directories, time tracking, and report generation.

Architecture:
    - Modular route registration via APIRouter
    - Dependency injection for database sessions
    - CORS enabled for frontend communication
    - Automatic OpenAPI documentation at /docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import projects, contacts, directory, time_entries, reports
from backend.api.models.database import init_db


# ---------------------------------------------------------------------------
# Application Setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Business Operations Platform API",
    description=(
        "REST API for managing construction projects, stakeholder directories, "
        "time tracking analytics, and automated report generation. "
        "Built with FastAPI and SQLAlchemy."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend (Streamlit) to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup Event
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    """Initialise database tables on application start."""
    init_db()


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------
app.include_router(projects.router, prefix="/api/v1", tags=["Projects"])
app.include_router(contacts.router, prefix="/api/v1", tags=["Contacts"])
app.include_router(directory.router, prefix="/api/v1", tags=["Project Directory"])
app.include_router(time_entries.router, prefix="/api/v1", tags=["Time Entries"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "Business Operations Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "api_version": "1.0.0",
    }
