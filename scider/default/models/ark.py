import logging
import os
import sys

from scider.core.llms import ModelRegistry

logger = logging.getLogger(__name__)

# Ark model from Volcengine (火山引擎)
ARK_MODEL = "ark-code-latest"


def _resolve_ark_config() -> tuple[str, str, str]:
    """Resolve Ark API configuration from environment variables.

    Returns:
        Tuple of (api_key, base_url, model_name)

    Raises:
        SystemExit: If required configuration is not found in environment.
    """
    api_key = os.getenv("ANTHROPIC_AUTH_TOKEN")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    model_name = os.getenv("ANTHROPIC_MODEL", ARK_MODEL)

    if api_key is None:
        logger.error(
            "ANTHROPIC_AUTH_TOKEN is required but not found in environment variable."
        )
        sys.exit(1)

    if base_url is None:
        logger.error(
            "ANTHROPIC_BASE_URL is required but not found in environment variable."
        )
        sys.exit(1)

    return api_key, base_url, model_name


def register_ark_models() -> None:
    """Register Ark models from Volcengine in the ModelRegistry.

    Uses environment variables:
        - ANTHROPIC_AUTH_TOKEN: Ark API authentication token
        - ANTHROPIC_BASE_URL: Ark API base URL
        - ANTHROPIC_MODEL: Model name (default: ark-code-latest)
    """
    api_key, base_url, model_name = _resolve_ark_config()

    # Register all agent models with Ark
    ModelRegistry.register(
        name="ideation",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="paper_search",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="metric_search",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="data",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="plan",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="critic",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="mem",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    # Use OpenAI embeddings (Ark doesn't provide embeddings)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        ModelRegistry.register(
            name="embed",
            model="text-embedding-3-small",
            api_key=openai_key,
        )
    else:
        logger.warning(
            "OPENAI_API_KEY not found. Embedding model not registered. "
            "Set OPENAI_API_KEY for embedding support."
        )

    ModelRegistry.register(
        name="history",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="experiment_agent",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="experiment_coding",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="experiment_execute",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="experiment_monitor",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    ModelRegistry.register(
        name="experiment_summary",
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    logger.info(f"✅ Registered Ark models: {model_name} @ {base_url}")
