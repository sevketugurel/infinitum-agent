from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # GCP Configuration
    GCP_PROJECT_ID: str = "infinitum-agent"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # Vertex AI Configuration
    GEMINI_MODEL: str = "gemini-2.5-pro"
    
    # Quota Management
    GEMINI_DAILY_QUOTA: int = 200  # Conservative limit for free tier
    USE_PAID_TIER: bool = False  # Set to True if using paid tier
    ENABLE_REQUEST_CACHING: bool = True
    CACHE_DURATION_HOURS: int = 24
    
    # SerpAPI Configuration
    SERPAPI_API_KEY: Optional[str] = None
    
    # Free Search Alternatives Configuration
    BING_API_KEY: Optional[str] = None  # Azure Bing Web Search API key
    GOOGLE_CSE_ID: Optional[str] = None  # Google Custom Search Engine ID
    
    # Google AI Studio Configuration
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # OpenAI Configuration (fallback)
    OPENAI_API_KEY: Optional[str] = None
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = "infinitum-agent"
    
    # Environment
    ENVIRONMENT: str = "development"
    PORT: int = 8080
    
    # Enhanced Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: Optional[str] = None
    ENABLE_STRUCTURED_LOGGING: bool = True
    ENABLE_RICH_LOGGING: bool = True  # For development
    LOG_SAMPLING_RATE: float = 1.0  # Sample rate for performance
    
    # Monitoring and Observability
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    ENABLE_TRACING: bool = True
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    
    # Performance and Debug Settings
    ENABLE_PERFORMANCE_LOGGING: bool = True
    LOG_SLOW_OPERATIONS: bool = True
    SLOW_OPERATION_THRESHOLD: float = 1.0  # seconds
    ENABLE_DEBUG_LOGGING: bool = False
    
    class Config:
        # Try to find .env file in the new config directory
        # Correctly locate the .env file in the project's root config directory
        # Assumes the script is run from the 'backend' directory context
        # Path from settings.py -> infinitum -> src -> backend -> config
        env_file_path = Path(__file__).parent.parent.parent.parent / "config" / ".env"
        env_file = env_file_path if env_file_path.exists() else None
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
        print(f"Bing API Key: {'***' + str(self.BING_API_KEY)[-4:] if self.BING_API_KEY else 'Not set'}")
        print(f"Google CSE ID: {'***' + str(self.GOOGLE_CSE_ID)[-4:] if self.GOOGLE_CSE_ID else 'Not set'}")
        
        # Validate critical settings
        if not self.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY is not set! This will cause authentication errors.")
        if not self.SERPAPI_API_KEY and not self.BING_API_KEY and not self.GOOGLE_CSE_ID:
            print("WARNING: No search API keys configured! Using free DuckDuckGo fallback.")

settings = Settings()
