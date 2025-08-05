"""
Repository interfaces - Define contracts for data access
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from ...core.entities.product import Product
from ...core.entities.user import User
from ...core.entities.search_session import SearchSession
from ...core.entities.package import Package


class Repository(ABC):
    """Base repository interface"""
    
    @abstractmethod
    async def save(self, entity) -> None:
        """Save an entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity by ID"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str):
        """Get an entity by ID"""
        pass


class ProductRepository(Repository):
    """Repository interface for Product entities"""
    
    @abstractmethod
    async def save(self, product: Product) -> None:
        """Save a product"""
        pass
    
    @abstractmethod
    async def delete(self, product_id: str) -> bool:
        """Delete a product by ID"""
        pass
    
    @abstractmethod
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get a product by ID"""
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> List[Product]:
        """Find products by name"""
        pass
    
    @abstractmethod
    async def find_by_category(self, category: str, limit: int = 20, offset: int = 0) -> Tuple[List[Product], int]:
        """Find products by category with pagination"""
        pass
    
    @abstractmethod
    async def find_by_brand(self, brand: str, limit: int = 20, offset: int = 0) -> Tuple[List[Product], int]:
        """Find products by brand with pagination"""
        pass
    
    @abstractmethod
    async def find_with_filters(self, filters: Dict[str, Any], 
                               limit: int = 20, offset: int = 0, 
                               sort_by: str = "relevance") -> Tuple[List[Product], int]:
        """Find products with complex filters"""
        pass
    
    @abstractmethod
    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None,
                    limit: int = 20, offset: int = 0) -> Tuple[List[Product], int]:
        """Search products by text query"""
        pass
    
    @abstractmethod
    async def get_popular_products(self, category: Optional[str] = None,
                                  limit: int = 20) -> List[Product]:
        """Get popular products"""
        pass
    
    @abstractmethod
    async def get_featured_products(self, limit: int = 20) -> List[Product]:
        """Get featured products"""
        pass
    
    @abstractmethod
    async def update_stats(self, product_id: str, stats: Dict[str, Any]) -> None:
        """Update product statistics"""
        pass


class UserRepository(Repository):
    """Repository interface for User entities"""
    
    @abstractmethod
    async def save(self, user: User) -> None:
        """Save a user"""
        pass
    
    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete a user by ID"""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        pass
    
    @abstractmethod
    async def find_by_role(self, role: str, limit: int = 20, offset: int = 0) -> Tuple[List[User], int]:
        """Find users by role"""
        pass
    
    @abstractmethod
    async def get_user_bookmarks(self, user_id: str) -> List[str]:
        """Get user's bookmarked product IDs"""
        pass
    
    @abstractmethod
    async def add_bookmark(self, user_id: str, product_id: str) -> None:
        """Add a product to user's bookmarks"""
        pass
    
    @abstractmethod
    async def remove_bookmark(self, user_id: str, product_id: str) -> None:
        """Remove a product from user's bookmarks"""
        pass
    
    @abstractmethod
    async def get_user_ratings(self, user_id: str) -> Dict[str, float]:
        """Get user's product ratings"""
        pass
    
    @abstractmethod
    async def set_user_rating(self, user_id: str, product_id: str, rating: float) -> None:
        """Set user's rating for a product"""
        pass


class SearchSessionRepository(Repository):
    """Repository interface for SearchSession entities"""
    
    @abstractmethod
    async def save(self, session: SearchSession) -> None:
        """Save a search session"""
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a search session by ID"""
        pass
    
    @abstractmethod
    async def get_by_id(self, session_id: str) -> Optional[SearchSession]:
        """Get a search session by ID"""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: str, limit: int = 20, offset: int = 0) -> Tuple[List[SearchSession], int]:
        """Get search sessions by user ID"""
        pass
    
    @abstractmethod
    async def get_active_sessions(self, user_id: Optional[str] = None) -> List[SearchSession]:
        """Get active search sessions"""
        pass
    
    @abstractmethod
    async def expire_old_sessions(self, older_than: datetime) -> int:
        """Expire sessions older than specified time"""
        pass
    
    @abstractmethod
    async def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get analytics data for a session"""
        pass


class PackageRepository(Repository):
    """Repository interface for Package entities"""
    
    @abstractmethod
    async def save(self, package: Package) -> None:
        """Save a package"""
        pass
    
    @abstractmethod
    async def delete(self, package_id: str) -> bool:
        """Delete a package by ID"""
        pass
    
    @abstractmethod
    async def get_by_id(self, package_id: str) -> Optional[Package]:
        """Get a package by ID"""
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Package]:
        """Get a package by name"""
        pass
    
    @abstractmethod
    async def find_by_category(self, category: str, limit: int = 20, offset: int = 0) -> Tuple[List[Package], int]:
        """Find packages by category"""
        pass
    
    @abstractmethod
    async def find_by_language(self, language: str, limit: int = 20, offset: int = 0) -> Tuple[List[Package], int]:
        """Find packages by programming language"""
        pass
    
    @abstractmethod
    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None,
                    limit: int = 20, offset: int = 0) -> Tuple[List[Package], int]:
        """Search packages by text query"""
        pass
    
    @abstractmethod
    async def get_popular_packages(self, category: Optional[str] = None,
                                  limit: int = 20) -> List[Package]:
        """Get popular packages"""
        pass
    
    @abstractmethod
    async def get_trending_packages(self, days: int = 7, limit: int = 20) -> List[Package]:
        """Get trending packages"""
        pass
    
    @abstractmethod
    async def update_stats(self, package_id: str, stats: Dict[str, Any]) -> None:
        """Update package statistics"""
        pass


class ReviewRepository(Repository):
    """Repository interface for product/package reviews"""
    
    @abstractmethod
    async def save(self, review: Dict[str, Any]) -> None:
        """Save a review"""
        pass
    
    @abstractmethod
    async def delete(self, review_id: str) -> bool:
        """Delete a review by ID"""
        pass
    
    @abstractmethod
    async def get_by_id(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get a review by ID"""
        pass
    
    @abstractmethod
    async def get_by_product_id(self, product_id: str, limit: int = 20, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Get reviews for a product"""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: str, limit: int = 20, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Get reviews by a user"""
        pass
    
    @abstractmethod
    async def get_average_rating(self, product_id: str) -> Optional[float]:
        """Get average rating for a product"""
        pass
    
    @abstractmethod
    async def get_rating_distribution(self, product_id: str) -> Dict[int, int]:
        """Get rating distribution for a product"""
        pass


class AnalyticsRepository(Repository):
    """Repository interface for analytics data"""
    
    @abstractmethod
    async def record_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Record an analytics event"""
        pass
    
    @abstractmethod
    async def get_events(self, event_type: str, start_date: datetime, 
                        end_date: datetime, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get analytics events"""
        pass
    
    @abstractmethod
    async def get_user_analytics(self, user_id: str, start_date: datetime,
                               end_date: datetime) -> Dict[str, Any]:
        """Get analytics for a specific user"""
        pass
    
    @abstractmethod
    async def get_product_analytics(self, product_id: str, start_date: datetime,
                                  end_date: datetime) -> Dict[str, Any]:
        """Get analytics for a specific product"""
        pass
    
    @abstractmethod
    async def get_search_analytics(self, start_date: datetime,
                                 end_date: datetime) -> Dict[str, Any]:
        """Get search analytics"""
        pass