# File: app/services/vertex_ai.py
from crewai.llm import LLM
import vertexai
from vertexai.generative_models import GenerativeModel
from ..core.config import settings
import json
import os
import time
import random
from typing import Optional
import litellm
from litellm.exceptions import InternalServerError, RateLimitError, ServiceUnavailableError

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
            f"gemini/{settings.GEMINI_MODEL}",  # Primary: gemini-2.0-flash-001
            "gemini/gemini-1.5-pro",            # Fallback 1: older but stable
            "gemini/gemini-1.5-flash",          # Fallback 2: faster, lighter
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

def ask_gemini(prompt: str) -> str:
    """
    Direct function to ask Gemini a question and get a response.
    
    Args:
        prompt (str): The question or prompt to send to Gemini
        
    Returns:
        str: The response from Gemini
        
    Raises:
        RuntimeError: If LLM is not initialized or fails to respond
    """
    if llm is None:
        raise RuntimeError("Gemini LLM is not initialized. Please check your Google Cloud credentials.")
    
    try:
        response = llm.call(prompt)
        if not response:
            raise RuntimeError("Gemini returned an empty response")
        return str(response)
    except Exception as e:
        raise RuntimeError(f"Failed to get response from Gemini: {str(e)}")
