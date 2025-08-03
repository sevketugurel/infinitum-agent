# Vertex AI Dummy Data

This directory contains comprehensive dummy data for testing Vertex AI functionality without requiring actual GCP credentials or API calls.

## Overview

The dummy data includes:
- **Mock Gemini Responses**: Realistic responses for different types of prompts
- **Test Prompts**: Categorized prompts for various testing scenarios
- **Cache Data**: Mock cache entries for testing caching functionality
- **Quota Data**: Different quota scenarios for testing quota management
- **Error Scenarios**: Various error conditions and responses
- **Configuration Data**: Different credential and configuration scenarios
- **API Response Structures**: Mock API response formats

## Files

- `vertex_ai_dummy_data.py` - Main dummy data module
- `__init__.py` - Package initialization
- `README.md` - This documentation
- `demo_vertex_ai_dummy_data.py` - Demonstration script

## Quick Start

### Basic Usage

```python
from tests.dummy_data.vertex_ai_dummy_data import (
    MOCK_GEMINI_RESPONSES,
    TEST_PROMPTS,
    get_mock_response_for_prompt
)

# Get a mock response for a specific prompt
response = get_mock_response_for_prompt("Extract keywords from this product")
print(response)

# Use predefined test prompts
product_prompts = TEST_PROMPTS["product_related"]
for prompt in product_prompts:
    response = get_mock_response_for_prompt(prompt)
    print(f"Prompt: {prompt}")
    print(f"Response: {response[:100]}...")
```

### Running the Demo

```bash
cd backend/tests
python demo_vertex_ai_dummy_data.py
```

### Using in Tests

```python
import pytest
from unittest.mock import patch
from tests.dummy_data.vertex_ai_dummy_data import MOCK_GEMINI_RESPONSES

def test_ask_gemini_with_dummy_data():
    with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
        mock_llm.call.return_value = MOCK_GEMINI_RESPONSES["product_analysis"]
        
        result = ask_gemini("Analyze this product")
        assert result == MOCK_GEMINI_RESPONSES["product_analysis"]
```

## Data Categories

### Mock Gemini Responses

- `simple_math` - Basic mathematical responses
- `product_analysis` - Product analysis and recommendations
- `keyword_extraction` - JSON-formatted keyword lists
- `package_creation` - Product package recommendations
- `product_search` - Product search results
- `technical_analysis` - Technical product analysis
- `error_response` - Error messages
- `empty_response` - Empty responses
- `long_response` - Very long detailed responses

### Test Prompts

- `simple_queries` - Basic questions and greetings
- `product_related` - Product analysis, search, and recommendations
- `technical_queries` - Technical questions about various topics
- `creative_requests` - Creative writing and design requests
- `edge_cases` - Empty prompts, very long prompts, special characters

### Cache Data

- `valid_cache` - Valid cache entries
- `expired_cache` - Expired cache entries
- `multiple_cache_entries` - Multiple cache entries with different states

### Quota Data

- `normal_usage` - Normal quota usage
- `high_usage` - High but not exceeded quota
- `quota_exceeded` - Quota exceeded scenario
- `new_day_reset` - Quota reset for new day

### Error Scenarios

- `rate_limit_error` - Rate limiting errors
- `connection_error` - Connection failures
- `authentication_error` - Authentication issues
- `service_unavailable` - Service unavailability
- `internal_server_error` - Server errors

## Utility Functions

### `get_mock_response_for_prompt(prompt: str) -> str`

Intelligently selects appropriate mock responses based on prompt content:

```python
# Automatically selects keyword extraction response
response = get_mock_response_for_prompt("Extract keywords from this product")

# Automatically selects package creation response
response = get_mock_response_for_prompt("Create a package for professional equipment")
```

### `create_mock_cache_entry(prompt: str, response: str, hours_old: int = 0) -> Dict`

Creates mock cache entries with specified age:

```python
cache_entry = create_mock_cache_entry(
    prompt="Test prompt",
    response="Test response",
    hours_old=2
)
```

### `get_test_prompts_by_category(category: str) -> List[str]`

Gets test prompts for a specific category:

```python
product_prompts = get_test_prompts_by_category("product_related")
technical_prompts = get_test_prompts_by_category("technical_queries")
```

### `get_mock_quota_data(scenario: str) -> Dict`

Gets mock quota data for a specific scenario:

```python
quota_data = get_mock_quota_data("quota_exceeded")
```

### `get_test_scenario(scenario_name: str) -> Dict`

Gets a specific test scenario configuration:

```python
scenario = get_test_scenario("normal_operation")
```

## Testing Scenarios

The dummy data supports comprehensive testing scenarios:

1. **Normal Operation** - Valid credentials, normal quota usage
2. **Quota Exceeded** - Daily quota limit reached
3. **Rate Limited** - Rate limiting errors
4. **Invalid Credentials** - Missing or invalid credentials
5. **Service Unavailable** - Service downtime scenarios

## Integration with Existing Tests

The dummy data can be easily integrated with existing test files:

```python
# In your test file
from tests.dummy_data.vertex_ai_dummy_data import (
    MOCK_GEMINI_RESPONSES,
    TEST_PROMPTS,
    get_mock_response_for_prompt
)

class TestVertexAI:
    def test_with_dummy_data(self):
        # Use dummy data instead of real API calls
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for prompt in TEST_PROMPTS["simple_queries"]:
                expected_response = get_mock_response_for_prompt(prompt)
                mock_llm.call.return_value = expected_response
                
                result = ask_gemini(prompt)
                assert result == expected_response
```

## Benefits

1. **No API Costs** - Test without making actual API calls
2. **Fast Execution** - No network latency
3. **Predictable Results** - Consistent test outcomes
4. **Comprehensive Coverage** - Test various scenarios and edge cases
5. **CI/CD Friendly** - Works in automated testing environments
6. **Development Friendly** - Develop without credentials

## Contributing

When adding new dummy data:

1. Follow the existing naming conventions
2. Add appropriate documentation
3. Include utility functions if needed
4. Update the `__all__` list in `__init__.py`
5. Add tests for new functionality

## Examples

See `test_vertex_ai_with_dummy_data.py` for comprehensive examples of how to use the dummy data in tests. 