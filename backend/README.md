# Infinitum AI Agent Backend

## 🎯 Day 2 - COMPLETED ✅

### Vertex AI + Crawl4AI Integration

**Status: FULLY IMPLEMENTED**

#### ✅ Completed Features:

1. **Gemini API Setup**
   - ✅ `ask_gemini(prompt)` function in `app/services/vertex_ai.py`
   - ✅ Model ID (`gemini-2.0-flash-001`) and region (`us-central1`) loaded from config
   - ✅ Unit tests for Gemini functionality in `tests/test_vertex_ai.py`

2. **Crawl4AI Integration** (Alternative to Firecrawl)
   - ✅ `get_structured_data(url)` function in `app/services/crawl4ai_service.py`
   - ✅ Structured output: `{title, price, brand, image, description}`
   - ✅ Test endpoint: `/api/v1/scrape-crawl4ai?url=<url>`
   - ✅ Fallback to Gemini-based scraping if Crawl4AI fails

3. **Firestore Integration**
   - ✅ Firestore Native mode initialized
   - ✅ `save_product_snapshot()` helper function
   - ✅ Products saved to `products` collection with auto-generated IDs

#### 🚀 Available Endpoints:

- `GET /test-ask-gemini?prompt=<text>` - Test Gemini function directly
- `GET /api/v1/scrape-crawl4ai?url=<url>` - Crawl4AI-powered extraction
- `GET /api/v1/test-crawl4ai` - Test with known working URL
- `GET /api/v1/research-product` - Full CrewAI-powered product research
- `GET /healthz` - Health check
- `GET /test-vertex` - Vertex AI connection test

#### 🔧 Setup Instructions:

1. **Install Dependencies:**
   ```bash
   poetry install
   ```

2. **Environment Variables (.env file):**
   ```
   GOOGLE_API_KEY=your_google_ai_studio_api_key
   SERPAPI_API_KEY=your_serpapi_key
   OPENAI_API_KEY=your_openai_key_optional
   ```

3. **Run Tests:**
   ```bash
   poetry run python test_functionality.py
   poetry run pytest tests/ -v
   ```

4. **Start Server:**
   ```bash
   PYTHONPATH=. poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

#### 🏗️ Architecture:

- **Vertex AI Service:** Direct Gemini integration with fallback handling
- **Crawl4AI Service:** Advanced web scraping with LLM-based extraction
- **Firestore Client:** Document storage and retrieval
- **CrewAI Integration:** Multi-agent product research system
- **FastAPI Endpoints:** RESTful API for all functionality

#### 📊 Day 2 Deliverable Status:

| Requirement | Status | Implementation |
|-------------|---------|----------------|
| Gemini API Setup | ✅ Complete | `vertex_ai.py` with `ask_gemini()` |
| Crawl4AI Setup | ✅ Complete | `crawl4ai_service.py` with `get_structured_data()` |
| Test Endpoint | ✅ Complete | `/api/v1/scrape-crawl4ai?url=` |
| Fallback to Gemini | ✅ Complete | Automatic fallback in `_fallback_extraction()` |
| Firestore Integration | ✅ Complete | `save_product_snapshot()` function |
| Unit Tests | ✅ Complete | `tests/test_vertex_ai.py` and `tests/test_crawl4ai_service.py` |

**✅ EOD Deliverable:** Crawl4AI-powered structured data extraction tested and working across real product pages with Gemini fallback.

---

## Dependencies

See `pyproject.toml` for full dependency list. Key additions for Day 2:
- `crawl4ai` - Advanced web scraping framework
- `pytest` - Unit testing framework
- `google-cloud-aiplatform` - Vertex AI integration
- `firebase-admin` - Firestore integration
- `crewai` - Multi-agent AI framework 