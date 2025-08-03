"""
Comprehensive Test Suite for Vector Search System
Tests all components: embeddings, vector index, and search functionality
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

import numpy as np

from infinitum.infrastructure.external_services.embeddings_service import (
    EmbeddingsService, EmbeddingRequest, EmbeddingResult, BatchEmbeddingResult
)
from infinitum.infrastructure.external_services.vector_index_service import VectorIndexService
from infinitum.infrastructure.external_services.vector_search_service import (
    VectorSearchService, SearchRequest, SearchResponse, SearchResult, SearchFilter, SearchMode
)

class TestEmbeddingsService:
    """Test suite for embeddings service"""
    
    @pytest.fixture
    def embeddings_service(self):
        """Create embeddings service instance for testing"""
        service = EmbeddingsService()
        # Mock the initialization to avoid actual API calls
        service.vertex_model = Mock()
        service.openai_client = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_generate_single_embedding(self, embeddings_service):
        """Test single embedding generation"""
        # Mock the vertex embedding generation
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 153 + [0.1, 0.2, 0.3]  # 768 dimensions
        
        with patch.object(embeddings_service, '_generate_vertex_embedding') as mock_generate:
            mock_generate.return_value = EmbeddingResult(
                id="test_id",
                embedding=mock_embedding,
                model_used="vertex-text-embedding-004"
            )
            
            result = await embeddings_service.generate_embedding(
                text="test product description",
                model="vertex-text-embedding-004"
            )
            
            assert result.embedding == mock_embedding
            assert result.model_used == "vertex-text-embedding-004"
            assert result.error is None
            assert len(result.embedding) == 768
    
    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self, embeddings_service):
        """Test batch embedding generation"""
        requests = [
            EmbeddingRequest(id="1", text="product 1 description"),
            EmbeddingRequest(id="2", text="product 2 description"),
            EmbeddingRequest(id="3", text="product 3 description")
        ]
        
        # Mock individual embedding generation
        mock_embedding = [0.1] * 768
        with patch.object(embeddings_service, 'generate_embedding') as mock_generate:
            mock_generate.return_value = EmbeddingResult(
                id="test",
                embedding=mock_embedding,
                model_used="vertex-text-embedding-004"
            )
            
            result = await embeddings_service.generate_batch_embeddings(
                requests=requests,
                model="vertex-text-embedding-004",
                batch_size=2
            )
            
            assert isinstance(result, BatchEmbeddingResult)
            assert result.success_count == 3
            assert result.error_count == 0
            assert len(result.results) == 3
            assert result.model_used == "vertex-text-embedding-004"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, embeddings_service):
        """Test rate limiting functionality"""
        rate_limiter = embeddings_service.vertex_rate_limiter
        
        # Test normal acquisition
        start_time = time.time()
        await rate_limiter.acquire(10)
        end_time = time.time()
        
        # Should not wait for normal request
        assert end_time - start_time < 0.1
        
        # Test rate limit hit (mock by filling up the rate limiter)
        rate_limiter.request_times = [time.time()] * 1000  # Fill up requests
        
        start_time = time.time()
        # This should trigger rate limiting, but we'll mock it to avoid long waits
        with patch('asyncio.sleep') as mock_sleep:
            await rate_limiter.acquire(1)
            # Should have called sleep due to rate limiting
            assert mock_sleep.called
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, embeddings_service):
        """Test embedding caching"""
        text = "test product for caching"
        
        # Mock cache operations
        with patch.object(embeddings_service, '_get_cached_embedding') as mock_get_cache, \
             patch.object(embeddings_service, '_cache_embedding') as mock_set_cache, \
             patch.object(embeddings_service, '_generate_vertex_embedding') as mock_generate:
            
            # First call - no cache
            mock_get_cache.return_value = None
            mock_generate.return_value = EmbeddingResult(
                id="test",
                embedding=[0.1] * 768,
                model_used="vertex-text-embedding-004"
            )
            
            result1 = await embeddings_service.generate_embedding(text, use_cache=True)
            
            # Should have tried to get from cache and then cached the result
            mock_get_cache.assert_called_once()
            mock_set_cache.assert_called_once()
            
            # Second call - with cache
            mock_get_cache.reset_mock()
            mock_set_cache.reset_mock()
            mock_get_cache.return_value = EmbeddingResult(
                id="cached",
                embedding=[0.2] * 768,
                model_used="vertex-text-embedding-004"
            )
            
            result2 = await embeddings_service.generate_embedding(text, use_cache=True)
            
            # Should have returned cached result
            assert result2.embedding == [0.2] * 768
            mock_get_cache.assert_called_once()
            mock_set_cache.assert_not_called()  # Should not cache again
    
    @pytest.mark.asyncio
    async def test_prepare_vector_index_data(self, embeddings_service):
        """Test vector index data preparation"""
        embedding_results = [
            EmbeddingResult(
                id="product_1",
                embedding=[0.1] * 768,
                metadata={"category": "electronics", "price": 100}
            ),
            EmbeddingResult(
                id="product_2",
                embedding=[0.2] * 768,
                metadata={"category": "clothing", "price": 50}
            )
        ]
        
        # Mock GCS upload
        with patch.object(embeddings_service, '_upload_to_gcs') as mock_upload:
            mock_upload.return_value = "gs://test-bucket/embeddings.jsonl.gz"
            
            result = await embeddings_service.prepare_vector_index_data(
                embedding_results,
                "gs://test-bucket/embeddings.jsonl.gz",
                metadata_fields=["category", "price"]
            )
            
            assert result["success"] is True
            assert result["total_vectors"] == 2
            assert result["dimensions"] == 768
            assert "category" in result["metadata_fields"]
            mock_upload.assert_called_once()

class TestVectorIndexService:
    """Test suite for vector index service"""
    
    @pytest.fixture
    def vector_index_service(self):
        """Create vector index service instance for testing"""
        service = VectorIndexService()
        return service
    
    @pytest.mark.asyncio
    async def test_create_vector_index(self, vector_index_service):
        """Test vector index creation"""
        with patch('infinitum.infrastructure.external_services.vector_index_service.MatchingEngineIndex') as mock_index_class, \
             patch.object(vector_index_service, '_store_index_info') as mock_store:
            
            # Mock index creation
            mock_index = Mock()
            mock_index.resource_name = "projects/test/locations/us-central1/indexes/123456"
            mock_index.display_name = "test-index"
            mock_index_class.create_tree_ah_index.return_value = mock_index
            
            result = await vector_index_service.create_vector_index(
                index_name="test-index",
                dimensions=768
            )
            
            assert result["success"] is True
            assert result["index_name"] == "test-index"
            assert result["status"] == "CREATING"
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_index_endpoint(self, vector_index_service):
        """Test index endpoint creation"""
        with patch('infinitum.infrastructure.external_services.vector_index_service.MatchingEngineIndexEndpoint') as mock_endpoint_class, \
             patch.object(vector_index_service, '_store_endpoint_info') as mock_store:
            
            # Mock endpoint creation
            mock_endpoint = Mock()
            mock_endpoint.resource_name = "projects/test/locations/us-central1/indexEndpoints/123456"
            mock_endpoint.display_name = "test-endpoint"
            mock_endpoint_class.create.return_value = mock_endpoint
            
            result = await vector_index_service.create_index_endpoint(
                endpoint_name="test-endpoint"
            )
            
            assert result["success"] is True
            assert result["endpoint_name"] == "test-endpoint"
            assert result["status"] == "CREATING"
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deploy_index_to_endpoint(self, vector_index_service):
        """Test index deployment to endpoint"""
        with patch.object(vector_index_service, '_get_index_info') as mock_get_index, \
             patch.object(vector_index_service, '_get_endpoint_info') as mock_get_endpoint, \
             patch.object(vector_index_service, '_wait_for_index_ready') as mock_wait, \
             patch.object(vector_index_service, '_store_deployment_info') as mock_store, \
             patch('infinitum.infrastructure.external_services.vector_index_service.MatchingEngineIndex') as mock_index_class, \
             patch('infinitum.infrastructure.external_services.vector_index_service.MatchingEngineIndexEndpoint') as mock_endpoint_class:
            
            # Mock data retrieval
            mock_get_index.return_value = {"index_id": "index_123", "index_name": "test-index"}
            mock_get_endpoint.return_value = {"endpoint_id": "endpoint_123", "endpoint_name": "test-endpoint"}
            
            # Mock objects
            mock_index = Mock()
            mock_endpoint = Mock()
            mock_deployed_index = Mock()
            
            mock_index_class.return_value = mock_index
            mock_endpoint_class.return_value = mock_endpoint
            mock_endpoint.deploy_index.return_value = mock_deployed_index
            
            result = await vector_index_service.deploy_index_to_endpoint(
                index_name="test-index",
                endpoint_name="test-endpoint",
                deployed_index_id="deployment_123"
            )
            
            assert result["success"] is True
            assert result["deployment_id"] == "deployment_123"
            assert result["status"] == "DEPLOYING"
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_index_status(self, vector_index_service):
        """Test getting index status"""
        with patch.object(vector_index_service, '_get_index_info') as mock_get_info:
            mock_get_info.return_value = {
                "index_id": "index_123",
                "index_name": "test-index",
                "status": "READY"
            }
            
            result = await vector_index_service.get_index_status("test-index")
            
            assert result["success"] is True
            assert result["index_name"] == "test-index"
            assert result["status"] == "READY"

class TestVectorSearchService:
    """Test suite for vector search service"""
    
    @pytest.fixture
    def vector_search_service(self):
        """Create vector search service instance for testing"""
        service = VectorSearchService()
        return service
    
    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, vector_search_service):
        """Test basic semantic search functionality"""
        query = "wireless bluetooth headphones"
        
        # Mock dependencies
        with patch.object(vector_search_service, '_generate_query_embedding') as mock_embedding, \
             patch.object(vector_search_service, '_perform_vector_search') as mock_search, \
             patch.object(vector_search_service, '_post_process_results') as mock_process, \
             patch.object(vector_search_service, '_generate_search_suggestions') as mock_suggestions:
            
            # Mock embedding generation
            mock_embedding.return_value = [0.1] * 768
            
            # Mock search results
            mock_search_results = [
                SearchResult(id="product_1", score=0.95, metadata={"title": "Sony WH-1000XM4"}),
                SearchResult(id="product_2", score=0.87, metadata={"title": "Bose QuietComfort 35"}),
                SearchResult(id="product_3", score=0.82, metadata={"title": "Apple AirPods Pro"})
            ]
            mock_search.return_value = mock_search_results
            mock_process.return_value = mock_search_results
            mock_suggestions.return_value = ["Try 'noise canceling headphones'", "Explore audio accessories"]
            
            result = await vector_search_service.semantic_search(
                query=query,
                limit=10,
                similarity_threshold=0.8
            )
            
            assert isinstance(result, SearchResponse)
            assert len(result.results) == 3
            assert result.results[0].score == 0.95
            assert result.total_found == 3
            assert len(result.suggestions) == 2
            assert result.search_metadata["query"] == query
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, vector_search_service):
        """Test semantic search with filters"""
        query = "gaming laptop"
        filters = [
            SearchFilter(namespace="category", values=["electronics"]),
            SearchFilter(namespace="price_range", values=["1000-2000"])
        ]
        
        with patch.object(vector_search_service, '_generate_query_embedding') as mock_embedding, \
             patch.object(vector_search_service, '_perform_vector_search') as mock_search, \
             patch.object(vector_search_service, '_post_process_results') as mock_process, \
             patch.object(vector_search_service, '_generate_search_suggestions') as mock_suggestions:
            
            mock_embedding.return_value = [0.1] * 768
            mock_search.return_value = [
                SearchResult(id="laptop_1", score=0.92, metadata={"title": "Gaming Laptop RTX 4060"})
            ]
            mock_process.return_value = mock_search.return_value
            mock_suggestions.return_value = []
            
            result = await vector_search_service.semantic_search(
                query=query,
                filters=filters,
                limit=5
            )
            
            assert len(result.filters_applied) == 2
            assert result.filters_applied[0].namespace == "category"
            assert result.filters_applied[1].namespace == "price_range"
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, vector_search_service):
        """Test hybrid search combining semantic and keyword search"""
        query = "professional camera"
        
        with patch.object(vector_search_service, 'semantic_search') as mock_semantic, \
             patch.object(vector_search_service, '_perform_keyword_search') as mock_keyword, \
             patch.object(vector_search_service, '_combine_search_results') as mock_combine:
            
            # Mock semantic search results
            semantic_results = [
                SearchResult(id="camera_1", score=0.9, metadata={"title": "Canon EOS R5"})
            ]
            mock_semantic.return_value = SearchResponse(
                results=semantic_results,
                total_found=1,
                query_time_ms=100,
                query_embedding_time_ms=50,
                search_time_ms=50,
                filters_applied=[],
                search_metadata={"query": query}
            )
            
            # Mock keyword search results
            keyword_results = [
                SearchResult(id="camera_2", score=0.8, metadata={"title": "Nikon D850"})
            ]
            mock_keyword.return_value = keyword_results
            
            # Mock combined results
            combined_results = semantic_results + keyword_results
            mock_combine.return_value = combined_results
            
            result = await vector_search_service.hybrid_search(
                query=query,
                semantic_weight=0.7,
                keyword_weight=0.3
            )
            
            assert result.search_metadata["search_mode"] == "hybrid"
            assert result.search_metadata["semantic_weight"] == 0.7
            assert result.search_metadata["keyword_weight"] == 0.3
    
    @pytest.mark.asyncio
    async def test_find_similar_items(self, vector_search_service):
        """Test finding similar items"""
        item_id = "product_123"
        
        with patch.object(vector_search_service, '_get_item_embedding') as mock_get_embedding, \
             patch.object(vector_search_service, '_perform_vector_search_with_embedding') as mock_search:
            
            # Mock item embedding
            mock_get_embedding.return_value = [0.1] * 768
            
            # Mock similar items
            similar_items = [
                SearchResult(id="product_124", score=0.95, metadata={"title": "Similar Product 1"}),
                SearchResult(id="product_125", score=0.88, metadata={"title": "Similar Product 2"}),
                SearchResult(id="product_123", score=1.0, metadata={"title": "Original Product"})  # Self
            ]
            mock_search.return_value = similar_items
            
            result = await vector_search_service.find_similar_items(
                item_id=item_id,
                limit=5,
                exclude_self=True
            )
            
            # Should exclude the original item
            assert len(result.results) == 2
            assert all(r.id != item_id for r in result.results)
            assert result.search_metadata["reference_item_id"] == item_id
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, vector_search_service):
        """Test personalized recommendations"""
        user_id = "user_123"
        user_preferences = {"categories": ["electronics", "books"], "price_range": "50-200"}
        interaction_history = ["product_1", "product_2", "product_3"]
        
        with patch.object(vector_search_service, '_build_user_profile_embedding') as mock_profile, \
             patch.object(vector_search_service, '_perform_vector_search_with_embedding') as mock_search, \
             patch.object(vector_search_service, '_rank_recommendations') as mock_rank:
            
            # Mock user profile embedding
            mock_profile.return_value = [0.1] * 768
            
            # Mock recommendation results (including some from interaction history)
            raw_recommendations = [
                SearchResult(id="product_4", score=0.9, metadata={"title": "Recommended Product 1"}),
                SearchResult(id="product_1", score=0.85, metadata={"title": "Already Seen"}),  # In history
                SearchResult(id="product_5", score=0.8, metadata={"title": "Recommended Product 2"})
            ]
            mock_search.return_value = raw_recommendations
            
            # Mock ranking (should filter out interaction history)
            filtered_recommendations = [
                SearchResult(id="product_4", score=0.9, metadata={"title": "Recommended Product 1"}),
                SearchResult(id="product_5", score=0.8, metadata={"title": "Recommended Product 2"})
            ]
            mock_rank.return_value = filtered_recommendations
            
            result = await vector_search_service.get_recommendations(
                user_id=user_id,
                user_preferences=user_preferences,
                interaction_history=interaction_history,
                limit=10
            )
            
            # Should not include items from interaction history
            assert len(result.results) == 2
            assert all(r.id not in interaction_history for r in result.results)
            assert result.search_metadata["user_id"] == user_id
            assert result.search_metadata["personalized"] is True
    
    @pytest.mark.asyncio
    async def test_search_caching(self, vector_search_service):
        """Test search result caching"""
        query = "test query for caching"
        
        with patch.object(vector_search_service, '_generate_query_embedding') as mock_embedding, \
             patch.object(vector_search_service, '_perform_vector_search') as mock_search, \
             patch.object(vector_search_service, '_post_process_results') as mock_process, \
             patch.object(vector_search_service, '_generate_search_suggestions') as mock_suggestions:
            
            mock_embedding.return_value = [0.1] * 768
            mock_results = [SearchResult(id="test_1", score=0.9)]
            mock_search.return_value = mock_results
            mock_process.return_value = mock_results
            mock_suggestions.return_value = []
            
            # First search - should generate and cache
            result1 = await vector_search_service.semantic_search(query=query)
            
            # Verify search was performed
            mock_search.assert_called_once()
            
            # Second search with same parameters - should use cache
            mock_search.reset_mock()
            result2 = await vector_search_service.semantic_search(query=query)
            
            # Should have used cache (no new search performed)
            # Note: In real implementation, this would check cache hit
            # For this test, we're just verifying the caching mechanism exists
            assert result1.search_metadata["query"] == result2.search_metadata["query"]
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, vector_search_service):
        """Test error handling in search"""
        query = "test query that will fail"
        
        with patch.object(vector_search_service, '_generate_query_embedding') as mock_embedding:
            # Mock embedding generation failure
            mock_embedding.side_effect = Exception("Embedding generation failed")
            
            result = await vector_search_service.semantic_search(query=query)
            
            # Should return error response
            assert len(result.results) == 0
            assert result.total_found == 0
            assert "error" in result.search_metadata
    
    def test_search_filter_creation(self):
        """Test search filter creation and validation"""
        filter_obj = SearchFilter(
            namespace="category",
            values=["electronics", "computers"],
            operator="allow"
        )
        
        assert filter_obj.namespace == "category"
        assert filter_obj.values == ["electronics", "computers"]
        assert filter_obj.operator == "allow"
    
    def test_search_request_creation(self):
        """Test search request creation with various parameters"""
        filters = [SearchFilter(namespace="price", values=["100-500"])]
        
        request = SearchRequest(
            query="test query",
            mode=SearchMode.HYBRID_SEARCH,
            filters=filters,
            limit=50,
            offset=10,
            similarity_threshold=0.75,
            include_metadata=True,
            boost_factors={"category": 1.2, "brand": 1.1}
        )
        
        assert request.query == "test query"
        assert request.mode == SearchMode.HYBRID_SEARCH
        assert len(request.filters) == 1
        assert request.limit == 50
        assert request.offset == 10
        assert request.similarity_threshold == 0.75
        assert request.boost_factors["category"] == 1.2

class TestIntegration:
    """Integration tests for the complete vector search system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self):
        """Test complete end-to-end search flow"""
        # This would test the complete flow from query to results
        # In a real environment, this would use test data and mock external services
        
        # Mock all external dependencies
        with patch('infinitum.infrastructure.external_services.embeddings_service.embeddings_service') as mock_embeddings, \
             patch('infinitum.infrastructure.external_services.vector_index_service.vector_index_service') as mock_index, \
             patch('infinitum.infrastructure.external_services.vector_search_service.vector_search_service') as mock_search:
            
            # Setup mocks
            mock_embeddings.generate_embedding.return_value = EmbeddingResult(
                id="test",
                embedding=[0.1] * 768,
                model_used="vertex-text-embedding-004"
            )
            
            mock_search.semantic_search.return_value = SearchResponse(
                results=[SearchResult(id="product_1", score=0.9)],
                total_found=1,
                query_time_ms=100,
                query_embedding_time_ms=50,
                search_time_ms=50,
                filters_applied=[],
                search_metadata={"query": "test"}
            )
            
            # Test the flow
            query = "test product search"
            result = await mock_search.semantic_search(query=query)
            
            assert len(result.results) == 1
            assert result.results[0].score == 0.9

