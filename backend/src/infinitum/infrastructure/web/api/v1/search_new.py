"""
Updated Search API endpoints using Clean Architecture
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from ......application.commands.search_products_command import SearchProductsCommand
from ......application.queries.get_product_query import GetProductQuery
from ......core.value_objects.search_query import SearchQuery
from ......core.value_objects.user_preferences import UserPreferences
from ......shared.exceptions import ValidationError, SearchError, NotFoundError
from ....di.container import (
    get_product_search_service,
    get_search_products_handler,
    get_product_handler
)

router = APIRouter(prefix="/api/v1", tags=["search"])


# Request/Response Models

class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    limit: int = Field(20, description="Maximum results to return", ge=1, le=100)
    offset: int = Field(0, description="Results offset for pagination", ge=0)
    category: Optional[str] = Field(None, description="Filter by category")
    brand: Optional[str] = Field(None, description="Filter by brand")
    price_min: Optional[float] = Field(None, description="Minimum price filter", ge=0)
    price_max: Optional[float] = Field(None, description="Maximum price filter", ge=0)
    rating_min: Optional[float] = Field(None, description="Minimum rating filter", ge=0, le=5)
    include_out_of_stock: bool = Field(True, description="Include out of stock products")


class SearchResponse(BaseModel):
    """Search response model"""
    products: List[Dict[str, Any]]
    total_count: int
    result_count: int
    query: str
    search_time_ms: int
    has_more: bool
    suggestions: List[str]
    filters_applied: Dict[str, Any]
    metadata: Dict[str, Any]


class ProductDetailResponse(BaseModel):
    """Product detail response model"""
    product: Optional[Dict[str, Any]]
    reviews: Optional[List[Dict[str, Any]]]
    related_products: Optional[List[Dict[str, Any]]]
    found: bool
    retrieval_time_ms: int
    user_data: Dict[str, Any]
    metadata: Dict[str, Any]


# Dependency functions

def get_user_context(
    user_id: Optional[str] = Query(None, description="User ID for personalization"),
    session_id: Optional[str] = Query(None, description="Session ID for tracking")
) -> Dict[str, Any]:
    """Extract user context from request"""
    return {
        'user_id': user_id,
        'session_id': session_id,
        'timestamp': datetime.utcnow().isoformat()
    }


# API Endpoints

@router.post("/search", response_model=SearchResponse)
async def search_products(
    request: SearchRequest,
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """
    Search for products using the new Clean Architecture.
    
    This endpoint uses the application layer to handle complex business logic
    including user preferences, session management, and analytics.
    """
    start_time = time.time()
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Build filters from request
        filters = {}
        if request.category:
            filters['category'] = request.category
        if request.brand:
            filters['brand'] = request.brand
        if request.price_min is not None:
            filters['price_min'] = request.price_min
        if request.price_max is not None:
            filters['price_max'] = request.price_max
        if request.rating_min is not None:
            filters['rating_min'] = request.rating_min
        
        # Execute search through application service
        result = await product_search_service.search_products(
            query_text=request.query,
            user_id=user_context.get('user_id'),
            session_id=user_context.get('session_id'),
            filters=filters,
            limit=request.limit,
            offset=request.offset
        )
        
        # Build response
        search_time_ms = int((time.time() - start_time) * 1000)
        
        return SearchResponse(
            products=result.products,
            total_count=result.total_count,
            result_count=result.result_count,
            query=result.query_used.query,
            search_time_ms=search_time_ms,
            has_more=result.has_more,
            suggestions=result.suggested_queries,
            filters_applied=result.filters_applied,
            metadata={
                'search_method': 'clean_architecture',
                'user_authenticated': user_context.get('user_id') is not None,
                'session_tracked': user_context.get('session_id') is not None,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={
            'error': 'Validation Error',
            'message': e.message,
            'details': e.details
        })
    
    except SearchError as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Search Error',
            'message': e.message,
            'query': request.query
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Internal Server Error',
            'message': str(e),
            'search_time_ms': int((time.time() - start_time) * 1000)
        })


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product_details(
    product_id: str,
    include_reviews: bool = Query(True, description="Include product reviews"),
    include_related: bool = Query(True, description="Include related products"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """
    Get detailed product information using Clean Architecture.
    
    This endpoint uses the application layer to handle business logic
    including user-specific data, analytics tracking, and session management.
    """
    start_time = time.time()
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Execute query through application service
        result = await product_search_service.get_product_details(
            product_id=product_id,
            user_id=user_context.get('user_id'),
            session_id=user_context.get('session_id'),
            include_reviews=include_reviews,
            include_related=include_related
        )
        
        return ProductDetailResponse(
            product=result.product,
            reviews=result.reviews,
            related_products=result.related_products,
            found=result.found,
            retrieval_time_ms=result.retrieval_time_ms,
            user_data={
                'has_bookmarked': result.user_has_bookmarked,
                'user_rating': result.user_rating
            },
            metadata={
                'data_source': result.data_source,
                'has_reviews': result.has_reviews,
                'has_related_products': result.has_related_products,
                'user_authenticated': user_context.get('user_id') is not None,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'Product Not Found',
            'message': e.message,
            'product_id': product_id
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Internal Server Error',
            'message': str(e),
            'retrieval_time_ms': int((time.time() - start_time) * 1000)
        })


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="Partial query for suggestions", min_length=1),
    limit: int = Query(5, description="Maximum suggestions to return", ge=1, le=10),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """Get search suggestions based on partial query"""
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Get suggestions through application service
        suggestions = await product_search_service.get_search_suggestions(
            partial_query=q,
            user_id=user_context.get('user_id'),
            limit=limit
        )
        
        return {
            'query': q,
            'suggestions': suggestions,
            'count': len(suggestions),
            'personalized': user_context.get('user_id') is not None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to get suggestions',
            'message': str(e)
        })


@router.get("/search/trending")
async def get_trending_searches(
    limit: int = Query(10, description="Maximum trending searches to return", ge=1, le=20)
):
    """Get trending search queries"""
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Get trending searches
        trending = await product_search_service.get_trending_searches(limit=limit)
        
        return {
            'trending_searches': trending,
            'count': len(trending),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to get trending searches',
            'message': str(e)
        })


@router.post("/products/{product_id}/bookmark")
async def bookmark_product(
    product_id: str,
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """Bookmark a product for a user"""
    
    user_id = user_context.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail={
            'error': 'Authentication Required',
            'message': 'User ID is required to bookmark products'
        })
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Bookmark through application service
        success = await product_search_service.bookmark_product(
            user_id=user_id,
            product_id=product_id,
            session_id=user_context.get('session_id')
        )
        
        return {
            'success': success,
            'product_id': product_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'Not Found',
            'message': e.message
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to bookmark product',
            'message': str(e)
        })


@router.delete("/products/{product_id}/bookmark")
async def remove_bookmark(
    product_id: str,
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """Remove a product bookmark for a user"""
    
    user_id = user_context.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail={
            'error': 'Authentication Required',
            'message': 'User ID is required to manage bookmarks'
        })
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Remove bookmark through application service
        success = await product_search_service.remove_bookmark(
            user_id=user_id,
            product_id=product_id,
            session_id=user_context.get('session_id')
        )
        
        return {
            'success': success,
            'product_id': product_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'Not Found',
            'message': e.message
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to remove bookmark',
            'message': str(e)
        })


@router.get("/users/{user_id}/bookmarks")
async def get_user_bookmarks(
    user_id: str,
    limit: int = Query(20, description="Maximum bookmarks to return", ge=1, le=100),
    offset: int = Query(0, description="Bookmarks offset for pagination", ge=0),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """Get user's bookmarked products"""
    
    # Verify user can access these bookmarks
    requesting_user_id = user_context.get('user_id')
    if requesting_user_id != user_id:
        raise HTTPException(status_code=403, detail={
            'error': 'Access Denied',
            'message': 'You can only access your own bookmarks'
        })
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Get bookmarks through application service
        result = await product_search_service.get_user_bookmarks(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            'bookmarks': result['products'],
            'total_count': result['total_count'],
            'limit': limit,
            'offset': offset,
            'has_more': result['has_more'],
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'User Not Found',
            'message': e.message
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to get bookmarks',
            'message': str(e)
        })


