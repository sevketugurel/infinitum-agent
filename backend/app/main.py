from fastapi import FastAPI
from .api.scrape import router as scrape_router
from .db.firestore_client import db  # This will initialize Firebase
from .services.vertex_ai import llm, ask_gemini

app = FastAPI(title="Infinitum AI Agent", version="1.0.0")

# Include routers
app.include_router(scrape_router, prefix="/api/v1", tags=["scraping"])

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/test-vertex")
def test_vertex():
    """Test Vertex AI connection"""
    if llm is None:
        return {
            "status": "error", 
            "error": "Vertex AI not initialized. Check GOOGLE_APPLICATION_CREDENTIALS and GCP project settings."
        }
    
    try:
        response = llm.call("Merhaba, bu bir test mesajıdır. Sadece 'Test başarılı' yaz.")
        return {"status": "success", "response": response}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/test-mock")
def test_mock():
    """Test endpoint without Vertex AI"""
    return {
        "status": "success", 
        "message": "Mock response - Vertex AI not configured",
        "sample_data": {
            "title": "Sony WH-1000XM5",
            "price": "$349.99",
            "brand": "Sony",
            "description": "Wireless noise-canceling headphones"
        }
    }

@app.get("/test-ask-gemini")
def test_ask_gemini(prompt: str = "Hello, please respond with 'Gemini is working correctly!'"):
    """Test the standalone ask_gemini function"""
    try:
        response = ask_gemini(prompt)
        return {
            "status": "success",
            "prompt": prompt, 
            "response": response
        }
    except Exception as e:
        return {
            "status": "error",
            "prompt": prompt,
            "error": str(e)
        }