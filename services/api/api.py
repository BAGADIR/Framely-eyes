"""Main FastAPI application for Framely-Eyes analyzer."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.router import router
from services.api.deps import settings


# Create FastAPI app
app = FastAPI(
    title="Framely-Eyes Video Analyzer",
    description="GPU-first, ultra-detailed Video Perception OS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router, prefix="", tags=["analysis"])


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    print("=" * 60)
    print("Framely-Eyes Video Analyzer")
    print("=" * 60)
    print(f"Store path: {settings.STORE_PATH}")
    print(f"Max video size: {settings.MAX_VIDEO_MB} MB")
    print(f"GPU available: {__import__('torch').cuda.is_available()}")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    print("Shutting down Framely-Eyes analyzer...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
