"""
Base sentiment analyzer classes and models

Provides abstract interface for sentiment analysis implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class SentimentScore(BaseModel):
    """
    Sentiment analysis result

    Sentiment score ranges from -1.0 (very negative) to 1.0 (very positive).
    Confidence represents the reliability of the sentiment assessment.

    Attributes:
        score: Sentiment score from -1.0 (negative) to 1.0 (positive)
        confidence: Analysis confidence from 0.0 (no confidence) to 1.0 (high confidence)
        timestamp: When the sentiment was analyzed
        key_themes: Optional list of key themes identified in the analysis
        risk_factors: Optional list of risk factors identified in the analysis
        reasoning: Optional explanation of the sentiment score
    """

    score: Decimal = Field(
        ...,
        description="Sentiment score from -1.0 (negative) to 1.0 (positive)",
    )
    confidence: Decimal = Field(
        ...,
        description="Confidence level from 0.0 (no confidence) to 1.0 (high confidence)",
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp when sentiment was analyzed",
    )
    key_themes: list[str] = Field(
        default_factory=list,
        description="Key themes identified in the analysis",
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Risk factors identified in the analysis",
    )
    reasoning: str = Field(
        default="",
        description="Explanation of the sentiment score",
    )

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: Decimal) -> Decimal:
        """
        Validate sentiment score is within valid range

        Args:
            v: Score value to validate

        Returns:
            Validated score

        Raises:
            ValueError: If score is outside [-1.0, 1.0] range
        """
        if v < Decimal("-1.0") or v > Decimal("1.0"):
            raise ValueError(f"Score must be between -1.0 and 1.0, got {v}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: Decimal) -> Decimal:
        """
        Validate confidence is within valid range

        Args:
            v: Confidence value to validate

        Returns:
            Validated confidence

        Raises:
            ValueError: If confidence is outside [0.0, 1.0] range
        """
        if v < Decimal("0.0") or v > Decimal("1.0"):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return v

    model_config = {
        "json_encoders": {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }
    }


class BaseSentimentAnalyzer(ABC):
    """
    Abstract base class for sentiment analyzers

    Provides common interface for all sentiment analysis implementations.
    Subclasses must implement the analyze_sentiment method.

    Example:
        >>> class MySentimentAnalyzer(BaseSentimentAnalyzer):
        ...     async def analyze_sentiment(self, symbol: str) -> SentimentScore:
        ...         # Implementation here
        ...         return SentimentScore(
        ...             score=Decimal("0.5"),
        ...             confidence=Decimal("0.8"),
        ...             timestamp=datetime.now()
        ...         )
    """

    @abstractmethod
    async def analyze_sentiment(self, symbol: str) -> SentimentScore:
        """
        Analyze sentiment for a stock symbol

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")

        Returns:
            SentimentScore with sentiment analysis results

        Raises:
            Exception: Implementation-specific exceptions for failures
        """
        pass


__all__ = ["SentimentScore", "BaseSentimentAnalyzer"]
