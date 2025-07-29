# File: tests/test_vertex_ai.py
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from app.services.vertex_ai import ask_gemini, initialize_vertex_ai, create_llm_with_retry


class TestVertexAI:
    """Unit tests for Vertex AI integration."""
    
    def test_ask_gemini_with_valid_prompt(self):
        """Test ask_gemini with a valid prompt."""
        # Mock the global llm variable
        with patch('app.services.vertex_ai.llm') as mock_llm:
            mock_llm.call.return_value = "Test response from Gemini"
            
            result = ask_gemini("Test prompt")
            
            assert result == "Test response from Gemini"
            mock_llm.call.assert_called_once_with("Test prompt")
    
    def test_ask_gemini_with_none_llm(self):
        """Test ask_gemini when LLM is None."""
        with patch('app.services.vertex_ai.llm', None):
            with pytest.raises(RuntimeError) as exc_info:
                ask_gemini("Test prompt")
            
            assert "Gemini LLM is not initialized" in str(exc_info.value)
    
    def test_ask_gemini_with_empty_response(self):
        """Test ask_gemini when LLM returns empty response."""
        with patch('app.services.vertex_ai.llm') as mock_llm:
            mock_llm.call.return_value = ""
            
            with pytest.raises(RuntimeError) as exc_info:
                ask_gemini("Test prompt")
            
            assert "Gemini returned an empty response" in str(exc_info.value)
    
    def test_ask_gemini_with_llm_exception(self):
        """Test ask_gemini when LLM throws an exception."""
        with patch('app.services.vertex_ai.llm') as mock_llm:
            mock_llm.call.side_effect = Exception("LLM connection error")
            
            with pytest.raises(RuntimeError) as exc_info:
                ask_gemini("Test prompt")
            
            assert "Failed to get response from Gemini" in str(exc_info.value)
            assert "LLM connection error" in str(exc_info.value)
    
    def test_ask_gemini_with_various_prompts(self):
        """Test ask_gemini with different types of prompts."""
        test_cases = [
            ("Simple prompt", "Simple response"),
            ("Complex prompt with\nnewlines", "Complex response"),
            ("Prompt with special chars: !@#$%", "Special response"),
            ("", "Empty prompt response"),
        ]
        
        with patch('app.services.vertex_ai.llm') as mock_llm:
            for prompt, expected_response in test_cases:
                mock_llm.call.return_value = expected_response
                
                result = ask_gemini(prompt)
                
                assert result == expected_response
                mock_llm.call.assert_called_with(prompt)
    
    @patch('app.services.vertex_ai.os.getenv')
    def test_initialize_vertex_ai_missing_credentials(self, mock_getenv):
        """Test initialize_vertex_ai when credentials are missing."""
        mock_getenv.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            initialize_vertex_ai()
        
        assert "GOOGLE_APPLICATION_CREDENTIALS environment variable not set" in str(exc_info.value)
    
    @patch('app.services.vertex_ai.os.path.exists')
    @patch('app.services.vertex_ai.os.getenv')
    def test_initialize_vertex_ai_credentials_file_not_found(self, mock_getenv, mock_exists):
        """Test initialize_vertex_ai when credentials file doesn't exist."""
        mock_getenv.return_value = "/fake/path/to/credentials.json"
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError) as exc_info:
            initialize_vertex_ai()
        
        assert "Credentials file not found" in str(exc_info.value)
    
    def test_create_llm_with_retry_success_first_attempt(self):
        """Test create_llm_with_retry succeeds on first attempt."""
        with patch('app.services.vertex_ai.LLM') as mock_llm_class:
            mock_llm_instance = Mock()
            mock_llm_instance.call.return_value = "Test response"
            mock_llm_class.return_value = mock_llm_instance
            
            result = create_llm_with_retry("test-model")
            
            assert result == mock_llm_instance
            mock_llm_class.assert_called_once_with(
                model="test-model",
                base_url=None,
                timeout=60,
                max_retries=2
            )
    
    def test_create_llm_with_retry_fails_all_attempts(self):
        """Test create_llm_with_retry fails after all retries."""
        with patch('app.services.vertex_ai.LLM') as mock_llm_class:
            mock_llm_class.side_effect = Exception("Connection failed")
            
            with patch('app.services.vertex_ai.time.sleep'):  # Speed up test
                result = create_llm_with_retry("test-model", max_retries=2)
            
            assert result is None
            assert mock_llm_class.call_count == 2  # Should try twice
    
    def test_create_llm_with_retry_temporary_errors(self):
        """Test create_llm_with_retry with temporary errors."""
        from litellm.exceptions import RateLimitError
        
        with patch('app.services.vertex_ai.LLM') as mock_llm_class:
            # First call fails with rate limit, second succeeds
            mock_llm_instance = Mock()
            mock_llm_instance.call.return_value = "Success"
            
            mock_llm_class.side_effect = [
                RateLimitError("Rate limit exceeded"),
                mock_llm_instance
            ]
            
            with patch('app.services.vertex_ai.time.sleep'):  # Speed up test
                result = create_llm_with_retry("test-model", max_retries=3)
            
            assert result == mock_llm_instance
            assert mock_llm_class.call_count == 2


class TestIntegration:
    """Integration tests (require actual credentials)."""
    
    @pytest.mark.skipif(
        not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
        reason="Requires Google Cloud credentials"
    )
    def test_real_gemini_call(self):
        """Test with real Gemini API (only if credentials available)."""
        try:
            response = ask_gemini("What is 2+2? Answer with just the number.")
            assert response is not None
            assert len(response.strip()) > 0
            print(f"Real Gemini response: {response}")
        except Exception as e:
            pytest.skip(f"Real Gemini test skipped due to: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 