@router.get("/users/{user_id}/search-history")
async def get_search_history(
    user_id: str,
    limit: int = Query(20, description="Maximum history items to return", ge=1, le=100),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """Get user's search history"""
    
    # Verify user can access this history
    requesting_user_id = user_context.get('user_id')
    if requesting_user_id != user_id:
        raise HTTPException(status_code=403, detail={
            'error': 'Access Denied',
            'message': 'You can only access your own search history'
        })
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Get search history through application service
        history = await product_search_service.get_search_history(
            user_id=user_id,
            limit=limit
        )
        
        return {
            'search_history': history,
            'count': len(history),
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'User Not Found',
            'message': e.message
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to get search history',
            'message': str(e)
        })


@router.delete("/users/{user_id}/search-history")
async def clear_search_history(
    user_id: str,
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """Clear user's search history"""
    
    # Verify user can clear this history
    requesting_user_id = user_context.get('user_id')
    if requesting_user_id != user_id:
        raise HTTPException(status_code=403, detail={
            'error': 'Access Denied',
            'message': 'You can only clear your own search history'
        })
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Clear search history through application service
        success = await product_search_service.clear_search_history(user_id=user_id)
        
        return {
            'success': success,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'User Not Found',
            'message': e.message
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to clear search history',
            'message': str(e)
        })


@router.get("/users/{user_id}/recommendations")
async def get_user_recommendations(
    user_id: str,
    limit: int = Query(10, description="Maximum recommendations to return", ge=1, le=50),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """Get personalized recommendations for a user"""
    
    # Verify user can access these recommendations
    requesting_user_id = user_context.get('user_id')
    if requesting_user_id != user_id:
        raise HTTPException(status_code=403, detail={
            'error': 'Access Denied',
            'message': 'You can only access your own recommendations'
        })
    
    try:
        # Get the application service
        product_search_service = get_product_search_service()
        
        # Get recommendations through application service
        recommendations = await product_search_service.get_user_recommendations(
            user_id=user_id,
            limit=limit
        )
        
        return {
            'recommendations': recommendations,
            'count': len(recommendations),
            'user_id': user_id,
            'personalized': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'User Not Found',
            'message': e.message
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'error': 'Failed to get recommendations',
            'message': str(e)
        })


@router.get("/health")
async def health_check():
    """Health check endpoint for the search API"""
    
    try:
        from ....di.container import get_container
        
        # Get container health status
        container = get_container()
        health_status = container.health_check()
        
        # Add API-specific health info
        health_status['api'] = {
            'status': 'healthy',
            'endpoints_available': [
                '/search',
                '/products/{id}',
                '/search/suggestions',
                '/search/trending'
            ],
            'clean_architecture': True
        }
        
        return health_status
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }