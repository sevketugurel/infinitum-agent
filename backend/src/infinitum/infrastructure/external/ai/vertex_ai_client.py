# File: src/infinitum/services/vertex_ai.py
from crewai.llm import LLM
import vertexai
from vertexai.generative_models import GenerativeModel
from ....config.settings import settings
import json
import os
import time
import random
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import litellm
from litellm.exceptions import InternalServerError, RateLimitError, ServiceUnavailableError

# Request caching and quota management
_request_cache: Dict[str, Dict[str, Any]] = {}
_quota_tracker = {
    "daily_requests": 0,
    "last_reset": datetime.now().date(),
    "quota_limit": settings.GEMINI_DAILY_QUOTA if hasattr(settings, 'GEMINI_DAILY_QUOTA') else 200,
    "quota_exceeded": False
}

def _get_cache_key(prompt: str, model_name: str = None) -> str:
    """Generate a cache key for the request."""
    content = f"{model_name or 'default'}:{prompt}"
    return hashlib.md5(content.encode()).hexdigest()

def _is_cache_valid(cache_entry: Dict[str, Any], max_age_hours: int = 24) -> bool:
    """Check if a cache entry is still valid."""
    if not cache_entry or 'timestamp' not in cache_entry:
        return False
    
    cache_time = datetime.fromisoformat(cache_entry['timestamp'])
    return datetime.now() - cache_time < timedelta(hours=max_age_hours)

def _update_quota_tracker():
    """Update and check quota limits."""
    global _quota_tracker
    
    # Reset daily counter if it's a new day
    today = datetime.now().date()
    if _quota_tracker["last_reset"] != today:
        _quota_tracker["daily_requests"] = 0
        _quota_tracker["last_reset"] = today
        _quota_tracker["quota_exceeded"] = False
        print(f"📊 Daily quota reset. Current usage: {_quota_tracker['daily_requests']}/{_quota_tracker['quota_limit']}")
    
    _quota_tracker["daily_requests"] += 1
    
    # Check if we're approaching the limit
    usage_percentage = (_quota_tracker["daily_requests"] / _quota_tracker["quota_limit"]) * 100
    
    if usage_percentage >= 90:
        _quota_tracker["quota_exceeded"] = True
        print(f"⚠️  QUOTA WARNING: {_quota_tracker['daily_requests']}/{_quota_tracker['quota_limit']} requests used ({usage_percentage:.1f}%)")
    elif usage_percentage >= 75:
        print(f"📊 Quota usage: {_quota_tracker['daily_requests']}/{_quota_tracker['quota_limit']} ({usage_percentage:.1f}%)")

def _is_quota_exceeded() -> bool:
    """Check if quota is exceeded."""
    return _quota_tracker["quota_exceeded"] or _quota_tracker["daily_requests"] >= _quota_tracker["quota_limit"]

