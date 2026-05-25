"""
Unit tests for scraut.platform.llm.client.

Covers: provider routing, base_url pass-through for Anthropic and OpenAI,
Google Gemini provider (token tracking, system prompt, missing metadata),
complete_json, complete_batch, and daily-limit enforcement.

All tests mock the SDK clients — no real API calls are ever made.
"""
import sys
from unittest.mock import MagicMock, patch, call

import pytest

import scraut.platform.llm.client as llm_client


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_daily_tokens():
    original = llm_client._daily_tokens_used
    llm_client._daily_tokens_used = 0
    yield
    llm_client._daily_tokens_used = original


def _cfg(provider="anthropic", model="test-model", base_url="",
         max_tokens=100, daily_limit=100_000, batch=False):
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "max_tokens": max_tokens,
        "cost_controls": {"max_daily_tokens": daily_limit,
                          "batch_where_possible": batch},
    }


def _anthropic_resp(text="ok", input_tokens=10, output_tokens=20):
    resp = MagicMock()
    resp.content[0].text = text
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    return resp


def _openai_resp(text="ok"):
    resp = MagicMock()
    resp.choices[0].message.content = text
    return resp


def _gemini_resp(text="ok", prompt_tokens=15, candidate_tokens=25):
    resp = MagicMock()
    resp.text = text
    resp.usage_metadata.prompt_token_count = prompt_tokens
    resp.usage_metadata.candidates_token_count = candidate_tokens
    return resp


