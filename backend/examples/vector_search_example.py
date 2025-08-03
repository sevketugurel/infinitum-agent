"""
Vector Search System Usage Examples
Demonstrates how to use the comprehensive vector search implementation
"""

import asyncio
import json
from typing import List, Dict, Any

# Import vector search components
from infinitum.infrastructure.external_services.vector_search_service import (
    vector_search_service, SearchFilter, SearchMode
)
from infinitum.infrastructure.external_services.embeddings_service import (
    embeddings_service, EmbeddingRequest
)
from infinitum.infrastructure.external_services.vector_index_service import vector_index_service
from infinitum.infrastructure.external_services.semantic_search_service import semantic_search_service

async def example_1_basic_semantic_search():
    """Example 1: Basic semantic search"""
    print("=== Example 1: Basic Semantic Search ===")
    
    query = "wireless bluetooth headphones with noise cancellation"
    
    try:
        result = await vector_search_service.semantic_search(
            query=query,
            limit=10,
            similarity_threshold=0.7,
            include_metadata=True,
            include_scores=True
        )
        
        print(f"Query: '{query}'")
        print(f"Found {len(result.results)} results in {result.query_time_ms:.2f}ms")
        print(f"Total matches: {result.total_found}")
        
        for i, item in enumerate(result.results[:5], 1):
            print(f"{i}. ID: {item.id}")
            print(f"   Score: {item.score:.3f}")
            if item.content:
                print(f"   Title: {item.content.get('title', 'N/A')}")
            print()
        
        if result.suggestions:
            print("Suggestions:")
            for suggestion in result.suggestions:
                print(f"  - {suggestion}")
        
    except Exception as e:
        print(f"Error: {e}")

async def example_2_search_with_filters():
    """Example 2: Search with filters"""
    print("=== Example 2: Search with Filters ===")
    
    query = "gaming laptop"
    filters = [
        SearchFilter(namespace="category", values=["electronics", "computers"], operator="allow"),
        SearchFilter(namespace="price_range", values=["1000-2000"], operator="allow"),
        SearchFilter(namespace="brand", values=["apple"], operator="deny")
    ]
    
    try:
        result = await vector_search_service.semantic_search(
            query=query,
            filters=filters,
            limit=15,
            similarity_threshold=0.6
        )
        
        print(f"Query: '{query}'")
        print(f"Filters applied: {len(result.filters_applied)}")
        for filter_obj in result.filters_applied:
            print(f"  - {filter_obj.namespace}: {filter_obj.operator} {filter_obj.values}")
        
        print(f"Found {len(result.results)} results")
        for item in result.results[:3]:
            print(f"  - {item.id}: {item.score:.3f}")
        
    except Exception as e:
        print(f"Error: {e}")

async def example_3_batch_embeddings():
    """Example 3: Generate batch embeddings"""
    print("=== Example 3: Batch Embeddings Generation ===")
    
    products = [
        {"id": "prod_1", "text": "Sony WH-1000XM4 Wireless Noise Canceling Headphones"},
        {"id": "prod_2", "text": "Apple AirPods Pro with Active Noise Cancellation"},
        {"id": "prod_3", "text": "Bose QuietComfort 35 II Wireless Bluetooth Headphones"}
    ]
    
    requests = [
        EmbeddingRequest(
            id=product["id"],
            text=product["text"],
            metadata={"category": "audio", "type": "headphones"}
        )
        for product in products
    ]
    
    try:
        result = await embeddings_service.generate_batch_embeddings(
            requests=requests,
            model="vertex-text-embedding-004",
            batch_size=3,
            max_concurrent=2
        )
        
        print(f"Batch processing completed:")
        print(f"  Success: {result.success_count}")
        print(f"  Errors: {result.error_count}")
        print(f"  Total time: {result.total_processing_time:.2f}s")
        print(f"  Model used: {result.model_used}")
        
        for i, embedding_result in enumerate(result.results[:3], 1):
            print(f"\n{i}. ID: {embedding_result.id}")
            print(f"   Dimensions: {len(embedding_result.embedding)}")
            print(f"   Processing time: {embedding_result.processing_time:.3f}s")
            if embedding_result.error:
                print(f"   Error: {embedding_result.error}")
        
    except Exception as e:
        print(f"Error: {e}")

async def example_4_enhanced_semantic_search():
    """Example 4: Enhanced semantic search with traditional analysis"""
    print("=== Example 4: Enhanced Semantic Search ===")
    
    query = "portable bluetooth speaker for outdoor activities"
    user_context = {
        "user_profile": {
            "preferences": {
                "budget_conscious": True,
                "category_interests": ["electronics", "outdoor"]
            }
        },
        "recent_interests": ["camping gear", "portable electronics"]
    }
    
    try:
        result = await semantic_search_service.enhanced_vector_search(
            user_query=query,
            user_context=user_context,
            limit=10,
            use_hybrid=True
        )
        
        print(f"Query: '{query}'")
        print(f"Search method: {result.get('search_method', 'N/A')}")
        print(f"Hybrid search: {result.get('hybrid_search', False)}")
        print(f"Query time: {result.get('query_time_ms', 0):.2f}ms")
        print(f"Found {result.get('total_found', 0)} results")
        
        query_analysis = result.get('query_analysis', {})
        if query_analysis:
            print("\nQuery Analysis:")
            print(f"  Intent: {query_analysis.get('intent_analysis', 'N/A')}")
            print(f"  Categories: {query_analysis.get('product_categories', [])}")
            print(f"  Key features: {query_analysis.get('key_features', [])}")
        
        results = result.get('results', [])
        for item in results[:3]:
            print(f"\nResult: {item.get('id', 'N/A')}")
            print(f"  Combined score: {item.get('combined_score', 0):.3f}")
            if item.get('reasoning'):
                print(f"  Reasoning: {item['reasoning']}")
        
    except Exception as e:
        print(f"Error: {e}")

async def example_5_search_analytics():
    """Example 5: Search analytics and monitoring"""
    print("=== Example 5: Search Analytics ===")
    
    try:
        analytics = await vector_search_service.get_search_analytics(days=7)
        
        print("Search Analytics (Last 7 days):")
        print(f"  Total searches: {analytics.get('total_searches', 0)}")
        print(f"  Average query time: {analytics.get('average_query_time_ms', 0):.2f}ms")
        print(f"  Average results per query: {analytics.get('average_results_per_query', 0):.2f}")
        
        embedding_stats = await embeddings_service.get_embedding_stats()
        
        print(f"\nEmbedding Statistics:")
        print(f"  Cache entries: {embedding_stats.get('cache_entries', 0)}")
        print(f"  Recent batches: {embedding_stats.get('recent_batches', 0)}")
        print(f"  Total embeddings: {embedding_stats.get('total_embeddings_generated', 0)}")
        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    """Run all examples"""
    print("Vector Search System Examples")
    print("=" * 50)
    
    examples = [
        example_1_basic_semantic_search,
        example_2_search_with_filters,
        example_3_batch_embeddings,
        example_4_enhanced_semantic_search,
        example_5_search_analytics
    ]
    
    for i, example_func in enumerate(examples, 1):
        try:
            print(f"\n{'='*20} Running Example {i} {'='*20}")
            await example_func()
            print(f"{'='*50}")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Example {i} failed: {e}")
            continue
    
    print("\nAll examples completed!")

if __name__ == "__main__":
    asyncio.run(main())