"""Base adapter interface and UniversalReview format."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from ..models import UrgencyLevel


@dataclass
class UniversalReview:
    """Universal review format that normalizes all review requests.

    This is the core abstraction that allows Humancheck to work with any AI framework.
    All framework-specific adapters convert their requests to this format.
    """
    task_type: str
    proposed_action: str
    agent_reasoning: Optional[str] = None
    confidence_score: Optional[float] = None
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    framework: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    organization_id: Optional[int] = None
    agent_id: Optional[int] = None
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_type": self.task_type,
            "proposed_action": self.proposed_action,
            "agent_reasoning": self.agent_reasoning,
            "confidence_score": self.confidence_score,
            "urgency": self.urgency.value if isinstance(self.urgency, UrgencyLevel) else self.urgency,
            "framework": self.framework,
            "metadata": self.metadata,
            "organization_id": self.organization_id,
            "agent_id": self.agent_id,
            "blocking": self.blocking,
        }


class ReviewAdapter(ABC):
    """Base adapter interface for framework integrations.

    Each AI framework (LangChain, Mastra, MCP, etc.) implements this interface
    to convert their specific request format into UniversalReview and vice versa.
    """

    @abstractmethod
    def to_universal(self, framework_request: Any) -> UniversalReview:
        """Convert framework-specific request to UniversalReview.

        Args:
            framework_request: Framework-specific request object

        Returns:
            UniversalReview instance
        """
        pass

    @abstractmethod
    def from_universal(self, universal_review: UniversalReview, decision: Any) -> Any:
        """Convert UniversalReview and decision back to framework-specific format.

        Args:
            universal_review: UniversalReview instance
            decision: Decision object from database

        Returns:
            Framework-specific response object
        """
        pass

    @abstractmethod
    def get_framework_name(self) -> str:
        """Get the name of the framework this adapter supports.

        Returns:
            Framework name (e.g., 'langchain', 'mastra', 'mcp', 'rest')
        """
        pass

    @abstractmethod
    async def handle_blocking(self, review_id: int, timeout: Optional[float] = None) -> Any:
        """Handle blocking review requests (wait for decision).

        Args:
            review_id: ID of the review to wait for
            timeout: Optional timeout in seconds

        Returns:
            Decision result when available

        Raises:
            TimeoutError: If timeout is reached before decision is made
        """
        pass

    async def validate_request(self, framework_request: Any) -> bool:
        """Validate framework-specific request.

        Args:
            framework_request: Framework-specific request object

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If request is invalid
        """
        # Default implementation - subclasses can override
        return True