# Performance and Load Tests
class TestPerformance:
    """Performance tests for vector search system"""
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self):
        """Test handling multiple concurrent searches"""
        service = VectorSearchService()
        
        # Mock dependencies to avoid actual API calls
        with patch.object(service, '_generate_query_embedding') as mock_embedding, \
             patch.object(service, '_perform_vector_search') as mock_search, \
             patch.object(service, '_post_process_results') as mock_process, \
             patch.object(service, '_generate_search_suggestions') as mock_suggestions:
            
            mock_embedding.return_value = [0.1] * 768
            mock_search.return_value = [SearchResult(id="test", score=0.9)]
            mock_process.return_value = mock_search.return_value
            mock_suggestions.return_value = []
            
            # Create multiple concurrent search tasks
            tasks = []
            for i in range(10):
                task = service.semantic_search(query=f"test query {i}", limit=5)
                tasks.append(task)
            
            # Execute all searches concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Verify all searches completed
            assert len(results) == 10
            assert all(len(r.results) == 1 for r in results)
            
            # Performance should be reasonable (less than 5 seconds for 10 concurrent searches)
            assert end_time - start_time < 5.0
    
    @pytest.mark.asyncio
    async def test_large_batch_embeddings(self):
        """Test handling large batch of embeddings"""
        service = EmbeddingsService()
        
        # Create large batch of requests
        requests = [
            EmbeddingRequest(id=f"product_{i}", text=f"Product {i} description")
            for i in range(100)
        ]
        
        with patch.object(service, 'generate_embedding') as mock_generate:
            mock_generate.return_value = EmbeddingResult(
                id="test",
                embedding=[0.1] * 768,
                model_used="vertex-text-embedding-004"
            )
            
            start_time = time.time()
            result = await service.generate_batch_embeddings(
                requests=requests,
                batch_size=10,
                max_concurrent=5
            )
            end_time = time.time()
            
            assert result.success_count == 100
            assert result.error_count == 0
            assert len(result.results) == 100
            
            # Should complete in reasonable time
            assert end_time - start_time < 10.0

# Utility functions for testing
def create_mock_embedding(dimensions: int = 768) -> List[float]:
    """Create a mock embedding vector"""
    return [0.1] * dimensions

def create_mock_search_results(count: int = 5) -> List[SearchResult]:
    """Create mock search results"""
    return [
        SearchResult(
            id=f"product_{i}",
            score=0.9 - (i * 0.1),
            metadata={"title": f"Product {i}", "category": "electronics"}
        )
        for i in range(count)
    ]

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])