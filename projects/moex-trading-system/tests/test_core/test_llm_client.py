"""Tests for LLM client (Xiaomi MiMo via OpenAI SDK)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.llm_client import LLMClient, reset_llm_client


class TestLLMClientNoKey:
    """Tests without API key — graceful degradation."""

    def test_creation_without_key(self):
        client = LLMClient(api_key="")
        assert not client.is_available

    def test_chat_without_key_returns_empty(self):
        client = LLMClient(api_key="")
        assert client.chat("Hello") == ""

    def test_chat_json_without_key_returns_empty_dict(self):
        client = LLMClient(api_key="")
        assert client.chat_json("Return JSON") == {}

    def test_analyze_news_without_key(self):
        client = LLMClient(api_key="")
        result = client.analyze_news("CBR raised rate")
        assert result["sentiment"] == 0.0
        assert result["confidence"] == 0.0
        assert result["impact"] == "unknown"

    def test_is_available_false(self):
        client = LLMClient(api_key="")
        assert client.is_available is False


class TestLLMClientWithMock:
    """Tests with mocked OpenAI client."""

    def _make_client(self):
        """Create client with mock."""
        client = LLMClient.__new__(LLMClient)
        client._api_key = "test-key"
        client._model = "mimo-v2-pro"
        client._fallback_models = ["mimo-v2-flash"]
        client._temperature = 0.3
        client._max_tokens = 2000
        client._timeout = 30
        client._base_url = "https://api.xiaomimimo.com/v1"

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello!"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 10
        mock_openai.chat.completions.create.return_value = mock_response

        client._client = mock_openai
        return client, mock_openai

    def test_chat_calls_api(self):
        client, mock = self._make_client()
        result = client.chat("Say hello")
        assert result == "Hello!"
        mock.chat.completions.create.assert_called_once()

    def test_chat_passes_system_message(self):
        client, mock = self._make_client()
        client.chat("Hello", system="Be helpful")
        call_args = mock.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"

    def test_fallback_on_error(self):
        client, mock = self._make_client()
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback!"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 5

        mock.chat.completions.create.side_effect = [
            Exception("Model error"),
            mock_response,
        ]
        result = client.chat("Hello")
        assert result == "Fallback!"
        assert mock.chat.completions.create.call_count == 2

    def test_json_parsing(self):
        client, mock = self._make_client()
        mock.chat.completions.create.return_value.choices[0].message.content = '{"sentiment": -0.5}'
        result = client.chat_json("Analyze")
        assert result == {"sentiment": -0.5}

    def test_json_parsing_with_backticks(self):
        client, mock = self._make_client()
        mock.chat.completions.create.return_value.choices[0].message.content = '```json\n{"key": "val"}\n```'
        result = client.chat_json("Analyze")
        assert result == {"key": "val"}

    def test_json_parsing_invalid(self):
        client, mock = self._make_client()
        mock.chat.completions.create.return_value.choices[0].message.content = "Not JSON at all"
        result = client.chat_json("Analyze")
        assert result == {}

    def test_analyze_news_returns_dict(self):
        client, mock = self._make_client()
        mock.chat.completions.create.return_value.choices[0].message.content = (
            '{"sentiment": -0.8, "affected_tickers": ["SBER"], '
            '"confidence": 0.9, "impact": "high", "summary": "test"}'
        )
        result = client.analyze_news("CBR raised rate to 21%")
        assert result["sentiment"] == -0.8
        assert "SBER" in result["affected_tickers"]


class TestSingleton:
    def test_reset_clears_instance(self):
        reset_llm_client()
        # After reset, get_llm_client creates fresh instance
        from src.core.llm_client import _instance
        assert _instance is None
