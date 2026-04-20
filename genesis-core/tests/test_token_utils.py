"""Unit tests for token_utils module."""

from genesis_core.llm.token_utils import (
    _flatten_messages,
    _heuristic,
    count_tokens,
    get_max_context_tokens,
)


class TestGetMaxContextTokens:
    # --- Anthropic / Claude models ---
    def test_claude_opus_4_6_returns_1M(self):
        assert get_max_context_tokens("claude-opus-4-6") == 1048576

    def test_claude_sonnet_4_6_returns_1M(self):
        assert get_max_context_tokens("claude-sonnet-4-6") == 1048576

    def test_claude_haiku_4_5_returns_200k(self):
        assert get_max_context_tokens("claude-haiku-4-5") == 204800

    def test_claude_haiku_4_5_dated_returns_200k(self):
        assert get_max_context_tokens("claude-haiku-4-5-20251001") == 204800

    def test_claude_sonnet_4_5_returns_200k(self):
        assert get_max_context_tokens("claude-sonnet-4-5") == 204800

    def test_claude_opus_4_5_returns_1M(self):
        assert get_max_context_tokens("claude-opus-4-5") == 1048576

    # --- OpenAI models ---
    def test_gpt_5_4_returns_1M(self):
        assert get_max_context_tokens("gpt-5.4") == 1048576

    def test_gpt_5_4_mini_returns_400k(self):
        assert get_max_context_tokens("gpt-5.4-mini") == 409600

    def test_gpt_5_4_nano_returns_400k(self):
        assert get_max_context_tokens("gpt-5.4-nano") == 409600

    def test_gpt_4o_returns_128k(self):
        assert get_max_context_tokens("gpt-4o") == 128000

    def test_gpt_4o_mini_returns_128k(self):
        assert get_max_context_tokens("gpt-4o-mini") == 128000

    def test_gpt_3_5_turbo_returns_16k(self):
        assert get_max_context_tokens("gpt-3.5-turbo") == 16385

    # --- Gemini models ---
    def test_gemini_2_5_pro_returns_1M(self):
        assert get_max_context_tokens("gemini-2.5-pro") == 1048576

    def test_gemini_2_0_flash_returns_1M(self):
        assert get_max_context_tokens("gemini-2.0-flash") == 1048576

    # --- Other models ---
    def test_glm_4_7_returns_200k(self):
        assert get_max_context_tokens("glm-4.7") == 204800

    def test_minimax_m2_7_returns_200k(self):
        assert get_max_context_tokens("minimax/m2.7") == 204800

    def test_nemotron_returns_1M(self):
        assert get_max_context_tokens("Nemotron-3-Nano-30B-A3B-BF16") == 1048576

    # --- Unknown ---
    def test_unknown_model_returns_none(self):
        assert get_max_context_tokens("unknown-model") is None


class TestCountTokens:
    def test_uses_heuristic_for_unknown_model(self):
        """Unknown model triggers heuristic fallback: 18 chars // 4 = 4."""
        messages = [{"role": "user", "content": "hello world"}]
        result = count_tokens(messages, "unknown-model")
        assert result == 4

    def test_count_tokens_returns_nonnegative_for_claude_model(self):
        """Claude model uses anthropic counting, returns >= 0 for valid messages."""
        messages = [{"role": "user", "content": "test message"}]
        result = count_tokens(messages, "claude-haiku-4-5")
        assert result >= 0

    def test_count_tokens_uses_heuristic_when_model_not_recognized(self):
        """If model is not recognized by any provider SDK, falls back to heuristic."""
        messages = [{"role": "user", "content": "hello world"}]
        # Uses heuristic: "user: hello world" = 18 chars → 4 tokens
        result = count_tokens(messages, "totally-unknown-model")
        assert result == 4


class TestHeuristic:
    def test_4_chars_per_token(self):
        # "user: " (5) + 40 a's (40) = 45 chars → 45 // 4 = 11
        msgs = [{"role": "user", "content": "a" * 40}]
        assert _heuristic(msgs) == 11

    def test_handles_empty_messages(self):
        assert _heuristic([]) == 0

    def test_no_content_still_counts_role(self):
        # "user: " = 5 chars → 5 // 4 = 1
        msgs = [{"role": "user"}]
        assert _heuristic(msgs) == 1


class TestFlattenMessages:
    def test_flattens_role_and_content(self):
        msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        result = _flatten_messages(msgs)
        assert "user: hi" in result
        assert "assistant: hello" in result

    def test_handles_missing_role(self):
        msgs = [{"content": "hello"}]
        result = _flatten_messages(msgs)
        assert ": hello" in result

    def test_handles_missing_content(self):
        msgs = [{"role": "system"}]
        result = _flatten_messages(msgs)
        assert "system:" in result
