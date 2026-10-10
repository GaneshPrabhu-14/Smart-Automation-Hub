"""GenAI layer: Groq or xAI through the OpenAI-compatible client."""
import time

from . import config

try:
    from openai import OpenAI, RateLimitError
except ImportError:
    OpenAI = None
    RateLimitError = None

RATE_LIMIT_ERRORS = (RateLimitError,) if RateLimitError is not None else ()


class LLM:
    def __init__(self):
        self.live = bool(config.LLM_API_KEY and OpenAI)
        self.client = (OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
                       if self.live else None)

    @property
    def mode(self) -> str:
        return f"LIVE LLM ({config.MODEL})" if self.live else "OFFLINE demo (rule-based)"

    def complete(self, messages: list, tools: list | None = None):
        kwargs = {"model": config.MODEL, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        try:
            return self.client.chat.completions.create(**kwargs)
        except RATE_LIMIT_ERRORS:
            time.sleep(config.LLM_RATE_LIMIT_RETRY_SECONDS)
            return self.client.chat.completions.create(**kwargs)
