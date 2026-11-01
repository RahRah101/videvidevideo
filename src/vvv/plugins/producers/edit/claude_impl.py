"""Claude as the `e:` LLM backend. Entry point `claude` in `vvv.llm_backends`; config section `claude:`.

config:
  claude: { model: claude-sonnet-5-5, max_tokens: 32000, effort: high }
"""
from __future__ import annotations
import base64

from .llm_backend import LLMBackend, Message, Usage

DEFAULT_MODEL = "claude-sonnet-5-5"
CONFIG_KEYS = {"model", "max_tokens", "effort"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
# Server-side refusal fallback: if the model declines, the API reruns on a fallback model in the
# same call. Not in the installed SDK's signature yet, so it goes through extra_body.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeLLM(LLMBackend):
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 32000, effort: str | None = None):
        import anthropic          # only when a script actually has `e:` lines
        self._anthropic = anthropic
        try:
            # credentials: ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or an `ant auth login` profile
            self.client = anthropic.Anthropic()
        except anthropic.AnthropicError as e:
            raise ValueError(f"claude: no Anthropic credentials ({e}). "
                             "Set ANTHROPIC_API_KEY in your shell or run `ant auth login`.") from None
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort

    @classmethod
    def from_config(cls, config) -> "ClaudeLLM":
        sec = config.section("claude", CONFIG_KEYS)
        effort = sec.get("effort")
        if effort is not None and effort not in EFFORTS:
            raise ValueError(f"claude.effort: one of {sorted(EFFORTS)}, got {effort!r}")
        max_tokens = sec.get("max_tokens", 32000)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1024:
            raise ValueError(f"claude.max_tokens: a whole number >= 1024, got {max_tokens!r}")
        return cls(model=str(sec.get("model", DEFAULT_MODEL)), max_tokens=max_tokens, effort=effort)

    def cache_identity(self) -> dict:
        return {"backend": "claude", "model": self.model, "effort": self.effort}

    @property
    def label(self) -> str:
        return self.model

    def complete(self, system: str, messages: list[Message]) -> tuple[str, Usage]:
        api_messages = [{"role": m.role, "content": _content(m)} for m in messages]
        kwargs = {}
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        # streaming: a whole HTML file plus thinking can take long enough to hit HTTP timeouts
        with self.client.beta.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=api_messages,
            betas=[FALLBACK_BETA],
            extra_body={"fallbacks": "default"},
            **kwargs,
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise RuntimeError(f"claude declined the edit ({getattr(details, 'category', None)}): "
                               f"{getattr(details, 'explanation', '')}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError(f"claude hit max_tokens={self.max_tokens} before finishing; "
                               "raise `claude: {max_tokens}` or simplify the prompt")
        text = "".join(b.text for b in response.content if b.type == "text")
        if response.model != self.model:
            print(f"[claude] note: served by fallback model {response.model}")
        return text, Usage(response.usage.input_tokens, response.usage.output_tokens)


def _content(m: Message) -> list[dict] | str:
    if not m.images:
        return m.text
    blocks: list[dict] = [
        {"type": "image", "source": {"type": "base64", "media_type": img.media_type,
                                     "data": base64.standard_b64encode(img.data).decode("ascii")}}
        for img in m.images
    ]
    blocks.append({"type": "text", "text": m.text})       # images first, then the text about them
    return blocks
