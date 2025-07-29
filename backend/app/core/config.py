from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # GCP Configuration
    GCP_PROJECT_ID: str = "infinitum-agent"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # Vertex AI Configuration
    GEMINI_MODEL: str = "gemini-2.0-flash-001"
    
    # SerpAPI Configuration
    SERPAPI_API_KEY: Optional[str] = None
    
    # Google AI Studio Configuration
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # OpenAI Configuration (fallback)
    OPENAI_API_KEY: Optional[str] = None
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = "infinitum-agent"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        # Find .env file in the backend directory (parent of app)
        env_file = Path(__file__).parent.parent.parent / ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set the GOOGLE_APPLICATION_CREDENTIALS environment variable if it's not set
        if self.GOOGLE_APPLICATION_CREDENTIALS and not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.GOOGLE_APPLICATION_CREDENTIALS
        
        # Set GEMINI_API_KEY as environment variable for LiteLLM to access
        if self.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = self.GEMINI_API_KEY
        
        # Set GOOGLE_API_KEY as environment variable (alternative for LiteLLM)
        if self.GOOGLE_API_KEY:
            os.environ['GOOGLE_API_KEY'] = self.GOOGLE_API_KEY
        
        # Set OPENAI_API_KEY as environment variable if available
        if self.OPENAI_API_KEY:
            os.environ['OPENAI_API_KEY'] = self.OPENAI_API_KEY
        
        # Set SERPAPI_API_KEY as environment variable
        if self.SERPAPI_API_KEY:
            os.environ['SERPAPI_API_KEY'] = self.SERPAPI_API_KEY
        
        # Print current configuration for debugging
        print(f"GCP Project ID: {self.GCP_PROJECT_ID}")
        print(f"Environment: {self.ENVIRONMENT}")
        print(f"Google Credentials Path: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')}")
        print(f"Google API Key: {'***' + str(self.GOOGLE_API_KEY)[-4:] if self.GOOGLE_API_KEY else 'Not set'}")
        print(f"Gemini API Key: {'***' + str(self.GEMINI_API_KEY)[-4:] if self.GEMINI_API_KEY else 'Not set'}")
        print(f"Gemini Model: {self.GEMINI_MODEL}")
        print(f"SerpAPI Key: {'***' + str(self.SERPAPI_API_KEY)[-4:] if self.SERPAPI_API_KEY else 'Not set'}")
        
        # Validate critical settings
        if not self.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY is not set! This will cause authentication errors.")
        if not self.SERPAPI_API_KEY:
            print("WARNING: SERPAPI_API_KEY is not set! This may cause search functionality issues.")

settings = Settings()
