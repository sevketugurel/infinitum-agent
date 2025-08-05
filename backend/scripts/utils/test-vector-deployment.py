#!/usr/bin/env python3
"""
Simple test script to verify vector search deployment
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

async def test_vector_search():
    """Test the vector search deployment"""
    try:
        from infinitum.infrastructure.external_services.vector_search_service import vector_search_service
        
        print("🔍 Testing Vector Search Deployment...")
        print(f"Endpoint: {vector_search_service.default_endpoint_name}")
        print(f"Deployed Index: {vector_search_service.default_deployed_index_id}")
        
        # Test basic search
        result = await vector_search_service.semantic_search(
            query="test query",
            limit=5,
            similarity_threshold=0.5
        )
        
        print(f"✅ Search successful!")
        print(f"   Results found: {len(result.results)}")
        print(f"   Total matches: {result.total_found}")
        print(f"   Query time: {result.query_time_ms:.2f}ms")
        print(f"   Embedding time: {result.query_embedding_time_ms:.2f}ms")
        print(f"   Search time: {result.search_time_ms:.2f}ms")
        
        if result.results:
            print("\n📋 Sample Results:")
            for i, item in enumerate(result.results[:3], 1):
                print(f"   {i}. ID: {item.id}, Score: {item.score:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_vector_search())
    sys.exit(0 if success else 1) 