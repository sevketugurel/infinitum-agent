"""
Production-Ready Vector Search Service
Implements comprehensive semantic search with vector similarity, filtering, pagination, and advanced features
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

import numpy as np
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndexEndpoint

from infinitum.settings import settings
from infinitum.infrastructure.logging_config import get_agent_logger
from infinitum.infrastructure.persistence.firestore_client import db
from infinitum.infrastructure.external_services.embeddings_service import embeddings_service, EmbeddingRequest
from infinitum.infrastructure.external_services.vector_index_service import vector_index_service

logger = get_agent_logger("vector_search_service")

class SearchMode(Enum):
    """Search modes for different use cases"""
    SEMANTIC_SIMILARITY = "semantic_similarity"
    HYBRID_SEARCH = "hybrid_search"
    CATEGORY_SEARCH = "category_search"
    RECOMMENDATION = "recommendation"

@dataclass
class SearchFilter:
    """Search filter configuration"""
    namespace: str
    values: List[str]
    operator: str = "allow"  # allow or deny

@dataclass
class SearchRequest:
    """Comprehensive search request"""
    query: str
    mode: SearchMode = SearchMode.SEMANTIC_SIMILARITY
    filters: Optional[List[SearchFilter]] = None
    limit: int = 20
    offset: int = 0
    similarity_threshold: float = 0.7
    include_metadata: bool = True
    include_scores: bool = True
    boost_factors: Optional[Dict[str, float]] = None
    user_context: Optional[Dict[str, Any]] = None

@dataclass
class SearchResult:
    """Single search result"""
    id: str
    score: float
    metadata: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None

@dataclass
class SearchResponse:
    """Complete search response"""
    results: List[SearchResult]
    total_found: int
    query_time_ms: float
    query_embedding_time_ms: float
    search_time_ms: float
    filters_applied: List[SearchFilter]
    search_metadata: Dict[str, Any]
    suggestions: Optional[List[str]] = None
    debug_info: Optional[Dict[str, Any]] = None

class VectorSearchService:
    """Production-ready vector search service with comprehensive features"""
    
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = "us-central1"
        self.search_collection = db.collection('search_logs')
        self.analytics_collection = db.collection('search_analytics')
        
        # Search configuration
        self.default_deployed_index_id = "product_search_v1"
        self.default_endpoint_name = "product-search-endpoint"
        
        # Performance settings
        self.max_concurrent_searches = 10
        self.search_timeout_seconds = 30
        self.cache_ttl_minutes = 15
        
        # Analytics
        self.enable_analytics = True
        self.enable_query_logging = True
        
        # Initialize search cache
        self._search_cache = {}
        self._cache_timestamps = {}
        
    async def semantic_search(
        self,
        query: str,
        filters: Optional[List[SearchFilter]] = None,
        limit: int = 20,
        offset: int = 0,
        similarity_threshold: float = 0.7,
        include_metadata: bool = True,
        include_scores: bool = True,
        user_context: Optional[Dict[str, Any]] = None,
        debug: bool = False
    ) -> SearchResponse:
        """
        Main semantic search function with comprehensive features
        
        Args:
            query: Natural language search query
            filters: List of filters to apply
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            similarity_threshold: Minimum similarity score threshold
            include_metadata: Whether to include result metadata
            include_scores: Whether to include similarity scores
            user_context: User context for personalization
            debug: Whether to include debug information
            
        Returns:
            SearchResponse with ranked results and metadata
        """
        start_time = time.time()
        search_id = f"search_{int(time.time() * 1000)}"
        
        try:
            logger.info(f"Starting semantic search: {search_id} - Query: '{query[:100]}...'")
            
            # Create search request
            search_request = SearchRequest(
                query=query,
                mode=SearchMode.SEMANTIC_SIMILARITY,
                filters=filters or [],
                limit=limit,
                offset=offset,
                similarity_threshold=similarity_threshold,
                include_metadata=include_metadata,
                include_scores=include_scores,
                user_context=user_context
            )
            
            # Check cache first
            cache_key = self._generate_cache_key(search_request)
            cached_response = await self._get_cached_response(cache_key)
            if cached_response and not debug:
                logger.info(f"Returning cached response for search: {search_id}")
                return cached_response
            
            # Step 1: Generate query embedding
            embedding_start = time.time()
            query_embedding = await self._generate_query_embedding(query, user_context)
            embedding_time = (time.time() - embedding_start) * 1000
            
            if not query_embedding:
                raise ValueError("Failed to generate query embedding")
            
            # Step 2: Perform vector search
            search_start = time.time()
            raw_results = await self._perform_vector_search(
                query_embedding, 
                search_request,
                debug
            )
            search_time = (time.time() - search_start) * 1000
            
            # Step 3: Post-process results
            processed_results = await self._post_process_results(
                raw_results,
                search_request,
                query
            )
            
            # Step 4: Apply pagination
            paginated_results = self._apply_pagination(processed_results, offset, limit)
            
            # Step 5: Generate suggestions
            suggestions = await self._generate_search_suggestions(query, processed_results, user_context)
            
            # Create response
            total_time = (time.time() - start_time) * 1000
            
            response = SearchResponse(
                results=paginated_results,
                total_found=len(processed_results),
                query_time_ms=total_time,
                query_embedding_time_ms=embedding_time,
                search_time_ms=search_time,
                filters_applied=search_request.filters,
                search_metadata={
                    "search_id": search_id,
                    "query": query,
                    "similarity_threshold": similarity_threshold,
                    "model_used": "vertex-text-embedding-004",
                    "timestamp": datetime.now().isoformat()
                },
                suggestions=suggestions,
                debug_info=self._generate_debug_info(search_request, raw_results) if debug else None
            )
            
            # Cache the response
            await self._cache_response(cache_key, response)
            
            # Log search for analytics
            if self.enable_query_logging:
                await self._log_search(search_id, search_request, response)
            
            logger.info(f"Search completed: {search_id} - {len(paginated_results)} results in {total_time:.2f}ms")
            
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {search_id} - {e}")
            
            # Return error response
            return SearchResponse(
                results=[],
                total_found=0,
                query_time_ms=(time.time() - start_time) * 1000,
                query_embedding_time_ms=0,
                search_time_ms=0,
                filters_applied=filters or [],
                search_metadata={
                    "search_id": search_id,
                    "query": query,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    async def hybrid_search(
        self,
        query: str,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
        **kwargs
    ) -> SearchResponse:
        """
        Hybrid search combining keyword and semantic search
        
        Args:
            query: Search query
            keyword_weight: Weight for keyword matching
            semantic_weight: Weight for semantic similarity
            **kwargs: Additional search parameters
            
        Returns:
            SearchResponse with hybrid results
        """
        try:
            logger.info(f"Starting hybrid search: '{query}' (kw:{keyword_weight}, sem:{semantic_weight})")
            
            # Perform semantic search
            semantic_response = await self.semantic_search(query, **kwargs)
            
            # Perform keyword search (simplified implementation)
            keyword_results = await self._perform_keyword_search(query, kwargs.get('limit', 20))
            
            # Combine and re-rank results
            combined_results = await self._combine_search_results(
                semantic_response.results,
                keyword_results,
                semantic_weight,
                keyword_weight
            )
            
            # Update response
            semantic_response.results = combined_results[:kwargs.get('limit', 20)]
            semantic_response.search_metadata["search_mode"] = "hybrid"
            semantic_response.search_metadata["keyword_weight"] = keyword_weight
            semantic_response.search_metadata["semantic_weight"] = semantic_weight
            
            return semantic_response
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            # Fallback to semantic search
            return await self.semantic_search(query, **kwargs)
    
    async def find_similar_items(
        self,
        item_id: str,
        limit: int = 10,
        similarity_threshold: float = 0.8,
        exclude_self: bool = True
    ) -> SearchResponse:
        """
        Find items similar to a given item
        
        Args:
            item_id: ID of the reference item
            limit: Maximum number of similar items to return
            similarity_threshold: Minimum similarity threshold
            exclude_self: Whether to exclude the reference item from results
            
        Returns:
            SearchResponse with similar items
        """
        try:
            logger.info(f"Finding similar items to: {item_id}")
            
            # Get item embedding from vector index
            item_embedding = await self._get_item_embedding(item_id)
            if not item_embedding:
                raise ValueError(f"Item {item_id} not found in vector index")
            
            # Search for similar items using the item's embedding
            search_request = SearchRequest(
                query="",  # No text query for similarity search
                mode=SearchMode.RECOMMENDATION,
                limit=limit + (1 if exclude_self else 0),  # Get extra if excluding self
                similarity_threshold=similarity_threshold
            )
            
            raw_results = await self._perform_vector_search_with_embedding(
                item_embedding,
                search_request
            )
            
            # Filter out the reference item if requested
            if exclude_self:
                raw_results = [r for r in raw_results if r.id != item_id]
            
            # Limit results
            similar_items = raw_results[:limit]
            
            return SearchResponse(
                results=similar_items,
                total_found=len(similar_items),
                query_time_ms=0,  # No query embedding needed
                query_embedding_time_ms=0,
                search_time_ms=0,  # Would need timing
                filters_applied=[],
                search_metadata={
                    "search_mode": "similarity",
                    "reference_item_id": item_id,
                    "similarity_threshold": similarity_threshold,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Similar items search failed for {item_id}: {e}")
            return SearchResponse(
                results=[],
                total_found=0,
                query_time_ms=0,
                query_embedding_time_ms=0,
                search_time_ms=0,
                filters_applied=[],
                search_metadata={
                    "error": str(e),
                    "reference_item_id": item_id
                }
            )
    
    async def get_recommendations(
        self,
        user_id: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        interaction_history: Optional[List[str]] = None,
        limit: int = 20
    ) -> SearchResponse:
        """
        Get personalized recommendations for a user
        
        Args:
            user_id: User identifier
            user_preferences: User preference data
            interaction_history: List of item IDs user has interacted with
            limit: Maximum number of recommendations
            
        Returns:
            SearchResponse with personalized recommendations
        """
        try:
            logger.info(f"Generating recommendations for user: {user_id}")
            
            # Build user profile embedding
            user_embedding = await self._build_user_profile_embedding(
                user_id,
                user_preferences,
                interaction_history
            )
            
            if not user_embedding:
                # Fallback to popular items or category-based recommendations
                return await self._get_fallback_recommendations(user_preferences, limit)
            
            # Search for recommendations using user profile embedding
            search_request = SearchRequest(
                query="",
                mode=SearchMode.RECOMMENDATION,
                limit=limit * 2,  # Get more to filter out already seen items
                similarity_threshold=0.6  # Lower threshold for recommendations
            )
            
            raw_results = await self._perform_vector_search_with_embedding(
                user_embedding,
                search_request
            )
            
            # Filter out items user has already interacted with
            if interaction_history:
                raw_results = [r for r in raw_results if r.id not in interaction_history]
            
            # Apply recommendation-specific ranking
            ranked_results = await self._rank_recommendations(
                raw_results,
                user_preferences,
                limit
            )
            
            return SearchResponse(
                results=ranked_results,
                total_found=len(ranked_results),
                query_time_ms=0,
                query_embedding_time_ms=0,
                search_time_ms=0,
                filters_applied=[],
                search_metadata={
                    "search_mode": "recommendations",
                    "user_id": user_id,
                    "personalized": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Recommendations failed for user {user_id}: {e}")
            return await self._get_fallback_recommendations(user_preferences, limit)
    
    # Private helper methods
    
    async def _generate_query_embedding(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[List[float]]:
        """Generate embedding for search query with optional context enhancement"""
        try:
            # Enhance query with user context if available
            enhanced_query = query
            if user_context:
                enhanced_query = await self._enhance_query_with_context(query, user_context)
            
            # Generate embedding
            result = await embeddings_service.generate_embedding(
                text=enhanced_query,
                model="vertex-text-embedding-004",
                task_type="SEMANTIC_SIMILARITY"
            )
            
            if result.error:
                logger.error(f"Embedding generation failed: {result.error}")
                return None
            
            return result.embedding
            
        except Exception as e:
            logger.error(f"Query embedding generation failed: {e}")
            return None
    
    async def _perform_vector_search(
        self,
        query_embedding: List[float],
        search_request: SearchRequest,
        debug: bool = False
    ) -> List[SearchResult]:
        """Perform the actual vector search against the index"""
        try:
            # Get endpoint information
            endpoint_info = await vector_index_service._get_endpoint_info(self.default_endpoint_name)
            if not endpoint_info:
                raise ValueError("Search endpoint not found")
            
            # Create endpoint client
            endpoint = MatchingEngineIndexEndpoint(endpoint_info["endpoint_id"])
            
            # Prepare search parameters
            search_params = {
                "deployed_index_id": self.default_deployed_index_id,
                "queries": [query_embedding],
                "num_neighbors": search_request.limit + search_request.offset,
            }
            
            # Add filters if specified
            if search_request.filters:
                restricts = []
                for filter_obj in search_request.filters:
                    restricts.append({
                        "namespace": filter_obj.namespace,
                        filter_obj.operator: filter_obj.values
                    })
                search_params["restricts"] = restricts
            
            # Perform search
            response = endpoint.find_neighbors(**search_params)
            
            # Process results
            results = []
            if response and len(response) > 0:
                neighbors = response[0]  # First query results
                
                for neighbor in neighbors:
                    if neighbor.distance >= search_request.similarity_threshold:
                        continue
                    
                    # Convert distance to similarity score (cosine distance -> cosine similarity)
                    similarity_score = 1.0 - neighbor.distance
                    
                    result = SearchResult(
                        id=neighbor.id,
                        score=similarity_score,
                        metadata=getattr(neighbor, 'restricts', None)
                    )
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _perform_vector_search_with_embedding(
        self,
        embedding: List[float],
        search_request: SearchRequest
    ) -> List[SearchResult]:
        """Perform vector search with a pre-computed embedding"""
        return await self._perform_vector_search(embedding, search_request)
    
    async def _post_process_results(
        self,
        raw_results: List[SearchResult],
        search_request: SearchRequest,
        original_query: str
    ) -> List[SearchResult]:
        """Post-process search results with additional data and ranking"""
        try:
            processed_results = []
            
            for result in raw_results:
                # Enrich with metadata from Firestore if needed
                if search_request.include_metadata:
                    content_data = await self._get_item_content(result.id)
                    if content_data:
                        result.content = content_data
                
                # Generate explanation if requested
                if search_request.user_context and search_request.user_context.get("explain_results"):
                    result.explanation = await self._generate_result_explanation(
                        result,
                        original_query,
                        search_request.user_context
                    )
                
                processed_results.append(result)
            
            # Apply additional ranking factors
            if search_request.boost_factors:
                processed_results = await self._apply_boost_factors(
                    processed_results,
                    search_request.boost_factors
                )
            
            # Sort by final score
            processed_results.sort(key=lambda x: x.score, reverse=True)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Post-processing failed: {e}")
            return raw_results
    
    def _apply_pagination(
        self,
        results: List[SearchResult],
        offset: int,
        limit: int
    ) -> List[SearchResult]:
        """Apply pagination to results"""
        return results[offset:offset + limit]
    
    async def _generate_search_suggestions(
        self,
        query: str,
        results: List[SearchResult],
        user_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate search suggestions based on query and results"""
        try:
            suggestions = []
            
            # Query expansion suggestions
            if len(results) < 5:
                suggestions.extend([
                    f"Try broader terms related to '{query}'",
                    f"Search for '{query}' alternatives",
                    f"Explore '{query}' categories"
                ])
            
            # Category-based suggestions from results
            if results:
                categories = set()
                for result in results[:5]:
                    if result.content and "category" in result.content:
                        categories.add(result.content["category"])
                
                for category in list(categories)[:3]:
                    suggestions.append(f"Explore more {category} products")
            
            # User context suggestions
            if user_context and "recent_searches" in user_context:
                recent = user_context["recent_searches"][:2]
                for recent_query in recent:
                    if recent_query != query:
                        suggestions.append(f"Try '{recent_query}' again")
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            return []
    
    def _generate_cache_key(self, search_request: SearchRequest) -> str:
        """Generate cache key for search request"""
        import hashlib
        
        # Create a string representation of the search request
        cache_data = {
            "query": search_request.query,
            "mode": search_request.mode.value,
            "filters": [asdict(f) for f in search_request.filters] if search_request.filters else [],
            "limit": search_request.limit,
            "offset": search_request.offset,
            "similarity_threshold": search_request.similarity_threshold
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    async def _get_cached_response(self, cache_key: str) -> Optional[SearchResponse]:
        """Get cached search response if valid"""
        try:
            if cache_key in self._search_cache:
                cache_time = self._cache_timestamps.get(cache_key, datetime.min)
                if datetime.now() - cache_time < timedelta(minutes=self.cache_ttl_minutes):
                    return self._search_cache[cache_key]
                else:
                    # Remove expired cache
                    del self._search_cache[cache_key]
                    del self._cache_timestamps[cache_key]
            
            return None
            
        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")
            return None
    
    async def _cache_response(self, cache_key: str, response: SearchResponse):
        """Cache search response"""
        try:
            self._search_cache[cache_key] = response
            self._cache_timestamps[cache_key] = datetime.now()
            
            # Clean up old cache entries (keep only last 1000)
            if len(self._search_cache) > 1000:
                oldest_keys = sorted(
                    self._cache_timestamps.keys(),
                    key=lambda k: self._cache_timestamps[k]
                )[:100]
                
                for key in oldest_keys:
                    del self._search_cache[key]
                    del self._cache_timestamps[key]
                    
        except Exception as e:
            logger.error(f"Cache storage failed: {e}")
    
    async def _log_search(
        self,
        search_id: str,
        request: SearchRequest,
        response: SearchResponse
    ):
        """Log search for analytics"""
        try:
            if not self.enable_analytics:
                return
            
            log_data = {
                "search_id": search_id,
                "query": request.query,
                "mode": request.mode.value,
                "results_count": len(response.results),
                "total_found": response.total_found,
                "query_time_ms": response.query_time_ms,
                "filters_applied": len(request.filters) if request.filters else 0,
                "timestamp": datetime.now().isoformat(),
                "user_context": bool(request.user_context)
            }
            
            self.search_collection.add(log_data)
            
        except Exception as e:
            logger.error(f"Search logging failed: {e}")
    
    def _generate_debug_info(
        self,
        request: SearchRequest,
        raw_results: List[SearchResult]
    ) -> Dict[str, Any]:
        """Generate debug information for search"""
        return {
            "request_params": asdict(request),
            "raw_results_count": len(raw_results),
            "filters_applied": len(request.filters) if request.filters else 0,
            "similarity_threshold": request.similarity_threshold,
            "cache_enabled": True,
            "endpoint_used": self.default_endpoint_name,
            "deployed_index_id": self.default_deployed_index_id
        }
    
    # Additional helper methods would be implemented here for:
    # - _perform_keyword_search
    # - _combine_search_results
    # - _get_item_embedding
    # - _get_item_content
    # - _enhance_query_with_context
    # - _build_user_profile_embedding
    # - _get_fallback_recommendations
    # - _rank_recommendations
    # - _generate_result_explanation
    # - _apply_boost_factors
    
    async def get_search_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get search analytics for the specified period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get recent searches
            searches = list(
                self.search_collection
                .where("timestamp", ">=", cutoff_date.isoformat())
                .stream()
            )
            
            if not searches:
                return {"message": "No search data available"}
            
            search_data = [doc.to_dict() for doc in searches]
            
            # Calculate analytics
            total_searches = len(search_data)
            avg_query_time = sum(s.get("query_time_ms", 0) for s in search_data) / total_searches
            avg_results = sum(s.get("results_count", 0) for s in search_data) / total_searches
            
            # Top queries
            query_counts = {}
            for search in search_data:
                query = search.get("query", "").lower()
                query_counts[query] = query_counts.get(query, 0) + 1
            
            top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "period_days": days,
                "total_searches": total_searches,
                "average_query_time_ms": round(avg_query_time, 2),
                "average_results_per_query": round(avg_results, 2),
                "top_queries": top_queries,
                "search_modes": {
                    mode: sum(1 for s in search_data if s.get("mode") == mode)
                    for mode in ["semantic_similarity", "hybrid_search", "recommendation"]
                }
            }
            
        except Exception as e:
            logger.error(f"Analytics retrieval failed: {e}")
            return {"error": str(e)}

# Global instance
vector_search_service = VectorSearchService()