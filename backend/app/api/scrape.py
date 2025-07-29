# File: app/api/scrape.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..crew.product_crew import product_crew
from ..db.firestore_client import save_product_snapshot
from ..services.crawl4ai_service import get_structured_data_sync
import time
import json
from litellm.exceptions import InternalServerError, ServiceUnavailableError, RateLimitError

router = APIRouter()

class ResearchQuery(BaseModel):
    product_query: str

def get_user_friendly_error_message(error_str: str) -> str:
    """Convert technical errors into user-friendly messages."""
    error_lower = error_str.lower()
    
    if "overloaded" in error_lower or "503" in error_str:
        return "The AI service is currently experiencing high demand. Please try again in a few moments."
    elif "rate limit" in error_lower or "429" in error_str:
        return "Too many requests. Please wait a moment before trying again."
    elif "api key" in error_lower or "unauthorized" in error_lower or "401" in error_str:
        return "API authentication issue. Please contact support."
    elif "timeout" in error_lower:
        return "The request took too long to process. Please try again with a simpler query."
    elif "quota" in error_lower:
        return "Service quota exceeded. Please try again later."
    else:
        return "An unexpected error occurred during research. Please try again."

@router.post("/research-product", status_code=201)
def research_product(query: ResearchQuery):
    """Triggers the product research crew and saves the result with robust error handling."""
    inputs = {'product_query': query.product_query}
    max_retries = 2
    base_delay = 2.0
    
    for attempt in range(max_retries + 1):
        try:
            print(f"Starting research for: {query.product_query} (attempt {attempt + 1}/{max_retries + 1})")
            
            # Add a small delay between retries to avoid overwhelming the service
            if attempt > 0:
                delay = base_delay * attempt
                print(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
            
            result = product_crew.kickoff(inputs=inputs)
            print(f"Crew result: {result}")
            
            # The result from the crew should be the final JSON object
            if not result:
                if attempt < max_retries:
                    print("Crew returned empty result, retrying...")
                    continue
                raise HTTPException(status_code=500, detail="The research crew could not generate results. Please try with a different product query.")
            
            # Save the structured data to Firestore
            try:
                # Extract the actual data from CrewOutput object
                product_data = None
                
                # Try pydantic first (if available and not empty)
                if hasattr(result, 'pydantic') and result.pydantic and hasattr(result.pydantic, 'model_dump'):
                    try:
                        product_data = result.pydantic.model_dump()
                        print("Using pydantic data for saving")
                    except:
                        pass
                
                # If pydantic failed, try json_dict
                if not product_data and hasattr(result, 'json_dict') and result.json_dict:
                    product_data = result.json_dict
                    print("Using json_dict data for saving")
                
                # If both failed, try parsing the raw JSON string
                if not product_data and hasattr(result, 'raw') and result.raw:
                    try:
                        # The raw output might be a JSON string
                        raw_str = str(result.raw).strip()
                        if raw_str.startswith('{') and raw_str.endswith('}'):
                            product_data = json.loads(raw_str)
                            print("Using parsed raw JSON data for saving")
                        else:
                            print(f"Raw data is not JSON format: {raw_str[:100]}...")
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse raw JSON: {e}")
                
                # Fallback: create a basic structure
                if not product_data:
                    print("Creating fallback product data structure")
                    product_data = {"raw_output": str(result)}
                
                # Validate the product data structure
                if product_data and isinstance(product_data, dict):
                    # Ensure we have at least a title for the document ID
                    if not product_data.get('title') and not product_data.get('raw_output'):
                        product_data['title'] = 'Unknown Product'
                    
                    document_id = save_product_snapshot(product_data)
                    if document_id:
                        print(f"Successfully saved to Firestore with document ID: {document_id}")
                        return {"document_id": document_id, "data": result}
                    else:
                        print("Failed to save to Firestore - no document ID returned")
                else:
                    print(f"Invalid product data format: {type(product_data)}")
                
                # If we get here, saving failed but we still have results
                return {"document_id": None, "data": result, "warning": "Research completed but could not save to database"}
                
            except Exception as save_error:
                print(f"Error saving to Firestore: {str(save_error)}")
                # Still return the result even if saving fails
                return {"document_id": None, "data": result, "warning": "Research completed but could not save to database"}
        
        except (InternalServerError, ServiceUnavailableError, RateLimitError) as llm_error:
            error_message = str(llm_error)
            print(f"LLM service error on attempt {attempt + 1}: {error_message}")
            
            if attempt < max_retries:
                print(f"Retrying due to temporary service issue...")
                continue
            else:
                user_message = get_user_friendly_error_message(error_message)
                raise HTTPException(status_code=503, detail=user_message)
        
        except Exception as e:
            error_str = str(e)
            print(f"Error in research_product (attempt {attempt + 1}): {error_str}")
            
            # Check if this is a retryable error
            if any(keyword in error_str.lower() for keyword in ["overloaded", "503", "timeout", "temporary"]):
                if attempt < max_retries:
                    print("Detected retryable error, will retry...")
                    continue
            
            # Non-retryable error or max retries reached
            user_message = get_user_friendly_error_message(error_str)
            raise HTTPException(status_code=500, detail=user_message)
    
    # This should never be reached, but just in case
    raise HTTPException(status_code=500, detail="Research failed after multiple attempts. Please try again later.")

@router.get("/scrape-crawl4ai")
async def scrape_crawl4ai(url: str):
    """
    Test endpoint for Crawl4AI-powered structured data extraction.
    
    Query Parameters:
        url (str): The product page URL to scrape
        
    Returns:
        Dict: Structured product data including title, price, brand, image, description
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    
    if not url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    
    try:
        print(f"Starting Crawl4AI extraction for URL: {url}")
        
        # Extract structured data using Crawl4AI
        product_data = get_structured_data_sync(url)
        
        if not product_data:
            raise HTTPException(status_code=500, detail="Failed to extract product data")
        
        # Save to Firestore if extraction was successful
        document_id = None
        if product_data.get("title") and product_data["title"] != "Product title not found":
            try:
                document_id = save_product_snapshot(product_data)
                print(f"Saved to Firestore with document ID: {document_id}")
            except Exception as save_error:
                print(f"Failed to save to Firestore: {save_error}")
                # Don't fail the request if saving fails
        
        return {
            "status": "success",
            "url": url,
            "data": product_data,
            "document_id": document_id,
            "extraction_method": product_data.get("extraction_method", "unknown")
        }
        
    except Exception as e:
        error_message = str(e)
        print(f"Error in scrape_crawl4ai: {error_message}")
        
        # Return user-friendly error
        if "timeout" in error_message.lower():
            raise HTTPException(status_code=408, detail="Request timeout - the website took too long to respond")
        elif "connection" in error_message.lower():
            raise HTTPException(status_code=502, detail="Could not connect to the website")
        elif "not found" in error_message.lower() or "404" in error_message:
            raise HTTPException(status_code=404, detail="The requested page was not found")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to scrape URL: {error_message}")

@router.get("/test-crawl4ai")
async def test_crawl4ai():
    """
    Test endpoint to verify Crawl4AI setup with a known working URL.
    """
    test_url = "https://www.amazon.com/dp/B0BDV6Q9LL"  # Sony headphones
    
    try:
        result = await scrape_crawl4ai(test_url)
        return {
            "status": "success",
            "message": "Crawl4AI test completed successfully",
            "test_url": test_url,
            "result": result
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": "Crawl4AI test failed",
            "error": str(e),
            "test_url": test_url
        }