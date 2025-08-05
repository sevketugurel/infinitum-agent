"""
Product Search Service - Main application service for product search operations
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..commands.search_products_command import SearchProductsCommand, SearchProductsResult
from ..commands.handlers.search_products_handler import SearchProductsHandler
from ..queries.get_product_query import GetProductQuery, GetProductResult
from ..queries.handlers.get_product_handler import GetProductHandler
from ...core.entities.user import User
from ...core.entities.search_session import SearchSession
from ...core.value_objects.search_query import SearchQuery
from ...core.value_objects.user_preferences import UserPreferences
from ...shared.interfaces.repositories import (
    ProductRepository, UserRepository, SearchSessionRepository
)
from ...shared.interfaces.services import (
    SearchService, RecommendationService, AnalyticsService, NotificationService
)
from ...shared.exceptions import ValidationError, NotFoundError, BusinessRuleError


class ProductSearchService:
    """
    Main application service for product search operations.
    
    This service orchestrates complex business workflows by coordinating
    between command handlers, query handlers, and domain services.
    """
    
    def __init__(
        self,
        # Handlers
        search_products_handler: SearchProductsHandler,
        get_product_handler: GetProductHandler,
        
        # Repositories
        user_repository: UserRepository,
        search_session_repository: SearchSessionRepository,
        
        # Services
        analytics_service: AnalyticsService,
        recommendation_service: Optional[RecommendationService] = None,
        notification_service: Optional[NotificationService] = None
    ):
        self.search_products_handler = search_products_handler
        self.get_product_handler = get_product_handler
        self.user_repository = user_repository
        self.search_session_repository = search_session_repository
        self.analytics_service = analytics_service
        self.recommendation_service = recommendation_service
        self.notification_service = notification_service
    
    async def search_products(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> SearchProductsResult:
        """
        Execute a product search with full business logic.
        
        This method:
        1. Creates and validates search query
        2. Retrieves user preferences if authenticated
        3. Manages search session
        4. Executes search via command handler
        5. Records analytics
        6. Returns results with recommendations
        """
        
        # 1. Create search query value object
        search_query = SearchQuery.create_smart(query_text)
        
        # 2. Get user and preferences if authenticated
        user = None
        user_preferences = None
        if user_id:
            user = await self.user_repository.get_by_id(user_id)
            if user:
                user_preferences = user.preferences
                
                # Check if user has reached search limit
                if user.search_limit_reached:
                    raise BusinessRuleError(
                        "Daily search limit reached. Upgrade to premium for unlimited searches.",
                        rule="search_limit"
                    )
        
        # 3. Get or create search session
        session = None
        if session_id:
            session = await self.search_session_repository.get_by_id(session_id)
            if not session:
                if user_id:
                    session = SearchSession.create_for_user(user_id)
                else:
                    session = SearchSession.create_anonymous()
                session.session_id = session_id
        
        # 4. Build search command
        command = SearchProductsCommand(
            query=search_query,
            user_id=user_id,
            session_id=session_id,
            user_preferences=user_preferences,
            limit=limit,
            offset=offset,
            category_filter=filters.get('category') if filters else None,
            brand_filter=filters.get('brand') if filters else None,
            price_min=filters.get('price_min') if filters else None,
            price_max=filters.get('price_max') if filters else None,
            rating_min=filters.get('rating_min') if filters else None
        )
        
        # 5. Execute search
        result = await self.search_products_handler.handle(command)
        
        # 6. Update user search count if authenticated
        if user:
            user.record_search(search_query)
            await self.user_repository.save(user)
        
        # 7. Record analytics
        await self.analytics_service.track_search(
            query=search_query,
            user_id=user_id,
            session_id=session_id,
            results_count=result.result_count
        )
        
        # 8. Add personalized recommendations if available
        if self.recommendation_service and user_id and result.has_results:
            try:
                recommendations = await self.recommendation_service.get_personalized_recommendations(
                    user_id=user_id,
                    limit=5
                )
                # Add recommendations to result (this would require extending the result class)
                # result.recommendations = [r.to_dict() for r in recommendations]
            except Exception as e:
                # Don't fail search if recommendations fail
                print(f"Failed to get recommendations: {str(e)}")
        
        return result
    
    async def get_product_details(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        include_reviews: bool = True,
        include_related: bool = True
    ) -> GetProductResult:
        """
        Get detailed product information with business logic.
        
        This method:
        1. Validates access permissions
        2. Retrieves product details
        3. Records product view
        4. Updates user session
        5. Tracks analytics
        """
        
        # 1. Create query
        query = GetProductQuery(
            product_id=product_id,
            user_id=user_id,
            session_id=session_id,
            include_reviews=include_reviews,
            include_related_products=include_related
        )
        
        # 2. Execute query
        result = await self.get_product_handler.handle(query)
        
        if not result.found:
            raise NotFoundError("Product", product_id)
        
        # 3. Update search session if available
        if session_id:
            session = await self.search_session_repository.get_by_id(session_id)
            if session:
                session.view_product(product_id)
                await self.search_session_repository.save(session)
        
        # 4. Track analytics
        await self.analytics_service.track_product_view(
            product_id=product_id,
            user_id=user_id,
            session_id=session_id
        )
        
        return result
    
    async def get_search_suggestions(
        self,
        partial_query: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> List[str]:
        """Get search suggestions based on partial query and user context"""
        
        # Get basic suggestions from search query
        temp_query = SearchQuery.create_smart(partial_query)
        suggestions = temp_query.get_search_suggestions()
        
        # Add personalized suggestions if user is authenticated
        if user_id and self.recommendation_service:
            try:
                user = await self.user_repository.get_by_id(user_id)
                if user:
                    # Get suggestions based on user's search history
                    recent_searches = user.get_recent_searches(5)
                    for search in recent_searches:
                        if partial_query.lower() in search.normalized_query:
                            suggestions.append(search.query)
                    
                    # Add category-based suggestions from user preferences
                    for category in user.preferences.preferred_categories:
                        if partial_query.lower() in category.lower():
                            suggestions.append(f"{partial_query} {category}")
            except Exception as e:
                print(f"Failed to get personalized suggestions: {str(e)}")
        
        # Remove duplicates and limit results
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:limit]
    
    async def bookmark_product(
        self,
        user_id: str,
        product_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Add product to user's bookmarks"""
        
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Verify product exists
        product_query = GetProductQuery(product_id=product_id, user_id=user_id)
        product_result = await self.get_product_handler.handle(product_query)
        if not product_result.found:
            raise NotFoundError("Product", product_id)
        
        # Add bookmark
        await self.user_repository.add_bookmark(user_id, product_id)
        
        # Update session if available
        if session_id:
            session = await self.search_session_repository.get_by_id(session_id)
            if session:
                session.bookmark_product(product_id)
                await self.search_session_repository.save(session)
        
        # Track analytics
        await self.analytics_service.track_event(
            event_type="product_bookmarked",
            user_id=user_id,
            session_id=session_id,
            properties={"product_id": product_id}
        )
        
        # Send notification if enabled
        if self.notification_service and user.preferences.wants_notifications:
            try:
                await self.notification_service.create_notification(
                    user_id=user_id,
                    notification_type="bookmark_added",
                    title="Product Bookmarked",
                    message=f"Product has been added to your bookmarks",
                    data={"product_id": product_id}
                )
            except Exception as e:
                print(f"Failed to send bookmark notification: {str(e)}")
        
        return True
    
    async def remove_bookmark(
        self,
        user_id: str,
        product_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Remove product from user's bookmarks"""
        
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Remove bookmark
        await self.user_repository.remove_bookmark(user_id, product_id)
        
        # Update session if available
        if session_id:
            session = await self.search_session_repository.get_by_id(session_id)
            if session:
                session.remove_bookmark(product_id)
                await self.search_session_repository.save(session)
        
        # Track analytics
        await self.analytics_service.track_event(
            event_type="product_unbookmarked",
            user_id=user_id,
            session_id=session_id,
            properties={"product_id": product_id}
        )
        
        return True
    
    async def get_user_bookmarks(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's bookmarked products"""
        
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Get bookmark IDs
        bookmark_ids = await self.user_repository.get_user_bookmarks(user_id)
        
        # Paginate
        paginated_ids = bookmark_ids[offset:offset + limit]
        
        # Get product details for each bookmark
        bookmarked_products = []
        for product_id in paginated_ids:
            try:
                query = GetProductQuery(
                    product_id=product_id,
                    user_id=user_id,
                    include_reviews=False,
                    include_related_products=False
                )
                result = await self.get_product_handler.handle(query)
                if result.found:
                    bookmarked_products.append(result.product)
            except Exception as e:
                print(f"Failed to get bookmarked product {product_id}: {str(e)}")
                continue
        
        return {
            'products': bookmarked_products,
            'total_count': len(bookmark_ids),
            'limit': limit,
            'offset': offset,
            'has_more': len(bookmark_ids) > (offset + limit)
        }
    
    async def get_search_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's search history"""
        
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Check if user allows search history
        if not user.preferences.save_search_history:
            return []
        
        # Get recent searches
        recent_searches = user.get_recent_searches(limit)
        
        return [search.to_dict() for search in recent_searches]
    
    async def clear_search_history(self, user_id: str) -> bool:
        """Clear user's search history"""
        
        # Get user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Clear history
        user.clear_search_history()
        await self.user_repository.save(user)
        
        # Track analytics
        await self.analytics_service.track_event(
            event_type="search_history_cleared",
            user_id=user_id
        )
        
        return True
    
    async def get_trending_searches(self, limit: int = 10) -> List[str]:
        """Get trending search queries"""
        
        try:
            # Get trending searches from analytics
            end_date = datetime.utcnow()
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            analytics = await self.analytics_service.get_search_analytics(
                start_date=start_date,
                end_date=end_date
            )
            
            trending = analytics.get('trending_queries', [])
            return trending[:limit]
            
        except Exception as e:
            print(f"Failed to get trending searches: {str(e)}")
            return []
    
    async def get_user_recommendations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get personalized recommendations for user"""
        
        if not self.recommendation_service:
            return []
        
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Check if user allows personalized recommendations
        if not user.preferences.personalized_recommendations:
            return []
        
        try:
            recommendations = await self.recommendation_service.get_personalized_recommendations(
                user_id=user_id,
                limit=limit
            )
            
            return [rec.to_dict() for rec in recommendations]
            
        except Exception as e:
            print(f"Failed to get user recommendations: {str(e)}")
            return []