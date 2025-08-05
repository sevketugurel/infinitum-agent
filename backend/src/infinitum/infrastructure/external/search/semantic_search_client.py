# File: src/infinitum/services/semantic_search_service.py
"""
Enhanced Semantic Search Service with Vector Search Integration
Combines traditional semantic analysis with advanced vector search capabilities
"""

from typing import List, Dict, Any, Optional, Tuple
import json
import numpy as np
from datetime import datetime
import logging

from ..ai.vertex_ai_client import ask_gemini
from ...persistence.firestore_client import db
from ...monitoring.logging.config import get_agent_logger

# Import new vector search components
from ..ai.vector_search_service import (
    vector_search_service, SearchFilter, SearchMode
)
from ..ai.embeddings_client import (
    embeddings_service, EmbeddingRequest
)

logger = get_agent_logger("semantic_search")

class SemanticSearchService:
    """Enhanced semantic search capabilities with vector search integration"""
    
    def __init__(self):
        self.products_collection = db.collection('products')
        self.embeddings_collection = db.collection('product_embeddings')
        
        # Vector search integration
        self.use_vector_search = True
        self.vector_search_threshold = 0.7
        self.fallback_to_traditional = True
    
    async def enhance_query_understanding(self, user_query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhance query understanding using semantic analysis"""
        try:
            # Build context information
            context_info = ""
            if user_context:
                preferences = user_context.get("user_profile", {}).get("preferences", {})
                recent_interests = user_context.get("recent_interests", [])
                
                context_info = f"""
                User Context:
                - Budget conscious: {preferences.get('budget_conscious', False)}
                - Quality focused: {preferences.get('quality_focused', False)}
                - Recent interests: {', '.join(recent_interests) if recent_interests else 'None'}
                - Preferred categories: {', '.join(preferences.get('category_interests', []))}
                """
            
            prompt = f"""
            Analyze this shopping query for semantic understanding AND extract search keywords in one response.
            
            User Query: "{user_query}"
            {context_info}
            
            Provide a JSON response with:
            1. "intent_analysis": What the user is really looking for
            2. "product_categories": Relevant product categories (electronics, fashion, etc.)
            3. "key_features": Important features/specifications mentioned or implied
            4. "budget_signals": Any budget/price signals detected
            5. "use_case": Primary use case or scenario
            6. "alternatives": Related or alternative search terms
            7. "semantic_tags": Tags for semantic matching
            8. "priority_factors": What matters most to this user (price, quality, features, etc.)
            9. "search_keywords": Array of 3-5 optimized Google search keywords for product finding
            
            For search_keywords, focus on product names, brands, categories, and specific features.
            Each keyword should be 1-4 words long and optimized for product search.
            Example: ["wireless headphones", "Sony WH-1000XM5", "noise canceling headphones"]
            
            Return ONLY the JSON object, no other text.
            """
            
            response = ask_gemini(prompt)
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
                analysis["query"] = user_query
                analysis["analysis_timestamp"] = datetime.now().isoformat()
                return analysis
            
            # Fallback analysis
            return self._create_fallback_analysis(user_query)
            
        except Exception as e:
            logger.error(f"Error in semantic query analysis: {e}")
            return self._create_fallback_analysis(user_query)
    
    def _create_fallback_analysis(self, query: str) -> Dict[str, Any]:
        """Create basic analysis when AI fails"""
        query_lower = query.lower()
        
        # Basic category detection
        categories = []
        if any(word in query_lower for word in ["headphones", "speaker", "audio"]):
            categories.append("audio")
        if any(word in query_lower for word in ["laptop", "computer", "pc"]):
            categories.append("computers")
        if any(word in query_lower for word in ["phone", "mobile", "smartphone"]):
            categories.append("mobile")
        if any(word in query_lower for word in ["camera", "photography", "video"]):
            categories.append("photography")
        
        # Basic budget detection
        budget_signals = []
        if any(word in query_lower for word in ["cheap", "budget", "affordable", "economical"]):
            budget_signals.append("budget_conscious")
        if any(word in query_lower for word in ["premium", "high-end", "professional", "best"]):
            budget_signals.append("quality_focused")
        
        return {
            "intent_analysis": f"User is looking for {query}",
            "product_categories": categories or ["general"],
            "key_features": [],
            "budget_signals": budget_signals,
            "use_case": "general_shopping",
            "alternatives": [query],
            "semantic_tags": query.split(),
            "priority_factors": ["relevance", "price"],
            "query": query,
            "analysis_timestamp": datetime.now().isoformat(),
            "fallback": True
        }
    
    async def find_similar_products(self, query_analysis: Dict[str, Any], 
                                  available_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find products most similar to the semantic query analysis"""
        try:
            if not available_products:
                return []
            
            # Extract semantic features from query analysis
            intent = query_analysis.get("intent_analysis", "")
            categories = query_analysis.get("product_categories", [])
            features = query_analysis.get("key_features", [])
            use_case = query_analysis.get("use_case", "")
            semantic_tags = query_analysis.get("semantic_tags", [])
            
            # Score each product for semantic similarity
            scored_products = []
            for product in available_products:
                similarity_score = self._calculate_semantic_similarity(
                    product, intent, categories, features, use_case, semantic_tags
                )
                
                product_with_score = product.copy()
                product_with_score["semantic_similarity_score"] = similarity_score
                product_with_score["semantic_reasoning"] = self._generate_similarity_reasoning(
                    product, query_analysis, similarity_score
                )
                scored_products.append(product_with_score)
            
            # Sort by semantic similarity
            scored_products.sort(key=lambda x: x.get("semantic_similarity_score", 0), reverse=True)
            
            return scored_products
            
        except Exception as e:
            logger.error(f"Error in semantic product matching: {e}")
            # Return products with default scores
            for product in available_products:
                product["semantic_similarity_score"] = 0.5
                product["semantic_reasoning"] = "Default scoring due to analysis error"
            return available_products
    
    def _calculate_semantic_similarity(self, product: Dict[str, Any], intent: str, 
                                     categories: List[str], features: List[str], 
                                     use_case: str, semantic_tags: List[str]) -> float:
        """Calculate semantic similarity score between product and query analysis"""
        total_score = 0.0
        max_score = 0.0
        
        title = product.get("title", "").lower()
        description = product.get("description", "").lower()
        brand = product.get("brand", "").lower()
        
        # Category matching (30% weight)
        category_score = 0.0
        for category in categories:
            if category.lower() in title or category.lower() in description:
                category_score += 1.0
        if categories:
            category_score = min(category_score / len(categories), 1.0)
        total_score += category_score * 0.3
        max_score += 0.3
        
        # Feature matching (25% weight)
        feature_score = 0.0
        for feature in features:
            if feature.lower() in title or feature.lower() in description:
                feature_score += 1.0
        if features:
            feature_score = min(feature_score / len(features), 1.0)
        total_score += feature_score * 0.25
        max_score += 0.25
        
        # Semantic tag matching (25% weight)
        tag_score = 0.0
        for tag in semantic_tags:
            if tag.lower() in title or tag.lower() in description or tag.lower() in brand:
                tag_score += 1.0
        if semantic_tags:
            tag_score = min(tag_score / len(semantic_tags), 1.0)
        total_score += tag_score * 0.25
        max_score += 0.25
        
        # Use case relevance (20% weight)
        use_case_score = 0.0
        if use_case and (use_case.lower() in title or use_case.lower() in description):
            use_case_score = 1.0
        total_score += use_case_score * 0.2
        max_score += 0.2
        
        # Normalize score
        if max_score > 0:
            return total_score / max_score
        return 0.0
    
    def _generate_similarity_reasoning(self, product: Dict[str, Any], 
                                     query_analysis: Dict[str, Any], score: float) -> str:
        """Generate human-readable reasoning for similarity score"""
        title = product.get("title", "Unknown Product")
        
        if score >= 0.8:
            return f"'{title}' is an excellent match - highly relevant to your needs"
        elif score >= 0.6:
            return f"'{title}' is a good match - meets most of your requirements"
        elif score >= 0.4:
            return f"'{title}' is a decent match - some relevant features"
        elif score >= 0.2:
            return f"'{title}' is a partial match - limited relevance"
        else:
            return f"'{title}' is a weak match - consider alternatives"
    
    async def enhance_product_packages(self, packages: List[Dict[str, Any]], 
                                     query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhance package recommendations using semantic understanding"""
        try:
            enhanced_packages = []
            
            for package in packages:
                enhanced_package = package.copy()
                
                # Re-score products in package using semantic analysis
                products = package.get("products", [])
                if products:
                    semantic_products = await self.find_similar_products(query_analysis, products)
                    enhanced_package["products"] = semantic_products
                    
                    # Calculate package semantic score
                    avg_score = sum(p.get("semantic_similarity_score", 0) for p in semantic_products) / len(semantic_products)
                    enhanced_package["semantic_package_score"] = avg_score
                    enhanced_package["semantic_package_reasoning"] = self._generate_package_reasoning(
                        enhanced_package, query_analysis, avg_score
                    )
                
                enhanced_packages.append(enhanced_package)
            
            # Sort packages by semantic relevance
            enhanced_packages.sort(
                key=lambda x: x.get("semantic_package_score", 0), 
                reverse=True
            )
            
            return enhanced_packages
            
        except Exception as e:
            logger.error(f"Error enhancing packages with semantic analysis: {e}")
            return packages
    
    def _generate_package_reasoning(self, package: Dict[str, Any], 
                                  query_analysis: Dict[str, Any], score: float) -> str:
        """Generate reasoning for package recommendation"""
        package_name = package.get("name", "Package")
        
        if score >= 0.8:
            return f"{package_name} perfectly matches your requirements and preferences"
        elif score >= 0.6:
            return f"{package_name} is well-suited to your needs with good feature alignment"
        elif score >= 0.4:
            return f"{package_name} offers decent value with some relevant features"
        else:
            return f"{package_name} has limited alignment but may still be worth considering"
    
    async def generate_semantic_suggestions(self, query_analysis: Dict[str, Any],
                                          user_context: Dict[str, Any] = None) -> List[str]:
        """Generate semantic-based search suggestions"""
        try:
            categories = query_analysis.get("product_categories", [])
            alternatives = query_analysis.get("alternatives", [])
            use_case = query_analysis.get("use_case", "")
            
            suggestions = []
            
            # Add category-based suggestions
            for category in categories[:3]:
                suggestions.append(f"Explore more {category} products")
            
            # Add alternative search suggestions
            for alt in alternatives[:2]:
                if alt != query_analysis.get("query", ""):
                    suggestions.append(f"Try searching for '{alt}'")
            
            # Add use-case based suggestions
            if use_case and use_case != "general_shopping":
                suggestions.append(f"Browse products for {use_case.replace('_', ' ')}")
            
            # Add context-based suggestions
            if user_context:
                recent_interests = user_context.get("recent_interests", [])
                for interest in recent_interests[:2]:
                    suggestions.append(f"Check out related {interest} products")
            
            return suggestions[:5]  # Limit to top 5 suggestions
            
        except Exception as e:
            logger.error(f"Error generating semantic suggestions: {e}")
            return ["Try different search terms", "Browse popular categories"]
    
    async def enhanced_vector_search(
        self,
        user_query: str,
        user_context: Dict[str, Any] = None,
        limit: int = 20,
        use_hybrid: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced search using vector search with traditional semantic analysis fallback
        
        Args:
            user_query: User's search query
            user_context: User context for personalization
            limit: Maximum number of results
            use_hybrid: Whether to use hybrid search
            
        Returns:
            Dict containing search results and metadata
        """
        try:
            logger.info(f"Enhanced vector search for query: '{user_query}'")
            
            # First, enhance query understanding using traditional analysis
            query_analysis = await self.enhance_query_understanding(user_query, user_context)
            
            if self.use_vector_search:
                try:
                    # Convert query analysis to search filters
                    filters = self._convert_analysis_to_filters(query_analysis)
                    
                    # Perform vector search
                    if use_hybrid:
                        search_result = await vector_search_service.hybrid_search(
                            query=user_query,
                            filters=filters,
                            limit=limit,
                            similarity_threshold=self.vector_search_threshold,
                            user_context=user_context,
                            semantic_weight=0.7,
                            keyword_weight=0.3
                        )
                    else:
                        search_result = await vector_search_service.semantic_search(
                            query=user_query,
                            filters=filters,
                            limit=limit,
                            similarity_threshold=self.vector_search_threshold,
                            user_context=user_context
                        )
                    
                    # Enhance results with traditional semantic analysis
                    enhanced_results = await self._enhance_vector_results(
                        search_result.results,
                        query_analysis,
                        user_context
                    )
                    
                    return {
                        "results": enhanced_results,
                        "total_found": search_result.total_found,
                        "query_analysis": query_analysis,
                        "search_metadata": search_result.search_metadata,
                        "suggestions": search_result.suggestions or [],
                        "search_method": "vector_search",
                        "query_time_ms": search_result.query_time_ms,
                        "hybrid_search": use_hybrid
                    }
                    
                except Exception as vector_error:
                    logger.warning(f"Vector search failed: {vector_error}")
                    if not self.fallback_to_traditional:
                        raise
                    
                    logger.info("Falling back to traditional semantic search")
            
            # Fallback to traditional semantic search
            # This would use the existing find_similar_products method
            # For now, we'll return a structured response indicating fallback
            return {
                "results": [],
                "total_found": 0,
                "query_analysis": query_analysis,
                "search_metadata": {
                    "query": user_query,
                    "fallback_used": True,
                    "timestamp": datetime.now().isoformat()
                },
                "suggestions": await self.generate_semantic_suggestions(query_analysis, user_context),
                "search_method": "traditional_fallback",
                "query_time_ms": 0,
                "hybrid_search": False
            }
            
        except Exception as e:
            logger.error(f"Enhanced vector search failed: {e}")
            return {
                "results": [],
                "total_found": 0,
                "query_analysis": {},
                "search_metadata": {"error": str(e)},
                "suggestions": [],
                "search_method": "error",
                "query_time_ms": 0,
                "hybrid_search": False
            }
    
    def _convert_analysis_to_filters(self, query_analysis: Dict[str, Any]) -> List[SearchFilter]:
        """Convert query analysis to vector search filters"""
        filters = []
        
        try:
            # Category filters
            categories = query_analysis.get("product_categories", [])
            if categories:
                filters.append(SearchFilter(
                    namespace="category",
                    values=categories,
                    operator="allow"
                ))
            
            # Budget filters
            budget_signals = query_analysis.get("budget_signals", [])
            if "budget_conscious" in budget_signals:
                filters.append(SearchFilter(
                    namespace="price_range",
                    values=["0-50", "50-100"],
                    operator="allow"
                ))
            elif "quality_focused" in budget_signals:
                filters.append(SearchFilter(
                    namespace="price_range",
                    values=["200-500", "500+"],
                    operator="allow"
                ))
            
            # Feature-based filters
            key_features = query_analysis.get("key_features", [])
            if key_features:
                # Convert features to searchable attributes
                feature_filters = []
                for feature in key_features[:3]:  # Limit to top 3 features
                    feature_filters.append(feature.lower().replace(" ", "_"))
                
                if feature_filters:
                    filters.append(SearchFilter(
                        namespace="features",
                        values=feature_filters,
                        operator="allow"
                    ))
            
        except Exception as e:
            logger.error(f"Error converting analysis to filters: {e}")
        
        return filters
    
    async def _enhance_vector_results(
        self,
        vector_results: List[Any],
        query_analysis: Dict[str, Any],
        user_context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Enhance vector search results with traditional semantic analysis"""
        try:
            enhanced_results = []
            
            for result in vector_results:
                enhanced_result = {
                    "id": result.id,
                    "score": result.score,
                    "vector_similarity": result.score,
                    "metadata": result.metadata or {},
                    "content": result.content or {}
                }
                
                # Add semantic reasoning from traditional analysis
                if result.content:
                    semantic_score = self._calculate_semantic_similarity(
                        {"title": result.content.get("title", ""),
                         "description": result.content.get("description", "")},
                        query_analysis.get("intent_analysis", ""),
                        query_analysis.get("product_categories", []),
                        query_analysis.get("key_features", []),
                        query_analysis.get("use_case", ""),
                        query_analysis.get("semantic_tags", [])
                    )
                    
                    enhanced_result["semantic_score"] = semantic_score
                    enhanced_result["combined_score"] = (result.score * 0.7) + (semantic_score * 0.3)
                    enhanced_result["reasoning"] = self._generate_similarity_reasoning(
                        {"title": result.content.get("title", "")},
                        query_analysis,
                        enhanced_result["combined_score"]
                    )
                
                enhanced_results.append(enhanced_result)
            
            # Re-sort by combined score
            enhanced_results.sort(key=lambda x: x.get("combined_score", x["score"]), reverse=True)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error enhancing vector results: {e}")
            # Return original results in case of error
            return [{"id": r.id, "score": r.score, "metadata": r.metadata, "content": r.content}
                   for r in vector_results]

# Global instance
semantic_search_service = SemanticSearchService()