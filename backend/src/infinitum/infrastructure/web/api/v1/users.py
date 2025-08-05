# File: src/infinitum/infrastructure/http/users.py
"""
User management API endpoints for context and preferences
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .....application.services.user_context_service import user_context_manager

logger = logging.getLogger(__name__)
router = APIRouter()

class UserPreferences(BaseModel):
    """User preferences model"""
    preferred_language: str = "en"
    currency: str = "USD"
    budget_conscious: bool = False
    quality_focused: bool = False
    brand_preferences: List[str] = []
    category_interests: List[str] = []
    price_range_preference: str = "mid_range"
    delivery_preference: str = "standard"
    review_importance: str = "high"
    warranty_importance: str = "medium"

class UserProfileResponse(BaseModel):
    """User profile response model"""
    user_id: str
    preferences: Dict[str, Any]
    conversation_count: int
    favorite_categories: List[str]
    created_at: str
    last_active: str

class ConversationHistoryResponse(BaseModel):
    """Conversation history response model"""
    conversation_id: str
    query: str
    timestamp: str
    category: str
    products_found: int
    response_summary: Dict[str, Any]

@router.get("/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """Get user profile and preferences"""
    try:
        logger.info(f"Getting profile for user: {user_id}")
        
        profile = await user_context_manager.get_or_create_user_profile(user_id)
        
        return UserProfileResponse(
            user_id=profile["user_id"],
            preferences=profile.get("preferences", {}),
            conversation_count=profile.get("conversation_count", 0),
            favorite_categories=profile.get("favorite_categories", []),
            created_at=profile.get("created_at", ""),
            last_active=profile.get("last_active", "")
        )
        
    except Exception as e:
        logger.error(f"Error getting user profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")

@router.put("/users/{user_id}/preferences")
async def update_user_preferences(user_id: str, preferences: UserPreferences):
    """Update user preferences"""
    try:
        logger.info(f"Updating preferences for user: {user_id}")
        
        preferences_dict = preferences.model_dump()
        success = await user_context_manager.update_user_preferences(user_id, preferences_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        return {
            "status": "success",
            "message": "Preferences updated successfully",
            "user_id": user_id,
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

@router.get("/users/{user_id}/conversations", response_model=List[ConversationHistoryResponse])
async def get_user_conversations(user_id: str, limit: int = 10):
    """Get user's conversation history"""
    try:
        logger.info(f"Getting conversation history for user: {user_id}")
        
        if limit < 1 or limit > 50:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")
        
        conversations = await user_context_manager.get_user_conversation_history(user_id, limit)
        
        return [
            ConversationHistoryResponse(
                conversation_id=conv["conversation_id"],
                query=conv["query"],
                timestamp=conv["timestamp"],
                category=conv.get("category", "general"),
                products_found=conv.get("products_found", 0),
                response_summary=conv.get("response_summary", {})
            )
            for conv in conversations
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")

@router.get("/users/{user_id}/context")
async def get_user_context(user_id: str, current_query: Optional[str] = None):
    """Get comprehensive user context analysis"""
    try:
        logger.info(f"Getting context analysis for user: {user_id}")
        
        if not current_query:
            current_query = "general shopping inquiry"
        
        context = await user_context_manager.analyze_user_context(user_id, current_query)
        
        return {
            "status": "success",
            "user_id": user_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting context for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze user context: {str(e)}")

@router.delete("/users/{user_id}/conversations/{conversation_id}")
async def delete_conversation(user_id: str, conversation_id: str):
    """Delete a specific conversation from user history"""
    try:
        logger.info(f"Deleting conversation {conversation_id} for user: {user_id}")
        
        # TODO: Implement conversation deletion
        # For now, return a placeholder response
        return {
            "status": "success",
            "message": "Conversation deletion not yet implemented",
            "user_id": user_id,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id} for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.get("/users/{user_id}/recommendations")
async def get_personalized_recommendations(user_id: str):
    """Get personalized shopping recommendations based on user history"""
    try:
        logger.info(f"Getting recommendations for user: {user_id}")
        
        # Get user context
        context = await user_context_manager.analyze_user_context(user_id, "")
        
        recommendations = {
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "category_suggestions": context.get("recent_interests", []),
            "personalization_tips": context.get("personalization_suggestions", []),
            "spending_insights": context.get("spending_patterns", {}),
            "next_steps": [
                "Explore trending products in your favorite categories",
                "Set up price alerts for items you're watching",
                "Check out new arrivals in your preferred brands"
            ]
        }
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting recommendations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@router.get("/users/health")
async def users_health_check():
    """Health check for user service"""
    try:
        # Test user context manager
        test_user_id = "health_check_user"
        profile = await user_context_manager.get_or_create_user_profile(test_user_id)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "user_service": "operational",
            "firestore_connection": "healthy" if profile else "degraded"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }