"""
Get Product Query Handler - Processes product detail retrieval queries
"""
import time
from typing import List, Dict, Any, Optional

from ..get_product_query import GetProductQuery, GetProductResult
from ....core.entities.product import Product
from ....core.entities.user import User
from ....shared.interfaces.repositories import ProductRepository, UserRepository
from ....shared.interfaces.services import RecommendationService, ReviewService
from ....shared.exceptions import NotFoundError, ValidationError


class GetProductHandler:
    """
    Handles GetProductQuery by retrieving product details and related information.
    
    This handler:
    1. Validates the query
    2. Retrieves the product from repository
    3. Fetches additional data (reviews, related products, etc.)
    4. Records the product view for analytics
    5. Returns comprehensive product information
    """
    
    def __init__(
        self,
        product_repository: ProductRepository,
        user_repository: Optional[UserRepository] = None,
        recommendation_service: Optional[RecommendationService] = None,
        review_service: Optional[ReviewService] = None
    ):
        self.product_repository = product_repository
        self.user_repository = user_repository
        self.recommendation_service = recommendation_service
        self.review_service = review_service
    
    async def handle(self, query: GetProductQuery) -> GetProductResult:
        """
        Handle the get product query.
        
        Args:
            query: The product query to process
            
        Returns:
            GetProductResult containing product details and related data
            
        Raises:
            ValidationError: If query validation fails
            NotFoundError: If product is not found
        """
        start_time = time.time()
        
        try:
            # 1. Validate query
            self._validate_query(query)
            
            # 2. Retrieve product
            product = await self._get_product(query.product_id)
            
            if not product:
                return GetProductResult(
                    product=None,
                    found=False,
                    retrieval_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # 3. Get user-specific data if user is authenticated
            user_has_bookmarked = False
            user_rating = None
            
            if query.user_id and self.user_repository:
                user_data = await self._get_user_product_data(query.user_id, query.product_id)
                user_has_bookmarked = user_data.get('has_bookmarked', False)
                user_rating = user_data.get('user_rating')
            
            # 4. Fetch additional data based on query options
            reviews = None
            if query.include_reviews:
                reviews = await self._get_product_reviews(query.product_id)
            
            related_products = None
            if query.include_related_products:
                related_products = await self._get_related_products(product, query.user_id)
            
            price_history = None
            if query.include_price_history:
                price_history = await self._get_price_history(query.product_id)
            
            # 5. Record product view for analytics
            if query.user_id or query.session_id:
                await self._record_product_view(query, product)
            
            # 6. Calculate retrieval time
            retrieval_time_ms = int((time.time() - start_time) * 1000)
            
            # 7. Build result
            result = GetProductResult(
                product=product.to_dict(),
                reviews=reviews,
                related_products=related_products,
                price_history=price_history,
                found=True,
                retrieval_time_ms=retrieval_time_ms,
                user_has_bookmarked=user_has_bookmarked,
                user_rating=user_rating
            )
            
            return result
            
        except Exception as e:
            retrieval_time_ms = int((time.time() - start_time) * 1000)
            
            # Log the error
            print(f"Product retrieval failed after {retrieval_time_ms}ms: {str(e)}")
            
            if isinstance(e, (ValidationError, NotFoundError)):
                raise
            else:
                # Return not found result for unexpected errors
                return GetProductResult(
                    product=None,
                    found=False,
                    retrieval_time_ms=retrieval_time_ms
                )
    
    def _validate_query(self, query: GetProductQuery) -> None:
        """Validate the get product query"""
        if not query.product_id or not query.product_id.strip():
            raise ValidationError("Product ID cannot be empty")
        
        # Additional validation could be added here
        # e.g., product ID format validation
    
    async def _get_product(self, product_id: str) -> Optional[Product]:
        """Retrieve product from repository"""
        try:
            return await self.product_repository.get_by_id(product_id)
        except Exception as e:
            print(f"Failed to retrieve product {product_id}: {str(e)}")
            return None
    
    async def _get_user_product_data(self, user_id: str, product_id: str) -> Dict[str, Any]:
        """Get user-specific data for the product"""
        try:
            # This would typically involve checking user bookmarks, ratings, etc.
            # For now, return empty data
            return {
                'has_bookmarked': False,
                'user_rating': None
            }
        except Exception as e:
            print(f"Failed to get user product data: {str(e)}")
            return {}
    
    async def _get_product_reviews(self, product_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get product reviews"""
        try:
            if not self.review_service:
                return None
            
            reviews = await self.review_service.get_product_reviews(product_id, limit=10)
            return [review.to_dict() for review in reviews] if reviews else None
            
        except Exception as e:
            print(f"Failed to get product reviews: {str(e)}")
            return None
    
    async def _get_related_products(self, product: Product, 
                                  user_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get related products"""
        try:
            if not self.recommendation_service:
                return None
            
            # Get recommendations based on the product
            related = await self.recommendation_service.get_similar_products(
                product_id=product.product_id,
                user_id=user_id,
                limit=5
            )
            
            return [p.to_dict() for p in related] if related else None
            
        except Exception as e:
            print(f"Failed to get related products: {str(e)}")
            return None
    
    async def _get_price_history(self, product_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get product price history"""
        try:
            # This would typically involve querying a price history service
            # For now, return None as this is a complex feature
            return None
            
        except Exception as e:
            print(f"Failed to get price history: {str(e)}")
            return None
    
    async def _record_product_view(self, query: GetProductQuery, product: Product) -> None:
        """Record that the product was viewed for analytics"""
        try:
            # This would typically involve:
            # 1. Recording the view in analytics
            # 2. Updating user session if session_id is provided
            # 3. Updating product view count
            # 4. Triggering recommendation updates
            
            # For now, just log the view
            print(f"Product view recorded: {product.product_id} by user {query.user_id}")
            
        except Exception as e:
            # Don't fail the query if analytics recording fails
            print(f"Failed to record product view: {str(e)}")


class GetProductListQuery:
    """Query to get a list of products with filters"""
    
    def __init__(
        self,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        rating_min: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        user_id: Optional[str] = None
    ):
        self.category = category
        self.brand = brand
        self.price_min = price_min
        self.price_max = price_max
        self.rating_min = rating_min
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.user_id = user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary"""
        return {
            'filters': {
                'category': self.category,
                'brand': self.brand,
                'price_min': self.price_min,
                'price_max': self.price_max,
                'rating_min': self.rating_min
            },
            'pagination': {
                'limit': self.limit,
                'offset': self.offset
            },
            'sort_by': self.sort_by,
            'user_id': self.user_id
        }


class GetProductListResult:
    """Result of a product list query"""
    
    def __init__(
        self,
        products: List[Dict[str, Any]],
        total_count: int,
        limit: int,
        offset: int,
        retrieval_time_ms: int = 0
    ):
        self.products = products
        self.total_count = total_count
        self.limit = limit
        self.offset = offset
        self.retrieval_time_ms = retrieval_time_ms
    
    @property
    def result_count(self) -> int:
        """Get number of products returned"""
        return len(self.products)
    
    @property
    def has_more(self) -> bool:
        """Check if there are more results"""
        return self.total_count > (self.offset + self.result_count)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'products': self.products,
            'total_count': self.total_count,
            'result_count': self.result_count,
            'pagination': {
                'limit': self.limit,
                'offset': self.offset,
                'has_more': self.has_more
            },
            'metadata': {
                'retrieval_time_ms': self.retrieval_time_ms
            }
        }


class GetProductListHandler:
    """Handler for product list queries"""
    
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository
    
    async def handle(self, query: GetProductListQuery) -> GetProductListResult:
        """Handle product list query"""
        start_time = time.time()
        
        try:
            # Build filter parameters
            filters = {}
            if query.category:
                filters['category'] = query.category
            if query.brand:
                filters['brand'] = query.brand
            if query.price_min is not None:
                filters['price_min'] = query.price_min
            if query.price_max is not None:
                filters['price_max'] = query.price_max
            if query.rating_min is not None:
                filters['rating_min'] = query.rating_min
            
            # Get products from repository
            products, total_count = await self.product_repository.find_with_filters(
                filters=filters,
                limit=query.limit,
                offset=query.offset,
                sort_by=query.sort_by
            )
            
            # Convert to dictionaries
            product_dicts = [p.to_dict() for p in products]
            
            retrieval_time_ms = int((time.time() - start_time) * 1000)
            
            return GetProductListResult(
                products=product_dicts,
                total_count=total_count,
                limit=query.limit,
                offset=query.offset,
                retrieval_time_ms=retrieval_time_ms
            )
            
        except Exception as e:
            retrieval_time_ms = int((time.time() - start_time) * 1000)
            print(f"Product list retrieval failed: {str(e)}")
            
            return GetProductListResult(
                products=[],
                total_count=0,
                limit=query.limit,
                offset=query.offset,
                retrieval_time_ms=retrieval_time_ms
            )