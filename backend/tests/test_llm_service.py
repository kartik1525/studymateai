import pytest
from unittest.mock import patch, MagicMock

from app.services.llm_service import LLMService, LLMGenerationError
from app.core.config import settings
from google.genai.errors import APIError

class MockAPIError(Exception):
    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(self.message)

@pytest.fixture
def patch_llm_pool():
    original_pool = settings.model_pool
    # Patch the property via patching the method, or just replace the list.
    # Since model_pool is a property that reads from env, we can patch os.environ.
    with patch.dict("os.environ", {"GEMINI_MODEL_POOL": "model1,model2,model3"}):
        # We need to bypass the property if we just mock the setting, or just mock settings.model_pool
        with patch("app.core.config.Settings.model_pool", new_callable=pytest.MonkeyPatch):
            pass # wait, better to just mock `settings.model_pool` directly
            
@pytest.fixture
def mock_pool():
    with patch("app.services.llm_service.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "test_key"
        mock_settings.model_pool = ["model1", "model2", "model3"]
        yield mock_settings

@pytest.fixture
def mock_client():
    with patch("app.services.llm_service.genai.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        yield mock_instance

def test_primary_model_succeeds(mock_pool, mock_client):
    LLMService._client = None
    mock_client.models.generate_content.return_value.text = "Success"
    
    result = LLMService.generate_text("Prompt")
    
    assert result == "Success"
    mock_client.models.generate_content.assert_called_once()
    args, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["model"] == "model1"

def test_primary_returns_503_and_retries(mock_pool, mock_client):
    LLMService._client = None
    
    mock_response = MagicMock()
    mock_response.text = "Success after retry"
    
    mock_client.models.generate_content.side_effect = [
        Exception("503 Service Unavailable"),
        mock_response
    ]
    
    with patch("time.sleep") as mock_sleep:
        result = LLMService.generate_text("Prompt")
        
    assert result == "Success after retry"
    assert mock_client.models.generate_content.call_count == 2
    # Both calls to model1
    assert mock_client.models.generate_content.call_args_list[0][1]["model"] == "model1"
    assert mock_client.models.generate_content.call_args_list[1][1]["model"] == "model1"
    mock_sleep.assert_called_once_with(1)

def test_primary_fails_fallback_to_second(mock_pool, mock_client):
    LLMService._client = None
    
    mock_response = MagicMock()
    mock_response.text = "Success from model2"
    
    # model1 fails twice (max_retries=2), then model2 succeeds
    mock_client.models.generate_content.side_effect = [
        Exception("503 Service Unavailable"),
        Exception("503 Service Unavailable"),
        mock_response
    ]
    
    with patch("time.sleep") as mock_sleep:
        result = LLMService.generate_text("Prompt", max_retries=2)
        
    assert result == "Success from model2"
    assert mock_client.models.generate_content.call_count == 3
    assert mock_client.models.generate_content.call_args_list[0][1]["model"] == "model1"
    assert mock_client.models.generate_content.call_args_list[1][1]["model"] == "model1"
    assert mock_client.models.generate_content.call_args_list[2][1]["model"] == "model2"
    assert mock_sleep.call_count == 1  # model1 attempt 1 sleeps, attempt 2 fails and falls back (no sleep)

def test_first_two_models_fail_third_succeeds(mock_pool, mock_client):
    LLMService._client = None
    
    mock_response = MagicMock()
    mock_response.text = "Success from model3"
    
    mock_client.models.generate_content.side_effect = [
        Exception("503 Error"),
        Exception("503 Error"),
        Exception("429 Quota"),
        Exception("429 Quota"),
        mock_response
    ]
    
    with patch("time.sleep"):
        result = LLMService.generate_text("Prompt", max_retries=2)
        
    assert result == "Success from model3"
    assert mock_client.models.generate_content.call_count == 5
    assert mock_client.models.generate_content.call_args_list[0][1]["model"] == "model1"
    assert mock_client.models.generate_content.call_args_list[2][1]["model"] == "model2"
    assert mock_client.models.generate_content.call_args_list[4][1]["model"] == "model3"

def test_all_models_fail(mock_pool, mock_client):
    LLMService._client = None
    
    mock_client.models.generate_content.side_effect = [
        Exception("503 Error") for _ in range(6)
    ]
    
    with patch("time.sleep"):
        with pytest.raises(LLMGenerationError, match="The AI tutor is temporarily busy"):
            LLMService.generate_text("Prompt", max_retries=2)
            
    assert mock_client.models.generate_content.call_count == 6

def test_primary_returns_401_fails_immediately(mock_pool, mock_client):
    LLMService._client = None
    
    mock_client.models.generate_content.side_effect = [
        Exception("401 Unauthorized")
    ]
    
    with patch("time.sleep") as mock_sleep:
        with pytest.raises(LLMGenerationError, match="Non-transient generation error"):
            LLMService.generate_text("Prompt", max_retries=2)
            
    # Should only call once and fail immediately, no sleep
    assert mock_client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()

def test_primary_returns_400_fails_immediately(mock_pool, mock_client):
    LLMService._client = None
    
    mock_client.models.generate_content.side_effect = [
        Exception("400 Bad Request")
    ]
    
    with patch("time.sleep") as mock_sleep:
        with pytest.raises(LLMGenerationError, match="Non-transient generation error"):
            LLMService.generate_text("Prompt", max_retries=2)
            
    assert mock_client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()

def test_prompt_consistency_across_fallbacks(mock_pool, mock_client):
    LLMService._client = None
    
    mock_response = MagicMock()
    mock_response.text = "Success"
    
    mock_client.models.generate_content.side_effect = [
        Exception("503 Error"),
        Exception("503 Error"),
        mock_response
    ]
    
    with patch("time.sleep"):
        LLMService.generate_text("Consistent Prompt", max_retries=2)
        
    for call in mock_client.models.generate_content.call_args_list:
        assert call[1]["contents"] == "Consistent Prompt"
