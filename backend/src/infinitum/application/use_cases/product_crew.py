# File: src/infinitum/application/use_cases/product_crew.py
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel
from typing import Optional
from ...infrastructure.external.ai.vertex_ai_client import llm # The LLM brain
from .tools import SearchTool, ScrapeWebsiteTool # The tools
from crewai.llm import LLM
from ...config.settings import settings
import os

# Define the output model
class ProductInfo(BaseModel):
    title: str
    price: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

# Instantiate the tools
search_tool = SearchTool()
scrape_tool = ScrapeWebsiteTool()

# Configure LLM with graceful fallback
if llm is None:
    print("⚠️  LLM not available (likely quota exhausted). Using mock LLM for graceful degradation.")
    # Create a mock LLM that can handle basic operations
    class MockLLM:
        def call(self, prompt):
            return "Mock response due to LLM unavailability"
        
        def __str__(self):
            return "MockLLM (Fallback)"
    
    crew_llm = MockLLM()
else:
    print("✅ Using real LLM for CrewAI agents")
    crew_llm = llm

# Define Agent 1: The Web Researcher
researcher = Agent(
    role='Expert Web Researcher',
    goal='Find the most relevant and high-traffic e-commerce URL for a given product query.',
    backstory='You are an expert at crafting Google search queries to pinpoint exact product pages on major retail sites like Amazon, eBay, or official brand stores.',
    tools=[search_tool],
    llm=crew_llm,
    verbose=False,  # Reduced verbosity
    max_retry_limit=2,  # Limit retries to prevent hanging
    execution_timeout=120  # 2 minute timeout per task
)

# Define Agent 2: The Product Analyst
analyst = Agent(
    role='Senior Product Analyst',
    goal='Extract detailed, structured information from the HTML of a product webpage.',
    backstory='You are a meticulous analyst who can read messy HTML and extract key product details like price, title, brand, and features. You focus on finding the most important information quickly.',
    tools=[scrape_tool],
    llm=crew_llm,
    verbose=False,  # Reduced verbosity
    max_retry_limit=2,  # Limit retries to prevent hanging
    execution_timeout=120  # 2 minute timeout per task
)

# Define the Tasks for the Crew
# Task 1: Find the product URL
research_task = Task(
    description='''Search for the product "{product_query}" and return the single best URL from a major e-commerce site.
    
    Instructions:
    - Focus on popular sites like Amazon, eBay, Best Buy, Target, or official brand stores
    - Return only ONE URL that is most likely to have detailed product information
    - Prefer URLs that clearly show the product name in the URL
    - If multiple good options exist, choose the one from the most reputable retailer''',
    expected_output='A single, valid URL pointing to the product page from a major retailer.',
    agent=researcher
)

# Task 2: Scrape the URL and extract data
analysis_task = Task(
    description='''Scrape the product page URL from the previous task and extract the key product information.
    
    The scraping tool will provide you with structured product information in this format:
    
    PRODUCT INFORMATION EXTRACTED:
    Title: [product title]
    Price: [price with currency]
    Brand: [brand name]
    Image URL: [main product image]
    Description: [product description]
    URL: [source url]
    
    Your job is to take this structured information and format it as a clean JSON object.
    
    Instructions:
    - Use the extracted information to create a proper JSON object
    - If any field shows "not found", set that field to null
    - Ensure price includes currency symbol (e.g., "$299.99")
    - Keep the description concise (under 200 characters)
    - Validate that the image URL is a complete, working URL
    - Return ONLY the JSON object, no other text
    
    Example output:
    {
      "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
      "price": "$348.00",
      "brand": "Sony", 
      "image_url": "https://example.com/image.jpg",
      "description": "Industry-leading noise canceling with Dual Noise Sensor technology. Up to 30 hour battery life."
    }''',
    expected_output='A clean JSON object containing the keys: title, price, brand, image_url, description.',
    agent=analyst,
    output_pydantic=ProductInfo # Instructs CrewAI to format the final output as structured data
)

# Assemble the Crew
product_crew = Crew(
    agents=[researcher, analyst],
    tasks=[research_task, analysis_task],
    process=Process.sequential,
    verbose=False,  # Reduced verbosity for cleaner logs
    max_execution_time=300,  # 5 minute timeout for entire crew execution
    memory=False  # Disable memory to reduce complexity and potential failure points
)
