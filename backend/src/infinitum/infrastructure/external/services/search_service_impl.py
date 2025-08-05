"""
Search Service Implementation - Concrete implementation of SearchService interface
"""
from typing import List, Optional, Dict, Any
import time
from datetime import datetime

from .....shared.interfaces.services import SearchService
from .....shared.exceptions import SearchError
from ..ai.vector_search_service import vector_search_service, SearchFilter, SearchMode
from ..search.semantic_search_client import semantic_search_service
from ...persistence.firestore_client import db


class SearchServiceImpl(SearchService):
    """
    Concrete implementation of SearchService interface.
    
    This service combines vector search, semantic search, and traditional
    keyword search to provide comprehensive search capabilities.
    """
    
    def __init__(self):
        self.trending_collection = db.collection('trending_searches')
        self.suggestions_collection = db.collection('search_suggestions')
        
        # Search configuration
        self.use_vector_search = True
        self.use_semantic_enhancement = True
        self.fallback_to_keyword = True
        
        # Performance settings
        self.search_timeout_seconds = 30
        self.max_results_per_source = 100
    
    async def search_products(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for products based on parameters.
        
        Args:
            search_params: Dictionary containing search parameters including:
                - query: Search query string
                - limit: Maximum results to return
                - offset: Results offset for pagination
                - filters: Additional filters (category, brand, price, etc.)
                - user_context: User context for personalization
                
        Returns:
            Dictionary with 'products' list and 'total_count'
        """
        start_time = time.time()
        
        try:
            query = search_params.get('query', '')
            limit = search_params.get('limit', 20)
            offset = search_params.get('offset', 0)
            filters = search_params.get('filters', {})
            user_context = search_params.get('user_context', {})
            
            if not query.strip():
                raise SearchError("Search query cannot be empty", query=query)
            
            # Strategy 1: Try vector search first (most advanced)
            if self.use_vector_search:
                try:
                    vector_results = await self._vector_search_products(
                        query, filters, limit, offset, user_context
                    )
                    
                    if vector_results['products']:
                        vector_results['search_method'] = 'vector_search'
                        vector_results['search_time_ms'] = (time.time() - start_time) * 1000
                        return vector_results
                        
                except Exception as vector_error:
                    print(f"Vector search failed: {vector_error}")
                    # Continue to fallback methods
            
            # Strategy 2: Enhanced semantic search
            if self.use_semantic_enhancement:
                try:
                    semantic_results = await self._semantic_search_products(
                        query, filters, limit, offset, user_context
                    )
                    
                    if semantic_results['products']:
                        semantic_results['search_method'] = 'semantic_search'
                        semantic_results['search_time_ms'] = (time.time() - start_time) * 1000
                        return semantic_results
                        
                except Exception as semantic_error:
                    print(f"Semantic search failed: {semantic_error}")
                    # Continue to fallback
            
            # Strategy 3: Fallback to basic keyword search
            if self.fallback_to_keyword:
                try:
                    keyword_results = await self._keyword_search_products(
                        query, filters, limit, offset
                    )
                    
                    keyword_results['search_method'] = 'keyword_search'
                    keyword_results['search_time_ms'] = (time.time() - start_time) * 1000
                    return keyword_results
                    
                except Exception as keyword_error:
                    print(f"Keyword search failed: {keyword_error}")
            
            # If all methods fail, return empty results
            return {
                'products': [],
                'total_count': 0,
                'search_method': 'failed',
                'search_time_ms': (time.time() - start_time) * 1000,
                'error': 'All search methods failed'
            }
            
        except Exception as e:
            raise SearchError(f"Product search failed: {str(e)}", query=search_params.get('query', ''))
    
    async def search_packages(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for packages based on parameters.
        
        Args:
            search_params: Dictionary containing search parameters
            
        Returns:
            Dictionary with 'packages' list and 'total_count'
        """
        try:
            # For now, delegate to product search but filter for packages
            # In a real implementation, you'd have a separate package search
            
            # Add package-specific filters
            search_params = search_params.copy()
            filters = search_params.get('filters', {})
            filters['type'] = 'package'
            search_params['filters'] = filters
            
            # Use product search infrastructure
            results = await self.search_products(search_params)
            
            # Transform results for package format
            return {
                'packages': results.get('products', []),
                'total_count': results.get('total_count', 0),
                'search_method': results.get('search_method', 'unknown'),
                'search_time_ms': results.get('search_time_ms', 0)
            }
            
        except Exception as e:
            raise SearchError(f"Package search failed: {str(e)}", query=search_params.get('query', ''))
    
    async def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get search suggestions for a query"""
        try:
            suggestions = []
            
            # Strategy 1: Get suggestions from semantic analysis
            if self.use_semantic_enhancement:
                try:
                    query_analysis = await semantic_search_service.enhance_query_understanding(query)
                    semantic_suggestions = await semantic_search_service.generate_semantic_suggestions(
                        query_analysis
                    )
                    suggestions.extend(semantic_suggestions)
                except Exception as e:
                    print(f"Semantic suggestions failed: {e}")
            
            # Strategy 2: Get suggestions from stored data
            try:
                # Query suggestions collection for similar queries
                query_lower = query.lower()
                suggestions_query = self.suggestions_collection.where(
                    'query_prefix', '>=', query_lower
                ).where(
                    'query_prefix', '<=', query_lower + '\uf8ff'
                ).limit(limit * 2)
                
                docs = suggestions_query.stream()
                for doc in docs:
                    suggestion_data = doc.to_dict()
                    suggestion = suggestion_data.get('suggestion', '')
                    if suggestion and suggestion not in suggestions:
                        suggestions.append(suggestion)
                        
            except Exception as e:
                print(f"Stored suggestions query failed: {e}")
            
            # Strategy 3: Generate basic suggestions
            if len(suggestions) < limit:
                basic_suggestions = self._generate_basic_suggestions(query)
                for suggestion in basic_suggestions:
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
            
            return suggestions[:limit]
            
        except Exception as e:
            print(f"Get search suggestions failed: {e}")
            return self._generate_basic_suggestions(query)[:limit]
    
    async def get_trending_searches(self, limit: int = 10) -> List[str]:
        """Get trending search queries"""
        try:
            # Get trending searches from the last 24 hours
            cutoff_time = datetime.now().timestamp() - (24 * 60 * 60)  # 24 hours ago
            
            trending_query = self.trending_collection.where(
                'timestamp', '>=', cutoff_time
            ).order_by('search_count', direction='DESCENDING').limit(limit)
            
            docs = trending_query.stream()
            trending_searches = []
            
            for doc in docs:
                trending_data = doc.to_dict()
                query = trending_data.get('query', '')
                if query:
                    trending_searches.append(query)
            
            # If no trending data, return popular fallback queries
            if not trending_searches:
                trending_searches = [
                    "wireless headphones",
                    "laptop deals",
                    "smartphone reviews",
                    "gaming accessories",
                    "home office setup",
                    "fitness tracker",
                    "kitchen appliances",
                    "camera equipment",
                    "smart home devices",
                    "outdoor gear"
                ]
            
            return trending_searches[:limit]
            
        except Exception as e:
            print(f"Get trending searches failed: {e}")
            # Return fallback trending searches
            return [
                "wireless headphones",
                "laptop deals", 
                "smartphone reviews",
                "gaming accessories",
                "home office setup"
            ][:limit]
    
    # Private helper methods
    
    async def _vector_search_products(
        self, 
        query: str, 
        filters: Dict[str, Any], 
        limit: int, 
        offset: int,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform vector search for products"""
        
        # Convert filters to vector search filters
        search_filters = []
        
        if 'category' in filters:
            search_filters.append(SearchFilter(
                namespace="category",
                values=[filters['category']],
                operator="allow"
            ))
        
        if 'brand' in filters:
            search_filters.append(SearchFilter(
                namespace="brand", 
                values=[filters['brand']],
                operator="allow"
            ))
        
        if 'price_range' in filters:
            search_filters.append(SearchFilter(
                namespace="price_range",
                values=[filters['price_range']],
                operator="allow"
            ))
        
        # Perform vector search
        search_response = await vector_search_service.semantic_search(
            query=query,
            filters=search_filters,
            limit=limit + offset,  # Get extra for offset
            offset=0,  # Handle offset in post-processing
            similarity_threshold=0.7,
            include_metadata=True,
            include_scores=True,
            user_context=user_context
        )
        
        # Apply offset to results
        results = search_response.results[offset:offset + limit]
        
        # Convert vector search results to product format
        products = []
        for result in results:
            product_data = {
                'id': result.id,
                'score': result.score,
                'similarity_score': result.score,
                **result.content if result.content else {},
                **result.metadata if result.metadata else {}
            }
            products.append(product_data)
        
        return {
            'products': products,
            'total_count': search_response.total_found,
            'suggestions': search_response.suggestions or [],
            'search_metadata': search_response.search_metadata
        }
    
    async def _semantic_search_products(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int,
        offset: int,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform semantic search for products"""
        
        # Use enhanced vector search from semantic service
        search_results = await semantic_search_service.enhanced_vector_search(
            user_query=query,
            user_context=user_context,
            limit=limit + offset,
            use_hybrid=True
        )
        
        # Apply offset
        all_results = search_results.get('results', [])
        paginated_results = all_results[offset:offset + limit]
        
        return {
            'products': paginated_results,
            'total_count': search_results.get('total_found', len(all_results)),
            'suggestions': search_results.get('suggestions', []),
            'search_metadata': search_results.get('search_metadata', {}),
            'query_analysis': search_results.get('query_analysis', {})
        }
    
    async def _keyword_search_products(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int,
        offset: int
    ) -> Dict[str, Any]:
        """Perform basic keyword search for products"""
        
        # This is a simplified keyword search
        # In production, you'd use a proper search engine like Elasticsearch
        
        try:
            # Query Firestore products collection
            products_collection = db.collection('products')
            
            # Simple text matching (this is very basic)
            query_lower = query.lower()
            
            # Get all products and filter in memory (not efficient for large datasets)
            all_docs = products_collection.limit(1000).stream()
            
            matching_products = []
            for doc in all_docs:
                try:
                    product_data = doc.to_dict()
                    product_data['id'] = doc.id
                    
                    # Check if query matches product fields
                    title = product_data.get('title', '').lower()
                    description = product_data.get('description', '').lower()
                    brand = product_data.get('brand', '').lower()
                    category = product_data.get('category', '').lower()
                    
                    # Simple keyword matching
                    if (query_lower in title or 
                        query_lower in description or 
                        query_lower in brand or
                        query_lower in category):
                        
                        # Apply filters
                        if self._matches_filters(product_data, filters):
                            # Calculate simple relevance score
                            score = 0
                            if query_lower in title:
                                score += 10
                            if query_lower in brand:
                                score += 5
                            if query_lower in description:
                                score += 2
                            if query_lower in category:
                                score += 1
                            
                            product_data['score'] = score
                            matching_products.append(product_data)
                            
                except Exception as e:
                    print(f"Error processing product {doc.id}: {e}")
                    continue
            
            # Sort by relevance score
            matching_products.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Apply pagination
            total_count = len(matching_products)
            paginated_products = matching_products[offset:offset + limit]
            
            return {
                'products': paginated_products,
                'total_count': total_count,
                'suggestions': self._generate_basic_suggestions(query),
                'search_metadata': {
                    'query': query,
                    'method': 'keyword_search',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            print(f"Keyword search error: {e}")
            return {
                'products': [],
                'total_count': 0,
                'suggestions': [],
                'search_metadata': {'error': str(e)}
            }
    
    def _matches_filters(self, product_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if product matches the given filters"""
        
        if 'category' in filters:
            if product_data.get('category') != filters['category']:
                return False
        
        if 'brand' in filters:
            if product_data.get('brand') != filters['brand']:
                return False
        
        if 'price_min' in filters:
            price = product_data.get('price', {})
            if isinstance(price, dict):
                amount = price.get('amount', 0)
            else:
                amount = price
            if amount < filters['price_min']:
                return False
        
        if 'price_max' in filters:
            price = product_data.get('price', {})
            if isinstance(price, dict):
                amount = price.get('amount', 0)
            else:
                amount = price
            if amount > filters['price_max']:
                return False
        
        if 'rating_min' in filters:
            rating = product_data.get('rating', 0)
            if rating < filters['rating_min']:
                return False
        
        return True
    
    def _generate_basic_suggestions(self, query: str) -> List[str]:
        """Generate basic search suggestions"""
        query_lower = query.lower()
        suggestions = []
        
        # Add common variations
        suggestions.append(f"{query} reviews")
        suggestions.append(f"{query} price")
        suggestions.append(f"best {query}")
        suggestions.append(f"{query} deals")
        suggestions.append(f"{query} comparison")
        
        # Add category-based suggestions
        if any(word in query_lower for word in ['phone', 'mobile', 'smartphone']):
            suggestions.extend([
                "smartphone accessories",
                "phone cases",
                "wireless chargers"
            ])
        elif any(word in query_lower for word in ['laptop', 'computer', 'pc']):
            suggestions.extend([
                "laptop accessories",
                "computer peripherals", 
                "gaming laptops"
            ])
        elif any(word in query_lower for word in ['headphones', 'earbuds', 'audio']):
            suggestions.extend([
                "wireless headphones",
                "noise canceling headphones",
                "gaming headsets"
            ])
        
        return suggestions[:5]
    
    async def record_search(self, query: str, results_count: int, user_context: Optional[Dict[str, Any]] = None):
        """Record search for analytics and trending calculations"""
        try:
            # Update trending searches
            trending_ref = self.trending_collection.document(query.lower())
            trending_doc = trending_ref.get()
            
            if trending_doc.exists:
                # Increment search count
                current_data = trending_doc.to_dict()
                search_count = current_data.get('search_count', 0) + 1
                trending_ref.update({
                    'search_count': search_count,
                    'last_searched': datetime.now().timestamp(),
                    'results_count': results_count
                })
            else:
                # Create new trending entry
                trending_ref.set({
                    'query': query,
                    'search_count': 1,
                    'first_searched': datetime.now().timestamp(),
                    'last_searched': datetime.now().timestamp(),
                    'results_count': results_count
                })
            
            # Store search suggestions based on successful searches
            if results_count > 0:
                # Generate and store suggestions for this query
                suggestions = await self.get_search_suggestions(query, limit=3)
                for suggestion in suggestions:
                    if suggestion != query:
                        suggestion_ref = self.suggestions_collection.document()
                        suggestion_ref.set({
                            'query_prefix': query.lower(),
                            'suggestion': suggestion,
                            'created_at': datetime.now().timestamp()
                        })
                        
        except Exception as e:
            print(f"Failed to record search: {e}")
            # Don't fail the search if recording fails