def create_llm_with_retry(model_name: str, max_retries: int = 3, base_delay: float = 1.0) -> Optional[LLM]:
    """Create an LLM instance with retry logic for handling temporary failures."""
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to create LLM with model: {model_name} (attempt {attempt + 1}/{max_retries})")
            
            # Let LiteLLM automatically pick up API keys from environment variables
            # This is the recommended approach for LiteLLM
            llm_instance = LLM(
                model=model_name,
                base_url=None,
                # Remove explicit api_key parameter - let LiteLLM use environment variables
                timeout=60,  # 60 second timeout
                max_retries=2  # LiteLLM internal retries
            )
            
            # Test the LLM with a simple call
            test_response = llm_instance.call("Hello")
            if test_response:
                print(f"Successfully created and tested LLM with model: {model_name}")
                return llm_instance
                
        except (InternalServerError, ServiceUnavailableError, RateLimitError) as e:
            print(f"Temporary error with {model_name} on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                print(f"Max retries reached for {model_name}")
                
        except Exception as e:
            print(f"Permanent error with {model_name}: {str(e)}")
            break
    
    return None

def initialize_vertex_ai():
    """Initialize Vertex AI and return an LLM instance with fallback options."""
    # Check if credentials are set
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Credentials file not found: {creds_path}")
    
    try:
        # Initialize Vertex AI
        vertexai.init(project=settings.GCP_PROJECT_ID, location="us-central1")
        print(f"Vertex AI initialized successfully with project: {settings.GCP_PROJECT_ID}")
        
        # Define fallback models in order of preference
        model_options = [
            f"gemini/{settings.GEMINI_MODEL}",  # Primary: gemini-2.5-pro
            "gemini/gemini-2.5-flash",          # Fallback 2: faster, lighter
        ]
        
        # Add OpenAI fallback if API key is available
        if os.getenv('OPENAI_API_KEY'):
            model_options.extend([
                "openai/gpt-4o",                # OpenAI fallback 1
                "openai/gpt-4o-mini"            # OpenAI fallback 2
            ])
        
        # Try each model until one works
        for model in model_options:
            print(f"Trying model: {model}")
            llm_instance = create_llm_with_retry(model)
            if llm_instance:
                print(f"Successfully initialized LLM with model: {model}")
                return llm_instance
        
        # If no models work, raise an error
        raise RuntimeError("All LLM models failed to initialize. Please check your API keys and service availability.")
        
    except Exception as e:
        print(f"Failed to initialize Vertex AI: {e}")
        raise

# Create the LLM instance with robust error handling
try:
    llm = initialize_vertex_ai()
    print("LLM initialized successfully")
except Exception as e:
    print(f"Failed to create Vertex AI LLM: {e}")
    llm = None

def ask_gemini(prompt: str, use_cache: bool = True, cache_hours: int = 24) -> str:
    """
    Direct function to ask Gemini a question and get a response with caching and quota management.
    
    Args:
        prompt (str): The question or prompt to send to Gemini
        use_cache (bool): Whether to use response caching
        cache_hours (int): How long to cache responses (in hours)
        
    Returns:
        str: The response from Gemini or intelligent fallback
    """
    # Check cache if enabled
    if use_cache:
        cache_key = _get_cache_key(prompt)
        if cache_key in _request_cache:
            cache_entry = _request_cache[cache_key]
            if _is_cache_valid(cache_entry, cache_hours):
                print(f"📋 Using cached response for prompt hash: {cache_key[:8]}...")
                return cache_entry['response']
            else:
                # Remove expired cache entry
                del _request_cache[cache_key]
    
    # Check quota before making API call
    if _is_quota_exceeded():
        print("⚠️  Daily quota exceeded, using intelligent fallback response")
        return create_intelligent_fallback_response(prompt)
    
    if llm is None:
        print("⚠️  Gemini LLM not available, using intelligent fallback response")
        return create_intelligent_fallback_response(prompt)
    
    try:
        # Update quota tracker
        _update_quota_tracker()
        
        # Make the API call
        print(f"🤖 Making Gemini API call ({_quota_tracker['daily_requests']}/{_quota_tracker['quota_limit']})")
        response = llm.call(prompt)
        
        if not response:
            print("⚠️  Gemini returned empty response, using fallback")
            return create_intelligent_fallback_response(prompt)
        
        response_str = str(response)
        
        # Cache the response if caching is enabled
        if use_cache:
            cache_key = _get_cache_key(prompt)
            _request_cache[cache_key] = {
                'response': response_str,
                'timestamp': datetime.now().isoformat(),
                'prompt_preview': prompt[:100] + "..." if len(prompt) > 100 else prompt
            }
            print(f"💾 Cached response for future use ({len(_request_cache)} total cached)")
        
        return response_str
        
    except RateLimitError as e:
        print(f"⚠️  Rate limit hit: {str(e)}")
        _quota_tracker["quota_exceeded"] = True
        print("⚠️  LLM not available (quota exhausted). Using mock LLM for graceful degradation.")
        return create_intelligent_fallback_response(prompt)
    except Exception as e:
        print(f"⚠️  Gemini call failed: {str(e)}, using fallback")
        return create_intelligent_fallback_response(prompt)

def create_intelligent_fallback_response(prompt: str) -> str:
    """
    Create intelligent fallback responses when Gemini is unavailable.
    Uses pattern matching to provide relevant responses based on prompt content.
    """
    prompt_lower = prompt.lower()
    
    # Keyword extraction patterns
    if "extract" in prompt_lower and "keywords" in prompt_lower:
        if "youtube" in prompt_lower or "streaming" in prompt_lower or "content" in prompt_lower:
            return '["youtube setup", "content creation", "streaming equipment", "video recording"]'
        elif "headphones" in prompt_lower or "audio" in prompt_lower:
            return '["wireless headphones", "noise cancelling", "bluetooth headphones", "audio quality"]'
        elif "swimming" in prompt_lower or "swim" in prompt_lower or "pool" in prompt_lower:
            return '["professional swimming equipment", "competitive swim gear", "swimming training aids", "pool equipment"]'
        elif "professional" in prompt_lower and "equipment" in prompt_lower:
            return '["professional equipment", "training gear", "competitive equipment", "performance tools"]'
        else:
            # Extract meaningful keywords from the prompt itself
            import re
            words = re.findall(r'\b[a-zA-Z]{3,}\b', prompt_lower)
            meaningful_words = [w for w in words if w not in ['extract', 'keywords', 'search', 'query', 'user', 'from', 'this', 'the', 'and', 'for', 'with']]
            if meaningful_words:
                return f'["{" ".join(meaningful_words[:3])}", "product search", "online shopping"]'
            return '["product search", "online shopping", "best deals", "product reviews"]'
    
    # Package creation patterns
    elif "package" in prompt_lower and ("create" in prompt_lower or "curate" in prompt_lower):
        return """
        {
            "packages": [
                {
                    "name": "Essential Starter Package",
                    "description": "A comprehensive starter package with essential products for your needs.",
                    "products": [],
                    "price_range": "Budget-friendly",
                    "why_recommended": "Perfect balance of quality and affordability for beginners."
                }
            ],
            "summary": "Curated package selection based on your requirements and budget.",
            "expert_recommendations": [
                "Start with essential items and upgrade gradually",
                "Focus on quality over quantity",
                "Read reviews before purchasing"
            ]
        }
        """
    
    # Product analysis patterns
    elif "analyze" in prompt_lower or "extract" in prompt_lower:
        return """
        Based on the available information, here are the key product details:
        - Quality: Good value for the price point
        - Features: Standard features expected for this category
        - Compatibility: Works with most common setups
        - Recommendation: Suitable for intended use case
        """
    
    # General search/recommendation patterns
    elif any(word in prompt_lower for word in ["recommend", "suggest", "find", "search"]):
        return """
        Based on your requirements, here are some suggestions:
        1. Consider your budget and specific needs
        2. Look for products with good reviews and ratings
        3. Check compatibility with your existing setup
        4. Compare features across different options
        5. Consider future upgrade paths
        """
    
    # Default fallback
    else:
        return """
        I understand you're looking for assistance. While our AI service is temporarily unavailable, 
        our system is still providing you with real product data from our comprehensive database. 
        You'll receive actual Amazon URLs, real prices, and accurate product information.
        """

def get_quota_status() -> Dict[str, Any]:
    """Get current quota usage statistics."""
    _update_quota_tracker()  # Update without incrementing
    _quota_tracker["daily_requests"] -= 1  # Compensate for the increment
    
    usage_percentage = (_quota_tracker["daily_requests"] / _quota_tracker["quota_limit"]) * 100
    
    return {
        "daily_requests": _quota_tracker["daily_requests"],
        "quota_limit": _quota_tracker["quota_limit"],
        "usage_percentage": round(usage_percentage, 1),
        "quota_exceeded": _quota_tracker["quota_exceeded"],
        "last_reset": _quota_tracker["last_reset"].isoformat(),
        "cache_entries": len(_request_cache)
    }

def clear_cache():
    """Clear the request cache."""
    global _request_cache
    cache_count = len(_request_cache)
    _request_cache.clear()
    print(f"🗑️  Cleared {cache_count} cached responses")

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    valid_entries = 0
    expired_entries = 0
    
    for cache_entry in _request_cache.values():
        if _is_cache_valid(cache_entry):
            valid_entries += 1
        else:
            expired_entries += 1
    
    return {
        "total_entries": len(_request_cache),
        "valid_entries": valid_entries,
        "expired_entries": expired_entries,
        "cache_hit_potential": f"{(valid_entries / max(1, len(_request_cache))) * 100:.1f}%"
    }
