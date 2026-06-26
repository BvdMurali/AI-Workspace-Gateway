"""
AI Workspace Gateway - Provider Interface Template
Defines the abstract wrapper classes for new model adapters.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional

class PromptMessage:
    """Standard message payload representation."""
    def __init__(self, role: str, content: str, tool_call_id: Optional[str] = None):
        self.role: str = role
        self.content: str = content
        self.tool_call_id: Optional[str] = tool_call_id

class TokenChunk:
    """Streaming response chunk representation."""
    def __init__(self, text: str, index: int):
        self.text: str = text
        self.index: int = index

class GenerateResult:
    """Standard text output results container."""
    def __init__(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None, usage: Optional[Dict[str, int]] = None):
        self.content: str = content
        self.tool_calls: Optional[List[Dict[str, Any]]] = tool_calls
        self.usage: Dict[str, int] = usage or {"input_tokens": 0, "output_tokens": 0}

class AbstractAIProvider(ABC):
    """
    Core abstract provider contract.
    All implementation adapters must inherit from this class.
    """

    @abstractmethod
    async def check_health(self) -> bool:
        """Verify endpoint availability and credentials connectivity."""
        pass

    @abstractmethod
    async def generate(
        self, 
        messages: List[PromptMessage], 
        config: Dict[str, Any]
    ) -> GenerateResult:
        """Execute non-streaming text completions."""
        pass

    @abstractmethod
    def generate_stream(
        self, 
        messages: List[PromptMessage], 
        config: Dict[str, Any]
    ) -> AsyncGenerator[TokenChunk, None]:
        """Execute streaming text completions."""
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate float vector embedding dimensions."""
        pass
