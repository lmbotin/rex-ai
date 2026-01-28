"""
Configuration for FNOL extraction pipeline.

Handles API keys and model settings.
"""

import os
from typing import Optional


class ExtractionConfig:
    """Configuration for extraction pipeline."""

    def __init__(
        self,
        llm_provider: str = "claude",
        llm_model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize extraction configuration.

        Args:
            llm_provider: LLM provider ('claude', 'openai', or 'mock')
            llm_model: Specific model to use (default depends on provider)
            api_key: API key (if None, reads from environment)
            max_retries: Maximum API retry attempts
            timeout: Request timeout in seconds
        """
        self.llm_provider = llm_provider.lower()
        self.max_retries = max_retries
        self.timeout = timeout

        # Set default models
        if llm_model is None:
            if self.llm_provider == "claude":
                self.llm_model = "claude-3-5-sonnet-20241022"
            elif self.llm_provider == "openai":
                self.llm_model = "gpt-4-turbo"
            else:
                self.llm_model = "mock"
        else:
            self.llm_model = llm_model

        # Get API key from parameter or environment
        if api_key:
            self.api_key = api_key
        elif self.llm_provider == "claude":
            self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        elif self.llm_provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        else:
            self.api_key = ""

    @classmethod
    def from_env(cls) -> "ExtractionConfig":
        """Create config from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "mock")  # Default to mock
        model = os.getenv("LLM_MODEL")
        return cls(llm_provider=provider, llm_model=model)

    def validate(self) -> bool:
        """Check if configuration is valid."""
        if self.llm_provider in ["claude", "openai"]:
            return bool(self.api_key)
        return True  # Mock doesn't need API key


# Default configuration
DEFAULT_CONFIG = ExtractionConfig.from_env()
