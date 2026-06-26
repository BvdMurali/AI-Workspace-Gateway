"""
AI Workspace Gateway - Provider Capabilities Checker Template
"""

from typing import Set

class ProviderCapabilities:
    """
    Defines capabilities supported by the provider's active model metadata.
    """
    
    def __init__(self, model_id: str):
        self.model_id = model_id

    def get_supported_features(self) -> Set[str]:
        """
        Returns set of flags matching capabilities.
        Allowed flags: {"text", "vision", "tool_calling", "embeddings"}.
        """
        return set()