def _mock_genai(text="ok", prompt_tokens=15, candidate_tokens=25):
    """Return a fully wired MagicMock for the google.generativeai module."""
    mock = MagicMock()
    mock.GenerativeModel.return_value.generate_content.return_value = (
        _gemini_resp(text, prompt_tokens, candidate_tokens)
    )
    return mock


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCompleteRouting:
    def test_routes_anthropic(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("anthropic")):
            with patch("scraut.platform.llm.client._call_anthropic", return_value="ans") as m:
                assert llm_client.complete("q") == "ans"
        m.assert_called_once_with("q", None, 100, model="test-model")

    def test_routes_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("openai")):
            with patch("scraut.platform.llm.client._call_openai", return_value="ans") as m:
                assert llm_client.complete("q") == "ans"
        m.assert_called_once_with("q", None, 100, model="test-model")

    def test_routes_gemini(self):
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("gemini")):
            with patch("scraut.platform.llm.client._call_gemini", return_value="ans") as m:
                assert llm_client.complete("q") == "ans"
        m.assert_called_once_with("q", None, 100, model="test-model")

    def test_routes_ollama(self):
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("ollama")):
            with patch("scraut.platform.llm.client._call_ollama", return_value="ans") as m:
                assert llm_client.complete("q") == "ans"
        m.assert_called_once_with("q", None, 100, model="test-model")

    def test_routes_github(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "gh-tok")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("github")):
            with patch("scraut.platform.llm.client._call_github", return_value="ans") as m:
                assert llm_client.complete("q") == "ans"
        m.assert_called_once_with("q", None, 100, model="test-model")

    def test_unknown_provider_returns_empty(self):
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("banana")):
            assert llm_client.complete("q") == ""

    def test_system_passed_through(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg()):
            with patch("scraut.platform.llm.client._call_anthropic", return_value="ok") as m:
                llm_client.complete("q", system="Be concise.")
        m.assert_called_once_with("q", "Be concise.", 100, model="test-model")

    def test_explicit_max_tokens_overrides_config(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg(max_tokens=100)):
            with patch("scraut.platform.llm.client._call_anthropic", return_value="ok") as m:
                llm_client.complete("q", max_tokens=500)
        m.assert_called_once_with("q", None, 500, model="test-model")

    def test_use_small_model_selects_small_model(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = _cfg("anthropic")
        cfg["small_model"] = "claude-haiku-small"
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("scraut.platform.llm.client._call_anthropic", return_value="ok") as m:
                llm_client.complete("q", use_small_model=True)
        m.assert_called_once_with("q", None, 100, model="claude-haiku-small")

    def test_use_small_model_falls_back_when_unset(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = _cfg("anthropic")
        cfg["small_model"] = ""
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("scraut.platform.llm.client._call_anthropic", return_value="ok") as m:
                llm_client.complete("q", use_small_model=True)
        m.assert_called_once_with("q", None, 100, model="test-model")

    def test_daily_limit_blocks_call(self):
        llm_client._daily_tokens_used = 51
        with patch("scraut.platform.llm.client.get_llm_config",
                   return_value=_cfg(daily_limit=50)):
            with patch("scraut.platform.llm.client._call_anthropic") as m:
                assert llm_client.complete("q") == ""
        m.assert_not_called()

    def test_exception_returns_empty(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg()):
            with patch("scraut.platform.llm.client._call_anthropic",
                       side_effect=RuntimeError("network error")):
                assert llm_client.complete("q") == ""


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCallAnthropic:
    def test_basic_call_returns_text(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_resp("hello", 5, 10)
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg()):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = llm_client._call_anthropic("prompt", None, 100)
        assert result == "hello"

    def test_tokens_tracked(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_resp(input_tokens=7, output_tokens=13)
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg()):
            with patch("anthropic.Anthropic", return_value=mock_client):
                llm_client._call_anthropic("prompt", None, 100)
        assert llm_client._daily_tokens_used == 20

    def test_system_prompt_included_when_given(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_resp()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg()):
            with patch("anthropic.Anthropic", return_value=mock_client):
                llm_client._call_anthropic("prompt", "You are helpful.", 100)
        kwargs = mock_client.messages.create.call_args[1]
        assert kwargs["system"] == "You are helpful."

    def test_no_system_prompt_omits_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_resp()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg()):
            with patch("anthropic.Anthropic", return_value=mock_client):
                llm_client._call_anthropic("prompt", None, 100)
        kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in kwargs

    def test_custom_base_url_forwarded(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_resp()
        cfg = _cfg("anthropic", base_url="https://my-proxy.example.com")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("anthropic.Anthropic", return_value=mock_client) as ctor:
                llm_client._call_anthropic("prompt", None, 100)
        ctor.assert_called_once_with(api_key="sk-test",
                                     base_url="https://my-proxy.example.com")

    def test_empty_base_url_not_forwarded(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_resp()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg(base_url="")):
            with patch("anthropic.Anthropic", return_value=mock_client) as ctor:
                llm_client._call_anthropic("prompt", None, 100)
        ctor.assert_called_once_with(api_key="sk-test")


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCallOpenAI:
    def test_basic_call_returns_text(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_resp("hi there")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("openai")):
            with patch("openai.OpenAI", return_value=mock_client):
                assert llm_client._call_openai("prompt", None, 100) == "hi there"

    def test_system_prepended_to_messages(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_resp()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("openai")):
            with patch("openai.OpenAI", return_value=mock_client):
                llm_client._call_openai("prompt", "system text", 100)
        msgs = mock_client.chat.completions.create.call_args[1]["messages"]
        assert msgs[0] == {"role": "system", "content": "system text"}
        assert msgs[1] == {"role": "user", "content": "prompt"}

    def test_custom_base_url_forwarded(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_resp()
        cfg = _cfg("openai", base_url="https://api.groq.com/openai/v1")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("openai.OpenAI", return_value=mock_client) as ctor:
                llm_client._call_openai("prompt", None, 100)
        ctor.assert_called_once_with(api_key="sk-test",
                                     base_url="https://api.groq.com/openai/v1")

    def test_empty_base_url_not_forwarded(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_resp()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("openai")):
            with patch("openai.OpenAI", return_value=mock_client) as ctor:
                llm_client._call_openai("prompt", None, 100)
        ctor.assert_called_once_with(api_key="sk-test")

    def test_missing_api_key_uses_placeholder(self, monkeypatch):
        """Unauthenticated local endpoints (LM Studio, Ollama-compat) need a non-empty key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_resp()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("openai")):
            with patch("openai.OpenAI", return_value=mock_client) as ctor:
                llm_client._call_openai("prompt", None, 100)
        ctor.assert_called_once_with(api_key="no-key")

    def test_local_endpoint_no_key(self, monkeypatch):
        """Custom base_url + no OPENAI_API_KEY = placeholder key forwarded."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_resp()
        cfg = _cfg("openai", base_url="http://localhost:1234/v1")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("openai.OpenAI", return_value=mock_client) as ctor:
                llm_client._call_openai("prompt", None, 100)
        ctor.assert_called_once_with(api_key="no-key",
                                     base_url="http://localhost:1234/v1")


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCallGemini:
    def test_basic_call_returns_text(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "gemini-key")
        mock_genai = _mock_genai("gemini response")
        with patch("scraut.platform.llm.client.get_llm_config",
                   return_value=_cfg("gemini", model="gemini-1.5-pro")):
            with patch.dict(sys.modules, {"google.generativeai": mock_genai}):
                result = llm_client._call_gemini("hello", None, 200)
        assert result == "gemini response"

    def test_api_key_configured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "my-gemini-key")
        mock_genai = _mock_genai()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("gemini")):
            with patch.dict(sys.modules, {"google.generativeai": mock_genai}):
                llm_client._call_gemini("prompt", None, 100)
        mock_genai.configure.assert_called_once_with(api_key="my-gemini-key")

    def test_token_tracking(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        mock_genai = _mock_genai(prompt_tokens=15, candidate_tokens=30)
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("gemini")):
            with patch.dict(sys.modules, {"google.generativeai": mock_genai}):
                llm_client._call_gemini("prompt", None, 100)
        assert llm_client._daily_tokens_used == 45

    def test_system_prompt_passed_as_system_instruction(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        mock_genai = _mock_genai()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("gemini")):
            with patch.dict(sys.modules, {"google.generativeai": mock_genai}):
                llm_client._call_gemini("prompt", "You are a bot.", 100)
        kwargs = mock_genai.GenerativeModel.call_args[1]
        assert kwargs["system_instruction"] == "You are a bot."

    def test_no_system_prompt_passes_none(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        mock_genai = _mock_genai()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("gemini")):
            with patch.dict(sys.modules, {"google.generativeai": mock_genai}):
                llm_client._call_gemini("prompt", None, 100)
        kwargs = mock_genai.GenerativeModel.call_args[1]
        assert kwargs["system_instruction"] is None

    def test_missing_usage_metadata_graceful(self, monkeypatch):
        """Gemini API may omit usage_metadata in some configurations."""
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        mock_genai = MagicMock()
        mock_response = MagicMock(spec=["text"])   # no usage_metadata attribute
        mock_response.text = "no-meta"
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("gemini")):
            with patch.dict(sys.modules, {"google.generativeai": mock_genai}):
                result = llm_client._call_gemini("prompt", None, 100)
        assert result == "no-meta"
        assert llm_client._daily_tokens_used == 0

    def test_generation_config_max_tokens(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        mock_genai = _mock_genai()
        with patch("scraut.platform.llm.client.get_llm_config", return_value=_cfg("gemini")):
            with patch.dict(sys.modules, {"google.generativeai": mock_genai}):
                llm_client._call_gemini("prompt", None, 512)
        mock_genai.types.GenerationConfig.assert_called_once_with(max_output_tokens=512)


# ---------------------------------------------------------------------------
# complete_json
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCompleteJson:
    def test_valid_json_parsed(self):
        with patch("scraut.platform.llm.client.complete", return_value='{"a": 1}'):
            assert llm_client.complete_json("q") == {"a": 1}

    def test_json_fences_stripped(self):
        with patch("scraut.platform.llm.client.complete",
                   return_value='```json\n{"a": 1}\n```'):
            assert llm_client.complete_json("q") == {"a": 1}

    def test_invalid_json_returns_empty_dict(self):
        with patch("scraut.platform.llm.client.complete", return_value="not json"):
            assert llm_client.complete_json("q") == {}

    def test_empty_response_returns_empty_dict(self):
        with patch("scraut.platform.llm.client.complete", return_value=""):
            assert llm_client.complete_json("q") == {}


# ---------------------------------------------------------------------------
# complete_batch
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCompleteBatch:
    def _cfg_batch(self, batch=True):
        c = _cfg()
        c["cost_controls"]["batch_where_possible"] = batch
        return c

    def test_empty_input_returns_empty(self):
        with patch("scraut.platform.llm.client.get_llm_config",
                   return_value=self._cfg_batch()):
            assert llm_client.complete_batch([]) == []

    def test_batching_disabled_calls_once_per_prompt(self):
        with patch("scraut.platform.llm.client.get_llm_config",
                   return_value=self._cfg_batch(batch=False)):
            with patch("scraut.platform.llm.client.complete", return_value="r") as m:
                result = llm_client.complete_batch(["a", "b", "c"])
        assert result == ["r", "r", "r"]
        assert m.call_count == 3

    def test_batching_enabled_single_call(self):
        with patch("scraut.platform.llm.client.get_llm_config",
                   return_value=self._cfg_batch(batch=True)):
            with patch("scraut.platform.llm.client.complete",
                       return_value='["r1", "r2"]') as m:
                result = llm_client.complete_batch(["a", "b"])
        assert result == ["r1", "r2"]
        assert m.call_count == 1

    def test_batch_parse_failure_falls_back_to_individual(self):
        call_n = [0]

        def _side(*_args, **_kwargs):
            call_n[0] += 1
            return "not json" if call_n[0] == 1 else "r"

        with patch("scraut.platform.llm.client.get_llm_config",
                   return_value=self._cfg_batch(batch=True)):
            with patch("scraut.platform.llm.client.complete", side_effect=_side):
                result = llm_client.complete_batch(["a", "b"])

        assert result == ["r", "r"]

# ---------------------------------------------------------------------------
# Fallback provider
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFallback:
    def _cfg_with_fallback(self, fb_provider="github", fb_model="gpt-4o-mini"):
        c = _cfg("anthropic")
        c["fallback"] = {"provider": fb_provider, "model": fb_model}
        return c

    def test_fallback_triggered_on_primary_failure(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = self._cfg_with_fallback("github", "gpt-4o-mini")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("scraut.platform.llm.client._call_anthropic",
                       side_effect=RuntimeError("no key")):
                with patch("scraut.platform.llm.client._call_github",
                           return_value="fallback answer") as fb:
                    result = llm_client.complete("q")
        assert result == "fallback answer"
        fb.assert_called_once()

    def test_fallback_not_triggered_on_success(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = self._cfg_with_fallback("github", "gpt-4o-mini")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("scraut.platform.llm.client._call_anthropic",
                       return_value="primary answer"):
                with patch("scraut.platform.llm.client._call_github") as fb:
                    result = llm_client.complete("q")
        assert result == "primary answer"
        fb.assert_not_called()

    def test_fallback_also_fails_returns_empty(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = self._cfg_with_fallback("ollama", "qwen2.5:0.5b")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("scraut.platform.llm.client._call_anthropic",
                       side_effect=RuntimeError("primary fail")):
                with patch("scraut.platform.llm.client._call_ollama",
                           side_effect=RuntimeError("ollama not running")):
                    result = llm_client.complete("q")
        assert result == ""

    def test_no_fallback_configured_returns_empty_on_failure(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = _cfg("anthropic")
        cfg.pop("fallback", None)
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("scraut.platform.llm.client._call_anthropic",
                       side_effect=RuntimeError("fail")):
                result = llm_client.complete("q")
        assert result == ""

    def test_fallback_uses_fallback_model(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = self._cfg_with_fallback("ollama", "qwen2.5:0.5b")
        with patch("scraut.platform.llm.client.get_llm_config", return_value=cfg):
            with patch("scraut.platform.llm.client._call_anthropic",
                       side_effect=RuntimeError("fail")):
                with patch("scraut.platform.llm.client._call_ollama",
                           return_value="ok") as m:
                    llm_client.complete("q")
        m.assert_called_once_with("q", None, 100, model="qwen2.5:0.5b")
