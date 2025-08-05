# Vector Search Deployment Troubleshooting Guide

## 🚨 Issue Resolution for Deployment Errors

The deployment script encountered several gcloud CLI compatibility issues. Here's how to resolve them and continue with your vector search implementation.

## 🔧 Immediate Solution

### Step 1: Use the Simplified Deployment Script

```bash
# Use the new simplified script instead
./backend/infra/deploy-vector-search-simple.sh --with-sample-data
```

This script will:
- ✅ Create the GCS bucket successfully
- ✅ Generate proper 768-dimensional sample embeddings
- ✅ Provide manual deployment instructions for the console
- ✅ Avoid gcloud CLI version conflicts

### Step 2: Manual Deployment in Google Cloud Console

Since the gcloud CLI commands have version compatibility issues, complete the deployment manually:

1. **Go to Vertex AI Vector Search Console**:
   - Visit: https://console.cloud.google.com/vertex-ai/matching-engine/indexes
   - Select project: `infinitum-agent`

2. **Create Vector Index**:
   ```
   Name: product-semantic-index-production
   Description: Vector index for product semantic search
   Region: us-central1
   Dimensions: 768
   Distance measure: Cosine distance
   Algorithm: Tree-AH
   Leaf node embedding count: 500
   Leaf nodes to search percent: 7
   Update method: Batch update
   ```

3. **Create Index Endpoint**:
   ```
   Name: product-search-endpoint-production
   Region: us-central1
   Network: Default
   ```

4. **Deploy Index to Endpoint**:
   ```
   Deployed index ID: product_search_v1_production
   Machine type: n1-standard-2
   Min replicas: 1
   Max replicas: 3
   ```

## 🛠 Alternative: Use Python Services Directly

You can bypass the deployment script entirely and use the Python services:

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Test the Services Without Deployment

```python
# Test embeddings generation
from infinitum.infrastructure.external_services.embeddings_service import embeddings_service

# This will work even without vector index deployment
result = await embeddings_service.generate_embedding(
    text="wireless bluetooth headphones",
    model="vertex-text-embedding-004"
)
print(f"Generated {len(result.embedding)}-dimensional embedding")
```

### Step 3: Use Enhanced Semantic Search

```python
# Use the enhanced semantic search with fallback
from infinitum.infrastructure.external_services.semantic_search_service import semantic_search_service

result = await semantic_search_service.enhanced_vector_search(
    user_query="wireless headphones",
    user_context={"user_profile": {"preferences": {"budget_conscious": True}}},
    limit=10,
    use_hybrid=True
)

# This will fall back to traditional search if vector search isn't available
print(f"Search method used: {result['search_method']}")
print(f"Found {result['total_found']} results")
```

## 🔍 Root Cause Analysis

The deployment errors occurred due to:

1. **Service Account Issue**: 
   - Error: `Service account infinitum-agent@appspot.gserviceaccount.com does not exist`
   - Solution: Used correct service account `87113618847-compute@developer.gserviceaccount.com`

2. **gcloud CLI Version Conflicts**:
   - Error: `unrecognized arguments: --config-file`
   - Solution: Updated to use inline metadata format

3. **Operation Wait Command Changes**:
   - Error: `Invalid choice: 'wait'`
   - Solution: Use `gcloud ai-platform operations wait` instead

4. **Variable Expansion Issues**:
   - Error: Bucket name showing as `[INFO]` instead of actual name
   - Solution: Fixed variable scoping in bash functions

## 🚀 Continue Without Full Deployment

You can still use most of the vector search functionality:

### 1. Test Embeddings Service

```bash
# Run the embeddings tests
pytest backend/tests/test_vector_search.py::TestEmbeddingsService -v
```

### 2. Test Enhanced Semantic Search

```bash
# Run the semantic search tests
pytest backend/tests/test_vector_search.py::TestVectorSearchService -v
```

### 3. Run Examples

```bash
# Run usage examples (will use fallback methods)
python backend/examples/vector_search_example.py
```

## 📋 Next Steps Priority

### High Priority (Can Do Now)
1. ✅ **Test Embeddings Generation**: Works without vector index
2. ✅ **Integrate Enhanced Semantic Search**: Has intelligent fallback
3. ✅ **Update Your API Endpoints**: Use the enhanced search service
4. ✅ **Generate Product Embeddings**: Prepare your data

### Medium Priority (After Manual Deployment)
1. 🔄 **Complete Manual Deployment**: Follow console instructions
2. 🔄 **Update Configuration**: Set endpoint and index IDs
3. 🔄 **Test Vector Search**: Verify full functionality

### Low Priority (Optimization)
1. ⏳ **Performance Tuning**: Optimize similarity thresholds
2. ⏳ **Monitoring Setup**: Add analytics dashboards
3. ⏳ **Scale Testing**: Test with larger datasets

## 🔧 Quick Integration Guide

### Update Your Existing API

Add this to your existing search endpoints:

```python
# In backend/src/infinitum/infrastructure/http/packages.py
from infinitum.infrastructure.external_services.semantic_search_service import semantic_search_service

@app.post("/api/enhanced-search")
async def enhanced_search(request: dict):
    """Enhanced search with vector search and fallback"""
    try:
        result = await semantic_search_service.enhanced_vector_search(
            user_query=request.get("query", ""),
            user_context=request.get("user_context", {}),
            limit=request.get("limit", 20),
            use_hybrid=True
        )
        
        return {
            "success": True,
            "results": result["results"],
            "total_found": result["total_found"],
            "search_method": result["search_method"],
            "query_time_ms": result["query_time_ms"],
            "suggestions": result["suggestions"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Test the Integration

```bash
# Test your enhanced API
curl -X POST http://localhost:8080/api/enhanced-search \
  -H "Content-Type: application/json" \
  -d '{"query": "wireless headphones", "limit": 10}'
```

## 📞 Support

If you encounter more issues:

1. **Check the logs**: All services include comprehensive logging
2. **Enable debug mode**: Add `debug=True` to search calls
3. **Review the documentation**: [`vector-search-guide.md`](backend/docs/vector-search-guide.md:1)
4. **Run the examples**: [`vector_search_example.py`](backend/examples/vector_search_example.py:1)

## ✅ Success Indicators

You'll know the system is working when:

- ✅ Embeddings service generates 768-dimensional vectors
- ✅ Enhanced semantic search returns results (even with fallback)
- ✅ Your API endpoints respond with enhanced search results
- ✅ Tests pass for the implemented components

The vector search system is designed to work gracefully with fallbacks, so you can start using the enhanced functionality immediately while completing the full deployment manually.