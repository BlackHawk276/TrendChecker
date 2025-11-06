"""
Main FastAPI application entry point.
E-Commerce Intelligence SaaS Platform.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import close_db, init_db
from app.services.redis_service import RedisService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting E-Commerce Intelligence SaaS API...")
    print(f"📊 Environment: {'Development' if settings.debug else 'Production'}")
    print(f"🔧 API Version: {settings.app_version}")

    # Initialize Redis connection
    try:
        await RedisService.get_redis()
        print("✅ Redis connection established")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {str(e)}")
        print("   Some features (token blacklist, rate limiting) may not work")

    # Initialize database (only in development)
    if settings.debug:
        print("🗄️  Initializing database tables...")
        # Uncomment to auto-create tables (use Alembic migrations in production)
        # await init_db()

    yield

    # Shutdown
    print("👋 Shutting down E-Commerce Intelligence SaaS API...")

    # Close Redis connection
    try:
        await RedisService.close()
        print("✅ Redis connection closed")
    except Exception as e:
        print(f"⚠️  Error closing Redis: {str(e)}")

    # Close database connections
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-Commerce Intelligence SaaS Platform API - Discover trending products and stores",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"] if settings.allowed_methods == "*" else settings.allowed_methods.split(","),
    allow_headers=["*"] if settings.allowed_headers == "*" else settings.allowed_headers.split(","),
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the API status and version.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": "development" if settings.debug else "production",
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    Returns welcome message and API information.
    """
    return JSONResponse(
        content={
            "message": "Welcome to E-Commerce Intelligence SaaS API",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }
    )


# Include routers
from app.routers import auth, stores, users

app.include_router(
    auth.router,
    prefix=f"{settings.api_v1_prefix}/auth",
    tags=["Authentication"]
)

app.include_router(
    stores.router,
    prefix=f"{settings.api_v1_prefix}/stores",
    tags=["Stores"]
)

app.include_router(
    users.router,
    prefix=f"{settings.api_v1_prefix}/users",
    tags=["Users"]
)

# Additional routers to be added later
# from app.routers import products
# app.include_router(products.router, prefix=f"{settings.api_v1_prefix}/products", tags=["Products"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled exceptions.
    """
    if settings.debug:
        # In debug mode, show full error details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__,
            }
        )
    else:
        # In production, hide error details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred. Please try again later.",
            }
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
