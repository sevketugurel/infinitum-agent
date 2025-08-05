# File: src/infinitum/services/user_context_service.py
"""
User Context and Preference Management Service
Handles user profiles, shopping preferences, and conversation history
"""

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timedelta
from ...infrastructure.persistence.firestore_client import db
from ...infrastructure.monitoring.logging.config import (
    get_agent_logger,
    log_function_call,
    log_business_event,
    EnhancedPerformanceTimer
)

logger = get_agent_logger("user_context")

class UserContextManager:
    """Manages user context, preferences, and shopping history"""
    
    def __init__(self):
        self.users_collection = db.collection('users')
        self.conversations_collection = db.collection('conversations')
    
    @log_function_call(logger=logger, log_performance=True)
    async def get_or_create_user_profile(self, user_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get existing user profile or create a new one"""
        with EnhancedPerformanceTimer(logger, "get_or_create_user_profile", user_id=user_id):
            try:
                # Try to get existing user
                user_doc = self.users_collection.document(user_id).get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    logger.info(f"Retrieved existing user profile: {user_id}", 
                               extra={'user_id': user_id, 'operation': 'user_profile_retrieval'})
                    
                    log_business_event(
                        logger,
                        "user_profile_accessed",
                        business_context="user_management",
                        user_id=user_id,
                        profile_age_days=(datetime.now() - datetime.fromisoformat(user_data.get('created_at', datetime.now().isoformat()))).days
                    )
                    return user_data
                
                # Create new user profile
                new_user = {
                    "user_id": user_id,
                    "created_at": datetime.now().isoformat(),
                    "last_active": datetime.now().isoformat(),
                    "preferences": self._get_default_preferences(),
                    "shopping_history": [],
                    "conversation_count": 0,
                    "favorite_categories": [],
                    "budget_ranges": {},
                    "metadata": metadata or {}
                }
                
                self.users_collection.document(user_id).set(new_user)
                logger.info(f"Created new user profile: {user_id}", 
                           extra={'user_id': user_id, 'operation': 'user_profile_creation'})
                
                log_business_event(
                    logger,
                    "new_user_registered",
                    business_context="user_acquisition",
                    user_id=user_id,
                    metadata_keys=list(metadata.keys()) if metadata else []
                )
                
                return new_user
                
            except Exception as e:
                logger.error(f"Error managing user profile for {user_id}: {e}", 
                           extra={'user_id': user_id, 'operation': 'user_profile_error'}, 
                           exc_info=True)
                return self._get_default_user_profile(user_id, metadata)
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
            "preferred_language": "en",
            "currency": "USD",
            "budget_conscious": False,
            "quality_focused": False,
            "brand_preferences": [],
            "category_interests": [],
            "price_range_preference": "mid_range",
            "delivery_preference": "standard",
            "review_importance": "high",
            "warranty_importance": "medium"
        }
    
    def _get_default_user_profile(self, user_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get default user profile when database is unavailable"""
        return {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "preferences": self._get_default_preferences(),
            "shopping_history": [],
            "conversation_count": 0,
            "metadata": metadata or {}
        }
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        try:
            user_ref = self.users_collection.document(user_id)
            user_ref.update({
                "preferences": preferences,
                "last_active": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
            logger.info(f"Updated preferences for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating preferences for {user_id}: {e}")
            return False
    
    async def save_conversation(self, user_id: str, session_id: str, query: str, 
                               response: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Save conversation to history"""
        try:
            conversation = {
                "conversation_id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": session_id,
                "query": query,
                "response": response,
                "context": context or {},
                "timestamp": datetime.now().isoformat(),
                "products_found": response.get("total_found", 0),
                "packages_created": response.get("package_count", 0),
                "category": self._extract_category_from_query(query)
            }
            
            # Save conversation
            conv_ref = self.conversations_collection.document(conversation["conversation_id"])
            conv_ref.set(conversation)
            
            # Update user's conversation count and history
            await self._update_user_shopping_history(user_id, conversation)
            
            logger.info(f"Saved conversation for user {user_id}: {conversation['conversation_id']}")
            return conversation["conversation_id"]
            
        except Exception as e:
            logger.error(f"Error saving conversation for {user_id}: {e}")
            return ""
    
    async def get_user_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent conversation history"""
        try:
            conversations = (
                self.conversations_collection
                .where("user_id", "==", user_id)
                .order_by("timestamp", direction="DESCENDING")
                .limit(limit)
                .get()
            )
            
            history = []
            for conv in conversations:
                data = conv.to_dict()
                # Remove large response data for history view
                if "response" in data:
                    data["response_summary"] = {
                        "total_found": data["response"].get("total_found", 0),
                        "package_count": data["response"].get("package_count", 0),
                        "summary": data["response"].get("summary", "")[:200]
                    }
                    del data["response"]
                history.append(data)
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history for {user_id}: {e}")
            return []
    
    async def analyze_user_context(self, user_id: str, current_query: str) -> Dict[str, Any]:
        """Analyze user context to enhance current query processing"""
        try:
            # Get user profile
            user_profile = await self.get_or_create_user_profile(user_id)
            
            # Get recent conversation history
            recent_conversations = await self.get_user_conversation_history(user_id, limit=5)
            
            # Analyze patterns
            context_analysis = {
                "user_profile": user_profile,
                "recent_interests": self._analyze_recent_interests(recent_conversations),
                "spending_patterns": self._analyze_spending_patterns(recent_conversations),
                "category_preferences": self._analyze_category_preferences(recent_conversations),
                "query_context": self._analyze_query_context(current_query, recent_conversations),
                "personalization_suggestions": self._generate_personalization_suggestions(user_profile, recent_conversations)
            }
            
            return context_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user context for {user_id}: {e}")
            return {"error": str(e)}
    
    def _extract_category_from_query(self, query: str) -> str:
        """Extract product category from query"""
        query_lower = query.lower()
        
        categories = {
            "electronics": ["headphones", "speaker", "camera", "phone", "laptop", "tablet"],
            "gaming": ["gaming", "game", "console", "controller", "keyboard", "mouse"],
            "content_creation": ["youtube", "streaming", "microphone", "webcam", "lighting"],
            "fitness": ["fitness", "exercise", "gym", "running", "sports"],
            "home": ["home", "kitchen", "furniture", "decor", "appliance"],
            "fashion": ["clothing", "shoes", "watch", "jewelry", "fashion"],
            "books": ["book", "kindle", "reading", "novel", "textbook"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _analyze_recent_interests(self, conversations: List[Dict[str, Any]]) -> List[str]:
        """Analyze user's recent shopping interests"""
        interests = []
        for conv in conversations:
            category = conv.get("category", "general")
            if category not in interests and category != "general":
                interests.append(category)
        return interests[:5]  # Top 5 recent interests
    
    def _analyze_spending_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's spending patterns from conversation history"""
        patterns = {
            "budget_conscious": 0,
            "premium_focused": 0,
            "average_products_per_search": 0,
            "most_active_categories": []
        }
        
        if not conversations:
            return patterns
        
        total_products = sum(conv.get("products_found", 0) for conv in conversations)
        patterns["average_products_per_search"] = round(total_products / len(conversations), 1)
        
        # Analyze query patterns for budget consciousness
        budget_keywords = ["cheap", "budget", "affordable", "economical", "under"]
        premium_keywords = ["premium", "high-quality", "best", "top", "professional"]
        
        for conv in conversations:
            query = conv.get("query", "").lower()
            if any(keyword in query for keyword in budget_keywords):
                patterns["budget_conscious"] += 1
            if any(keyword in query for keyword in premium_keywords):
                patterns["premium_focused"] += 1
        
        return patterns
    
    def _analyze_category_preferences(self, conversations: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze user's category preferences"""
        category_counts = {}
        for conv in conversations:
            category = conv.get("category", "general")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sort by frequency
        return dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _analyze_query_context(self, current_query: str, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze current query in context of user history"""
        context = {
            "is_repeat_category": False,
            "is_similar_to_recent": False,
            "suggested_refinements": [],
            "related_past_searches": []
        }
        
        current_category = self._extract_category_from_query(current_query)
        
        # Check if this is a repeat category
        recent_categories = [conv.get("category") for conv in conversations[:3]]
        if current_category in recent_categories:
            context["is_repeat_category"] = True
        
        # Find related past searches
        for conv in conversations:
            if conv.get("category") == current_category:
                context["related_past_searches"].append({
                    "query": conv.get("query"),
                    "timestamp": conv.get("timestamp"),
                    "products_found": conv.get("products_found", 0)
                })
        
        return context
    
    def _generate_personalization_suggestions(self, user_profile: Dict[str, Any], 
                                            conversations: List[Dict[str, Any]]) -> List[str]:
        """Generate personalization suggestions based on user data"""
        suggestions = []
        
        preferences = user_profile.get("preferences", {})
        
        # Budget-based suggestions
        if preferences.get("budget_conscious"):
            suggestions.append("Focus on value-for-money options")
        elif preferences.get("quality_focused"):
            suggestions.append("Prioritize high-quality, premium options")
        
        # Category-based suggestions
        recent_interests = self._analyze_recent_interests(conversations)
        if recent_interests:
            suggestions.append(f"Consider related products in {', '.join(recent_interests)}")
        
        # History-based suggestions
        if len(conversations) > 3:
            suggestions.append("Check your previous searches for comparison")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    async def _update_user_shopping_history(self, user_id: str, conversation: Dict[str, Any]):
        """Update user's shopping history with new conversation"""
        try:
            user_ref = self.users_collection.document(user_id)
            
            # Get current user data
            user_doc = user_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                
                # Update conversation count
                conversation_count = user_data.get("conversation_count", 0) + 1
                
                # Update shopping history (keep last 50 entries)
                shopping_history = user_data.get("shopping_history", [])
                shopping_history.append({
                    "conversation_id": conversation["conversation_id"],
                    "query": conversation["query"],
                    "category": conversation["category"],
                    "timestamp": conversation["timestamp"],
                    "products_found": conversation["products_found"]
                })
                
                # Keep only recent history
                if len(shopping_history) > 50:
                    shopping_history = shopping_history[-50:]
                
                # Update favorite categories
                favorite_categories = user_data.get("favorite_categories", [])
                category = conversation["category"]
                if category not in favorite_categories and category != "general":
                    favorite_categories.append(category)
                
                # Update user document
                user_ref.update({
                    "conversation_count": conversation_count,
                    "shopping_history": shopping_history,
                    "favorite_categories": favorite_categories,
                    "last_active": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error updating shopping history for {user_id}: {e}")

# Global instance
user_context_manager = UserContextManager()