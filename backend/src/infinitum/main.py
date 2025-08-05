from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime

# Import routers
from .infrastructure.web.api.v1.search import router as search_router
from .infrastructure.web.api.v1.packages import router as packages_router
from .infrastructure.web.api.v1.users import router as users_router
from .infrastructure.web.api.v1.chat import router as chat_router

# Import services and utilities
from .infrastructure.external.search.serpapi_client import get_serpapi_account_info
from .infrastructure.persistence.firestore_client import db  # This will initialize Firebase
from .infrastructure.external.ai.vertex_ai_client import llm, ask_gemini, get_quota_status, get_cache_stats, clear_cache
from .infrastructure.monitoring.logging.config import (
    setup_enhanced_logging,
    get_agent_logger,
    log_system_info,
    setup_debug_logging,
    log_business_event
)
from .infrastructure.web.middleware.logging_middleware import setup_logging_middleware
from .infrastructure.monitoring.logging.dashboard import create_dashboard_routes, setup_log_capture, get_logging_health
from .config.settings import settings

# Setup Enhanced Logging
setup_enhanced_logging()
setup_log_capture()

# Setup debug logging if enabled
if settings.ENABLE_DEBUG_LOGGING:
    setup_debug_logging()

logger = get_agent_logger("main")

# Create FastAPI application
app = FastAPI(
    title="Infinitum AI Agent", 
    version="1.0.0",
    description="AI-powered product search and recommendation agent with full-stack integration",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration for Frontend Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "http://localhost:4173",  # Vite preview server
        "https://infinitum-agent.web.app",  # Firebase hosting
        "https://infinitum-agent.firebaseapp.com",  # Firebase hosting
        # Note: Wildcard subdomains not supported in CORS
        # Add specific domains as needed for production deployments
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
    ],
    expose_headers=["*"]
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "*.run.app",  # Google Cloud Run
        "*.appspot.com",  # Google App Engine
        "infinitum-agent.web.app",
        "infinitum-agent.firebaseapp.com"
    ]
)

# Setup logging middleware and dashboard
setup_logging_middleware(app)
create_dashboard_routes(app)

# Log system startup information
log_system_info(logger)
log_business_event(
    logger, 
    "application_startup", 
    business_context="system_initialization",
    version="1.0.0",
    environment=settings.ENVIRONMENT
)

