"""
Service interfaces - Define contracts for application services
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from ...core.entities.product import Product
from ...core.entities.user import User
from ...core.entities.package import Package
from ...core.value_objects.search_query import SearchQuery


class SearchService(ABC):
    """Service interface for search operations"""
    
    @abstractmethod
    async def search_products(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for products based on parameters.
        
        Args:
            search_params: Dictionary containing search parameters
            
        Returns:
            Dictionary with 'products' list and 'total_count'
        """
        pass
    
    @abstractmethod
    async def search_packages(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for packages based on parameters.
        
        Args:
            search_params: Dictionary containing search parameters
            
        Returns:
            Dictionary with 'packages' list and 'total_count'
        """
        pass
    
    @abstractmethod
    async def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get search suggestions for a query"""
        pass
    
    @abstractmethod
    async def get_trending_searches(self, limit: int = 10) -> List[str]:
        """Get trending search queries"""
        pass


class RecommendationService(ABC):
    """Service interface for recommendation operations"""
    
    @abstractmethod
    async def get_similar_products(self, product_id: str, user_id: Optional[str] = None,
                                 limit: int = 5) -> List[Product]:
        """Get products similar to the given product"""
        pass
    
    @abstractmethod
    async def get_personalized_recommendations(self, user_id: str,
                                             limit: int = 10) -> List[Product]:
        """Get personalized product recommendations for a user"""
        pass
    
    @abstractmethod
    async def get_trending_products(self, category: Optional[str] = None,
                                  limit: int = 10) -> List[Product]:
        """Get trending products"""
        pass
    
    @abstractmethod
    async def get_popular_in_category(self, category: str,
                                    limit: int = 10) -> List[Product]:
        """Get popular products in a specific category"""
        pass
    
    @abstractmethod
    async def get_frequently_bought_together(self, product_id: str,
                                           limit: int = 5) -> List[Product]:
        """Get products frequently bought together with the given product"""
        pass
    
    @abstractmethod
    async def get_recommended_packages(self, user_id: str, programming_language: Optional[str] = None,
                                     limit: int = 10) -> List[Package]:
        """Get recommended packages for a user"""
        pass


class ReviewService(ABC):
    """Service interface for review operations"""
    
    @abstractmethod
    async def get_product_reviews(self, product_id: str, limit: int = 20,
                                offset: int = 0) -> List[Dict[str, Any]]:
        """Get reviews for a product"""
        pass
    
    @abstractmethod
    async def add_review(self, user_id: str, product_id: str, rating: float,
                        comment: Optional[str] = None) -> Dict[str, Any]:
        """Add a review for a product"""
        pass
    
    @abstractmethod
    async def update_review(self, review_id: str, rating: Optional[float] = None,
                          comment: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing review"""
        pass
    
    @abstractmethod
    async def delete_review(self, review_id: str, user_id: str) -> bool:
        """Delete a review"""
        pass
    
    @abstractmethod
    async def get_review_summary(self, product_id: str) -> Dict[str, Any]:
        """Get review summary for a product (average rating, distribution, etc.)"""
        pass
    
    @abstractmethod
    async def moderate_review(self, review_id: str, action: str) -> bool:
        """Moderate a review (approve, reject, flag)"""
        pass


class UserService(ABC):
    """Service interface for user operations"""
    
    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> User:
        """Update user information"""
        pass
    
    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        pass
    
    @abstractmethod
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        pass
    
    @abstractmethod
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> None:
        """Update user preferences"""
        pass
    
    @abstractmethod
    async def get_user_activity(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user activity history"""
        pass
    
    @abstractmethod
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account"""
        pass


class NotificationService(ABC):
    """Service interface for notification operations"""
    
    @abstractmethod
    async def send_email(self, to_email: str, subject: str, body: str,
                        template: Optional[str] = None) -> bool:
        """Send an email notification"""
        pass
    
    @abstractmethod
    async def send_push_notification(self, user_id: str, title: str, message: str,
                                   data: Optional[Dict[str, Any]] = None) -> bool:
        """Send a push notification"""
        pass
    
    @abstractmethod
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Send an SMS notification"""
        pass
    
    @abstractmethod
    async def create_notification(self, user_id: str, notification_type: str,
                                title: str, message: str,
                                data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an in-app notification"""
        pass
    
    @abstractmethod
    async def get_user_notifications(self, user_id: str, limit: int = 20,
                                   unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        pass
    
    @abstractmethod
    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        pass


class AnalyticsService(ABC):
    """Service interface for analytics operations"""
    
    @abstractmethod
    async def track_event(self, event_type: str, user_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         properties: Optional[Dict[str, Any]] = None) -> None:
        """Track an analytics event"""
        pass
    
    @abstractmethod
    async def track_search(self, query: SearchQuery, user_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         results_count: int = 0) -> None:
        """Track a search event"""
        pass
    
    @abstractmethod
    async def track_product_view(self, product_id: str, user_id: Optional[str] = None,
                               session_id: Optional[str] = None) -> None:
        """Track a product view event"""
        pass
    
    @abstractmethod
    async def get_search_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get search analytics for a date range"""
        pass
    
    @abstractmethod
    async def get_product_analytics(self, product_id: str, start_date: datetime,
                                  end_date: datetime) -> Dict[str, Any]:
        """Get analytics for a specific product"""
        pass
    
    @abstractmethod
    async def get_user_analytics(self, user_id: str, start_date: datetime,
                               end_date: datetime) -> Dict[str, Any]:
        """Get analytics for a specific user"""
        pass


class CacheService(ABC):
    """Service interface for caching operations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        pass
    
    @abstractmethod
    async def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None) -> Any:
        """Get from cache or set using factory function if not exists"""
        pass


class ExternalApiService(ABC):
    """Service interface for external API operations"""
    
    @abstractmethod
    async def fetch_product_data(self, product_identifier: str,
                               source: str) -> Optional[Dict[str, Any]]:
        """Fetch product data from external source"""
        pass
    
    @abstractmethod
    async def fetch_price_data(self, product_identifier: str,
                             sources: List[str]) -> List[Dict[str, Any]]:
        """Fetch price data from multiple sources"""
        pass
    
    @abstractmethod
    async def fetch_reviews(self, product_identifier: str,
                          source: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch reviews from external source"""
        pass
    
    @abstractmethod
    async def validate_product_url(self, url: str) -> Dict[str, Any]:
        """Validate and extract information from product URL"""
        pass


class AIService(ABC):
    """Service interface for AI operations"""
    
    @abstractmethod
    async def analyze_search_intent(self, query: str) -> Dict[str, Any]:
        """Analyze search query intent using AI"""
        pass
    
    @abstractmethod
    async def generate_product_description(self, product_data: Dict[str, Any]) -> str:
        """Generate product description using AI"""
        pass
    
    @abstractmethod
    async def extract_product_features(self, product_text: str) -> List[str]:
        """Extract product features from text using AI"""
        pass
    
    @abstractmethod
    async def classify_product_category(self, product_data: Dict[str, Any]) -> str:
        """Classify product category using AI"""
        pass
    
    @abstractmethod
    async def generate_search_suggestions(self, query: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate search suggestions using AI"""
        pass
    
    @abstractmethod
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using AI"""
        pass
    
    @abstractmethod
    async def detect_spam_review(self, review_text: str) -> Dict[str, Any]:
        """Detect if a review is spam using AI"""
        pass


class VectorSearchService(ABC):
    """Service interface for vector search operations"""
    
    @abstractmethod
    async def index_product(self, product: Product) -> None:
        """Index a product for vector search"""
        pass
    
    @abstractmethod
    async def search_similar_products(self, query_vector: List[float],
                                    limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar products using vector similarity"""
        pass
    
    @abstractmethod
    async def get_product_embedding(self, product_id: str) -> Optional[List[float]]:
        """Get vector embedding for a product"""
        pass
    
    @abstractmethod
    async def update_product_embedding(self, product_id: str, embedding: List[float]) -> None:
        """Update vector embedding for a product"""
        pass
    
    @abstractmethod
    async def delete_product_embedding(self, product_id: str) -> bool:
        """Delete vector embedding for a product"""
        pass