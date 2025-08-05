"""
Search Products Command Handler - Processes product search commands
"""
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..search_products_command import SearchProductsCommand, SearchProductsResult
from ....core.entities.product import Product
from ....core.entities.search_session import SearchSession
from ....core.value_objects.search_query import SearchQuery
from ....shared.interfaces.repositories import ProductRepository, SearchSessionRepository
from ....shared.interfaces.services import SearchService, RecommendationService
from ....shared.exceptions import SearchError, ValidationError


class SearchProductsHandler:
    """
    Handles SearchProductsCommand by coordinating search operations.
    
    This handler orchestrates the search process by:
    1. Validating the search command
    2. Applying user preferences and filters
    3. Executing the search via SearchService
    4. Recording the search in session
    5. Generating suggestions and recommendations
    """
    
    def __init__(
        self,
        product_repository: ProductRepository,
        search_service: SearchService,
        search_session_repository: Optional[SearchSessionRepository] = None,
        recommendation_service: Optional[RecommendationService] = None
    ):
        self.product_repository = product_repository
        self.search_service = search_service
        self.search_session_repository = search_session_repository
        self.recommendation_service = recommendation_service
    
    async def handle(self, command: SearchProductsCommand) -> SearchProductsResult:
        """
        Handle the search products command.
        
        Args:
            command: The search command to process
            
        Returns:
            SearchProductsResult containing products and metadata
            
        Raises:
            ValidationError: If command validation fails
            SearchError: If search operation fails
        """
        start_time = time.time()
        
        try:
            # 1. Validate command
            self._validate_command(command)
            
            # 2. Build search parameters
            search_params = self._build_search_parameters(command)
            
            # 3. Execute search
            products, total_count = await self._execute_search(search_params)
            
            # 4. Apply user preferences if available
            if command.user_preferences:
                products = self._apply_user_preferences(products, command.user_preferences)
            
            # 5. Record search in session if session tracking is enabled
            if self.search_session_repository and command.session_id:
                await self._record_search_in_session(command, products, total_count)
            
            # 6. Generate suggestions
            suggested_queries = self._generate_query_suggestions(command.query, products)
            related_categories = self._extract_related_categories(products)
            
            # 7. Calculate search time
            search_time_ms = int((time.time() - start_time) * 1000)
            
            # 8. Build result
            result = SearchProductsResult(
                products=[p.to_dict() for p in products],
                total_count=total_count,
                query_used=command.query,
                search_time_ms=search_time_ms,
                limit=command.limit,
                offset=command.offset,
                has_more=total_count > (command.offset + len(products)),
                filters_applied=self._get_applied_filters(command),
                suggested_queries=suggested_queries,
                related_categories=related_categories
            )
            
            return result
            
        except Exception as e:
            search_time_ms = int((time.time() - start_time) * 1000)
            
            # Log the error (in a real implementation, use proper logging)
            print(f"Search failed after {search_time_ms}ms: {str(e)}")
            
            if isinstance(e, (ValidationError, SearchError)):
                raise
            else:
                raise SearchError(f"Unexpected error during search: {str(e)}")
    
    def _validate_command(self, command: SearchProductsCommand) -> None:
        """Validate the search command"""
        if not command.query or not command.query.query.strip():
            raise ValidationError("Search query cannot be empty")
        
        if command.limit <= 0 or command.limit > 100:
            raise ValidationError("Limit must be between 1 and 100")
        
        if command.offset < 0:
            raise ValidationError("Offset cannot be negative")
        
        if command.price_min is not None and command.price_min < 0:
            raise ValidationError("Minimum price cannot be negative")
        
        if (command.price_min is not None and command.price_max is not None 
            and command.price_min > command.price_max):
            raise ValidationError("Minimum price cannot be greater than maximum price")
        
        if command.rating_min is not None and (command.rating_min < 0 or command.rating_min > 5):
            raise ValidationError("Rating filter must be between 0 and 5")
    
    def _build_search_parameters(self, command: SearchProductsCommand) -> Dict[str, Any]:
        """Build search parameters from command"""
        params = {
            'query': command.query.normalized_query,
            'limit': command.limit,
            'offset': command.offset,
            'include_out_of_stock': command.include_out_of_stock
        }
        
        # Add filters
        if command.category_filter:
            params['category'] = command.category_filter
        
        if command.brand_filter:
            params['brand'] = command.brand_filter
        
        if command.price_min is not None:
            params['price_min'] = command.price_min
        
        if command.price_max is not None:
            params['price_max'] = command.price_max
        
        if command.rating_min is not None:
            params['rating_min'] = command.rating_min
        
        # Add user preferences as search context
        if command.user_preferences:
            params['user_context'] = {
                'preferred_categories': command.user_preferences.preferred_categories,
                'excluded_categories': command.user_preferences.excluded_categories,
                'preferred_brands': command.user_preferences.preferred_brands,
                'excluded_brands': command.user_preferences.excluded_brands,
                'sort_preference': command.user_preferences.sort_preference.value
            }
        
        return params
    
    async def _execute_search(self, search_params: Dict[str, Any]) -> tuple[List[Product], int]:
        """Execute the actual search operation"""
        try:
            # Use the search service to perform the search
            results = await self.search_service.search_products(search_params)
            
            # Convert results to Product entities
            products = []
            for result_data in results.get('products', []):
                try:
                    product = Product.from_dict(result_data)
                    products.append(product)
                except Exception as e:
                    # Log conversion error but continue with other products
                    print(f"Failed to convert product data: {str(e)}")
                    continue
            
            total_count = results.get('total_count', len(products))
            
            return products, total_count
            
        except Exception as e:
            raise SearchError(f"Search service failed: {str(e)}")
    
    def _apply_user_preferences(self, products: List[Product], 
                              preferences: 'UserPreferences') -> List[Product]:
        """Apply user preferences to filter and sort products"""
        filtered_products = []
        
        for product in products:
            # Apply preference-based filtering
            product_data = {
                'price': float(product.price.amount),
                'rating': product.rating,
                'brand': product.brand,
                'category': product.category,
                'features': product.features
            }
            
            # Check if product matches user preferences
            if preferences.get_preference_score(product_data) > 0:
                filtered_products.append(product)
        
        # Sort based on user preferences
        if preferences.sort_preference.value == 'price_asc':
            filtered_products.sort(key=lambda p: p.price.amount)
        elif preferences.sort_preference.value == 'price_desc':
            filtered_products.sort(key=lambda p: p.price.amount, reverse=True)
        elif preferences.sort_preference.value == 'rating':
            filtered_products.sort(key=lambda p: p.rating or 0, reverse=True)
        elif preferences.sort_preference.value == 'popularity':
            filtered_products.sort(key=lambda p: p.popularity_score or 0, reverse=True)
        # Default is relevance (keep original order)
        
        return filtered_products
    
    async def _record_search_in_session(self, command: SearchProductsCommand, 
                                      products: List[Product], total_count: int) -> None:
        """Record the search in the user's session"""
        try:
            if not self.search_session_repository:
                return
            
            # Get or create session
            session = await self.search_session_repository.get_by_id(command.session_id)
            if not session:
                # Create new session if it doesn't exist
                session = SearchSession.create_for_user(
                    user_id=command.user_id,
                    user_agent=command.user_agent
                )
                session.session_id = command.session_id
            
            # Add search result to session
            search_time_ms = 100  # Placeholder - would be calculated properly
            session.add_search_result(
                query=command.query,
                products=products,
                total_results=total_count,
                search_time_ms=search_time_ms
            )
            
            # Save session
            await self.search_session_repository.save(session)
            
        except Exception as e:
            # Log error but don't fail the search
            print(f"Failed to record search in session: {str(e)}")
    
    def _generate_query_suggestions(self, query: SearchQuery, 
                                  products: List[Product]) -> List[str]:
        """Generate query suggestions based on search results"""
        suggestions = []
        
        # Add query-based suggestions
        suggestions.extend(query.get_search_suggestions())
        
        # Add product-based suggestions
        if products:
            # Get common categories from results
            categories = [p.category for p in products if p.category]
            category_counts = {}
            for cat in categories:
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # Add top categories as suggestions
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            for category, _ in top_categories:
                suggestions.append(f"{query.query} {category}")
            
            # Add brand suggestions
            brands = [p.brand for p in products if p.brand]
            unique_brands = list(set(brands))[:3]
            for brand in unique_brands:
                suggestions.append(f"{brand} {query.query}")
        
        # Remove duplicates and limit
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:5]
    
    def _extract_related_categories(self, products: List[Product]) -> List[str]:
        """Extract related categories from search results"""
        if not products:
            return []
        
        categories = [p.category for p in products if p.category]
        category_counts = {}
        for cat in categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Return top categories
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in top_categories[:5]]
    
    def _get_applied_filters(self, command: SearchProductsCommand) -> Dict[str, Any]:
        """Get dictionary of applied filters"""
        filters = {}
        
        if command.category_filter:
            filters['category'] = command.category_filter
        
        if command.brand_filter:
            filters['brand'] = command.brand_filter
        
        if command.price_min is not None:
            filters['price_min'] = command.price_min
        
        if command.price_max is not None:
            filters['price_max'] = command.price_max
        
        if command.rating_min is not None:
            filters['rating_min'] = command.rating_min
        
        if not command.include_out_of_stock:
            filters['exclude_out_of_stock'] = True
        
        return filters