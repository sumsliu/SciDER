from __future__ import annotations

from threading import RLock
from time import sleep
from typing import Callable

from functional import seq
from loguru import logger
from openai import OpenAI, APITimeoutError, RateLimitError as OpenAIRateLimitError, APIError

from ..tools import ToolRegistry
from .constant import __AGENT_STATE_NAME__
from .message_utils import validate_and_clean_messages
from .types import Message


class ZeroChoiceError(Exception):
    """Raised when LLM completion returns zero choices."""

    pass


def function_to_json_schema(func_or_name: Callable | str) -> dict:
    if isinstance(func_or_name, str):
        tool = ToolRegistry.instance().tools[func_or_name]
        return tool.json_schema
    elif callable(func_or_name):
        tool = ToolRegistry.instance().tools[func_or_name.__name__]
        return tool.json_schema
    else:
        raise ValueError("func must be a string or a callable")


class ModelRegistry:
    _instance: ModelRegistry | None = None
    _lock: RLock = RLock()

    def __new__(cls) -> ModelRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.models = {}

    @classmethod
    def instance(cls) -> ModelRegistry:
        return cls()

    @classmethod
    def register(
        cls,
        name: str,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs,
    ):
        cls.instance().models[name] = {
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            **kwargs,
        }
        logger.debug("Registered model: {}", name)

    def get_model_params(self, name: str) -> dict:
        if name not in self.models:
            raise ValueError(f"Model `{name}` not found")
        return self.models[name]

    @classmethod
    def completion(cls, *args, **kwargs) -> Message:
        # completion with retry for RateLimitError
        max_retries = 3

        for attempt in range(max_retries):
            try:
                return cls._completion(*args, **kwargs)
            except OpenAIRateLimitError as e:
                rate_limit_delay = 65  # seconds
                if attempt == max_retries - 1:
                    # Last attempt failed, re-raise
                    logger.error(f"RateLimitError after {max_retries} attempts: {str(e)}")
                    raise
                # Wait and retry
                logger.warning(
                    f"RateLimitError on attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {rate_limit_delay}s before retry... Error: {str(e)}"
                )
                sleep(rate_limit_delay)
            except ZeroChoiceError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    f"Encountered ZeroChoiceError({str(e)}) in LLM completion. Retrying {attempt + 1}/{max_retries} after 45 seconds..."
                )
                sleep(45)  # brief wait before retry
            except APIError as e:
                # Handle service unavailable and other API errors
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    f"Encountered APIError({str(e)}) in LLM completion. Retrying {attempt + 1}/{max_retries} after 60 seconds..."
                )
                sleep(60)  # brief wait before retry

    @classmethod
    def _completion(
        cls,
        name: str,
        history: list[Message],
        system_prompt: str,
        agent_sender: str | None = None,
        tools: list | None = None,
        tool_choice: str | None = None,
        **kwargs,
    ) -> Message:
        tools_json_schemas = [function_to_json_schema(tool) for tool in tools] if tools else []
        for schema in tools_json_schemas:
            params = schema["function"]["parameters"]
            params["properties"].pop(__AGENT_STATE_NAME__, None)
            if __AGENT_STATE_NAME__ in params["required"]:
                params["required"].remove(__AGENT_STATE_NAME__)

        messages = [Message(role="system", content=system_prompt)] + history

        model_params: dict = cls.instance().get_model_params(name)

        logger.trace("Using OpenAI SDK for model: {}", name)

        # Use OpenAI SDK directly
        model_params_copy = model_params.copy()

        # Create OpenAI client with custom base_url if provided
        client_kwargs = {}
        if model_params_copy.get("base_url"):
            client_kwargs["base_url"] = model_params_copy.pop("base_url")
        if model_params_copy.get("api_key"):
            client_kwargs["api_key"] = model_params_copy.pop("api_key")

        client = OpenAI(**client_kwargs)

        # Prepare messages
        openai_messages = [msg.to_ll_message() for msg in messages]

        # Validate and clean message sequence for OpenAI API compatibility
        openai_messages = validate_and_clean_messages(openai_messages)

        # Prepare request parameters
        request_params = {
            "model": model_params_copy["model"],
            "messages": openai_messages,
        }

        # Add tools if provided
        if tools_json_schemas:
            request_params["tools"] = tools_json_schemas
        if tool_choice:
            request_params["tool_choice"] = tool_choice

        # Add any additional kwargs
        request_params.update(kwargs)

        # Make API call
        response = client.chat.completions.create(**request_params)

        if not response.choices or len(response.choices) == 0:
            raise ZeroChoiceError("No choices returned from OpenAI API")

        # Convert response to Message
        msg: Message = Message.from_ll_message(response.choices[0].message)
        msg.llm_sender = name
        msg.agent_sender = agent_sender
        msg.completion_tokens = response.usage.completion_tokens if response.usage else 0
        msg.prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        return msg

    @classmethod
    def embedding(cls, name: str, texts: list[str], **kwargs) -> list[list[float]]:
        """Returns a list of embeddings for the given texts."""
        model_params: dict = cls.instance().models[name]

        # Create OpenAI client with custom base_url if provided
        client_kwargs = {}
        if model_params.get("base_url"):
            client_kwargs["base_url"] = model_params["base_url"]
        if model_params.get("api_key"):
            client_kwargs["api_key"] = model_params["api_key"]

        client = OpenAI(**client_kwargs)

        # Make API call
        response = client.embeddings.create(
            model=model_params["model"],
            input=texts,
            **kwargs
        )

        return [d.embedding for d in response.data]

