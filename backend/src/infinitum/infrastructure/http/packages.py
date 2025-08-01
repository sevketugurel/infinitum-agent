# File: src/infinitum/infrastructure/http/packages.py
"""
Packages API endpoint for Day 3 agent orchestration
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

from infinitum.application.use_cases.main_agent import process_user_query
from infinitum.infrastructure.external_services.serpapi_service import test_serpapi_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class PackageRequest(BaseModel):
    """Request model for package creation"""
    query: str = Field(..., description="User's product search query", min_length=1, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata about the request")
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="User preferences for search")

class PackageResponse(BaseModel):
    """Response model for package creation"""
    session_id: str
    status: str
    user_query: str
    metadata: Optional[Dict[str, Any]]
    processing_time_seconds: float
    steps_completed: int
    products_found: int
    response: Dict[str, Any]

class PackageErrorResponse(BaseModel):
    """Error response model"""
    session_id: str
    status: str
    user_query: str
    error: str
    processing_time_seconds: float
    steps_completed: int

@router.post("/packages", response_model=PackageResponse, status_code=201)
async def create_package(request: PackageRequest, background_tasks: BackgroundTasks):
    """
    Main endpoint for processing user queries through the 5-step agent workflow.
    
    This endpoint:
    1. Accepts user query and metadata
    2. Processes the query through the agent pipeline
    3. Returns curated product recommendations
    4. Logs everything to Firestore
    
    Args:
        request (PackageRequest): User query and metadata
        background_tasks (BackgroundTasks): FastAPI background tasks
        
    Returns:
        PackageResponse: Agent processing results with products
        
    Raises:
        HTTPException: If processing fails or invalid input
    """
    
    start_time = datetime.now()
    
    # Log incoming request
    logger.info(f"Processing package request: '{request.query[:100]}...'")
    
    try:
        # Prepare metadata
        metadata = request.metadata or {}
        metadata.update({
            "user_id": request.user_id,
            "preferences": request.preferences,
            "request_timestamp": start_time.isoformat(),
            "endpoint": "/api/v1/packages"
        })
        
        # Process the query through the agent pipeline
        result = await process_user_query(request.query, metadata)
        
        # Check if processing was successful
        if result["status"] == "error":
            logger.error(f"Agent processing failed: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Agent processing failed",
                    "error": result.get("error"),
                    "session_id": result.get("session_id"),
                    "suggestions": [
                        "Try a more specific product query",
                        "Check if the product exists",
                        "Try different keywords"
                    ]
                }
            )
        
        # Log successful processing
        logger.info(f"Package created successfully - Session: {result['session_id']}, Products: {result['products_found']}")
        
        # Schedule background cleanup if needed
        # background_tasks.add_task(cleanup_old_sessions)
        
        return PackageResponse(
            session_id=result["session_id"],
            status=result["status"],
            user_query=result["user_query"],
            metadata=result.get("metadata"),
            processing_time_seconds=result["processing_time_seconds"],
            steps_completed=result["steps_completed"],
            products_found=result["products_found"],
            response=result["response"]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        error_message = str(e)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.error(f"Unexpected error in create_package: {error_message}")
        
        # Return structured error response
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error during package processing",
                "error": error_message,
                "processing_time_seconds": processing_time,
                "suggestions": [
                    "Try again in a few moments",
                    "Check if your query is valid",
                    "Contact support if the issue persists"
                ]
            }
        )

@router.get("/packages/health")
async def packages_health_check():
    """
    Health check endpoint for the packages service.
    Tests all dependencies and returns status.
    """
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        # Test SerpAPI connection
        serpapi_test = test_serpapi_connection()
        health_status["checks"]["serpapi"] = {
            "status": "healthy" if serpapi_test["status"] == "success" else "unhealthy",
            "configured": serpapi_test["serpapi_configured"],
            "details": serpapi_test
        }
        
        # Test Gemini/Vertex AI (basic import test)
        try:
            from ..services.vertex_ai import ask_gemini
            health_status["checks"]["vertex_ai"] = {
                "status": "healthy",
                "message": "Import successful"
            }
        except Exception as e:
            health_status["checks"]["vertex_ai"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Crawl4AI service
        try:
            from ..services.crawl4ai_service import get_structured_data
            health_status["checks"]["crawl4ai"] = {
                "status": "healthy", 
                "message": "Import successful"
            }
        except Exception as e:
            health_status["checks"]["crawl4ai"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Firestore connection
        try:
            from ..db.firestore_client import db
            # Try a simple read operation
            collections = list(db.collections())
            health_status["checks"]["firestore"] = {
                "status": "healthy",
                "collections_count": len(collections)
            }
        except Exception as e:
            health_status["checks"]["firestore"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Determine overall status
        unhealthy_checks = [check for check in health_status["checks"].values() if check["status"] == "unhealthy"]
        if unhealthy_checks:
            health_status["status"] = "degraded"
            health_status["issues"] = len(unhealthy_checks)
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

