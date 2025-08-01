from fastapi import FastAPI
from infinitum.infrastructure.http.scrape import router as scrape_router
from infinitum.infrastructure.http.packages import router as packages_router
from infinitum.infrastructure.http.users import router as users_router
from infinitum.infrastructure.external_services.serpapi_service import get_serpapi_account_info
from infinitum.infrastructure.persistence.firestore_client import db  # This will initialize Firebase
from infinitum.infrastructure.external_services.vertex_ai import llm, ask_gemini, get_quota_status, get_cache_stats, clear_cache
from infinitum.infrastructure.logging_config import (
    setup_enhanced_logging, 
    get_agent_logger, 
    log_system_info,
    setup_debug_logging,
    log_business_event
)
from infinitum.infrastructure.middleware import setup_logging_middleware
from infinitum.infrastructure.logging_dashboard import create_dashboard_routes, setup_log_capture, get_logging_health
from infinitum.settings import settings
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Setup Enhanced Logging
setup_enhanced_logging()
setup_log_capture()

# Setup debug logging if enabled
if settings.ENABLE_DEBUG_LOGGING:
    setup_debug_logging()

logger = get_agent_logger("main")

app = FastAPI(
    title="Infinitum AI Agent", 
    version="1.0.0",
    description="AI-powered product search and recommendation agent"
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

# Include routers
app.include_router(scrape_router, prefix="/api/v1", tags=["scraping"])
app.include_router(packages_router, prefix="/api/v1", tags=["packages"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])

@app.get("/healthz")
def healthz():
    """Enhanced health check including logging system status"""
    logging_health = get_logging_health()
    return {
        "status": "ok",
        "timestamp": logger.handlers[0].formatter.formatTime(logger.makeRecord(
            logger.name, 20, "", 0, "", (), None
        )) if logger.handlers else None,
        "logging": logging_health
    }

@app.get("/admin/logging/health")
def logging_health():
    """Detailed logging system health check"""
    return get_logging_health()

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
        from .infrastructure.external_services.vertex_ai import llm
        
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