# Include API routers with proper prefixes
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(packages_router, prefix="/api/v1", tags=["packages"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

# Health check endpoints
@app.get("/healthz")
def healthz():
    """Enhanced health check including logging system status"""
    logging_health = get_logging_health()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "logging": logging_health,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health/detailed")
def detailed_health_check():
    """Comprehensive health check for all services"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "services": {}
    }
    
    # Check Firebase/Firestore
    try:
        collections = list(db.collections())
        health_status["services"]["firestore"] = {
            "status": "healthy",
            "collections_count": len(collections)
        }
    except Exception as e:
        health_status["services"]["firestore"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Vertex AI
    try:
        if llm is None:
            health_status["services"]["vertex_ai"] = {
                "status": "unavailable",
                "message": "LLM not initialized (likely quota exhausted)"
            }
        else:
            health_status["services"]["vertex_ai"] = {
                "status": "healthy",
                "message": "LLM initialized successfully"
            }
    except Exception as e:
        health_status["services"]["vertex_ai"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check SerpAPI
    try:
        account_info = get_serpapi_account_info()
        if "error" in account_info:
            health_status["services"]["serpapi"] = {
                "status": "unhealthy",
                "error": account_info["error"]
            }
        else:
            health_status["services"]["serpapi"] = {
                "status": "healthy",
                "searches_left": account_info.get("total_searches_left", "unknown")
            }
    except Exception as e:
        health_status["services"]["serpapi"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return health_status

@app.get("/admin/logging/health")
def logging_health():
    """Detailed logging system health check"""
    return get_logging_health()

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Service status endpoints
@app.get("/serpapi-status")
async def serpapi_status():
    """Check SerpAPI account status and quota"""
    try:
        account_info = get_serpapi_account_info()
        if "error" in account_info:
            return {"status": "error", "message": account_info["error"]}
        
        return {
            "status": "success", 
            "account_info": account_info,
            "searches_left": account_info.get("total_searches_left", "unknown"),
            "monthly_usage": account_info.get("this_month_usage", "unknown")
        }
    except Exception as e:
        return {"status": "error", "message": f"SerpAPI status check failed: {str(e)}"}

@app.get("/llm-status")
async def llm_status():
    """Check LLM (Gemini) status and availability"""
    try:
        from .infrastructure.external.ai.vertex_ai_client import llm
        
        if llm is None:
            return {
                "status": "unavailable",
                "message": "LLM not initialized (likely quota exhausted)",
                "fallback_active": True,
                "system_operational": True,
                "note": "System continues to work with real product database and intelligent fallbacks"
            }
        
        # Test LLM with a simple call
        try:
            test_response = llm.call("Hello")
            if test_response:
                return {
                    "status": "available",
                    "message": "LLM is working properly",
                    "fallback_active": False,
                    "system_operational": True
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"LLM test failed: {str(e)}",
                "fallback_active": True,
                "system_operational": True,
                "note": "System continues to work with intelligent fallbacks"
            }
            
    except Exception as e:
        return {
            "status": "error", 
            "message": f"LLM status check failed: {str(e)}",
            "fallback_active": True,
            "system_operational": True
        }

@app.get("/quota-status")
async def quota_status():
    """Get current quota usage and cache statistics."""
    try:
        quota_info = get_quota_status()
        cache_info = get_cache_stats()
        
        return {
            "status": "success",
            "quota": quota_info,
            "cache": cache_info,
            "recommendations": _get_quota_recommendations(quota_info)
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get quota status: {str(e)}"}

@app.post("/clear-cache")
async def clear_response_cache():
    """Clear the LLM response cache."""
    try:
        clear_cache()
        return {"status": "success", "message": "Cache cleared successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to clear cache: {str(e)}"}

# Frontend integration endpoints
@app.get("/api/config")
async def get_frontend_config():
    """Get configuration for frontend application"""
    return {
        "api_base_url": f"http://localhost:{settings.PORT}" if settings.ENVIRONMENT == "development" else "https://your-cloud-run-url.run.app",
        "websocket_url": f"ws://localhost:{settings.PORT}" if settings.ENVIRONMENT == "development" else "wss://your-cloud-run-url.run.app",
        "firebase_config": {
            "project_id": settings.FIREBASE_PROJECT_ID,
            "auth_domain": f"{settings.FIREBASE_PROJECT_ID}.firebaseapp.com",
            "api_key": settings.FIREBASE_WEB_API_KEY if hasattr(settings, 'FIREBASE_WEB_API_KEY') else None
        },
        "features": {
            "auth_enabled": True,
            "real_time_chat": True,
            "vector_search": True,
            "analytics": settings.ENABLE_METRICS
        },
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Infinitum AI Agent API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/healthz",
        "api_endpoints": {
            "chat": "/api/v1/chat",
            "packages": "/api/v1/packages", 
            "users": "/api/v1/users",
            "websocket": "/api/v1/chat/ws/{user_id}"
        }
    }

def _get_quota_recommendations(quota_info: dict) -> list:
    """Generate recommendations based on quota usage."""
    recommendations = []
    usage = quota_info["usage_percentage"]
    
    if usage >= 90:
        recommendations.extend([
            "🚨 URGENT: Consider upgrading to paid tier - quota nearly exhausted",
            "💾 Enable aggressive caching to reduce API calls",
            "⏸️  Consider pausing non-essential features"
        ])
    elif usage >= 75:
        recommendations.extend([
            "⚠️  Consider upgrading to paid tier soon",
            "🔄 Review and optimize prompt efficiency",
            "📊 Monitor usage closely"
        ])
    elif usage >= 50:
        recommendations.extend([
            "📊 Monitor usage - halfway to daily limit",
            "💡 Consider implementing request prioritization"
        ])
    else:
        recommendations.append("✅ Quota usage is healthy")
    
    if quota_info["cache_entries"] < 10:
        recommendations.append("💾 Cache is building up - responses will be faster soon")
    
    return recommendations

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": "The requested resource was not found",
        "status_code": 404,
        "path": str(request.url.path)
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "status_code": 500,
        "path": str(request.url.path)
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("🚀 Infinitum AI Agent API starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.PORT}")
    logger.info("✅ Application startup complete")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("🛑 Infinitum AI Agent API shutting down...")
    logger.info("✅ Application shutdown complete")