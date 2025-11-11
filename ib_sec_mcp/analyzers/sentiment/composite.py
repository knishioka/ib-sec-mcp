"""
Composite sentiment analyzer

Aggregates sentiment from multiple sources with configurable weights.
"""

import logging
from datetime import datetime
from decimal import Decimal

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore

logger = logging.getLogger(__name__)


class CompositeSentimentAnalyzer(BaseSentimentAnalyzer):
    """
    Composite sentiment analyzer

    Aggregates sentiment scores from multiple sources (news, social media,
    analyst ratings, etc.) using configurable weights.

    Attributes:
        sources: Dictionary mapping source names to analyzer instances
        weights: Dictionary mapping source names to Decimal weights (normalized to sum to 1.0)
    """

    def __init__(
        self,
        sources: dict[str, BaseSentimentAnalyzer] | None = None,
        weights: dict[str, Decimal] | None = None,
    ):
        """
        Initialize composite sentiment analyzer

        Args:
            sources: Dictionary mapping source names to analyzer instances
            weights: Optional dictionary mapping source names to weights.
                    If not provided, equal weights are used.
                    Weights will be normalized to sum to 1.0.

        Raises:
            ValueError: If weights contain negative values
        """
        self.sources = sources or {}
        self.weights = self._normalize_weights(weights or {})

        # Validate weights
        for name, weight in self.weights.items():
            if weight < Decimal("0"):
                raise ValueError(f"Weight for {name} must be non-negative, got {weight}")

    def _normalize_weights(self, weights: dict[str, Decimal]) -> dict[str, Decimal]:
        """
        Normalize weights to sum to 1.0

        If no weights provided, use equal weights for all sources.

        Args:
            weights: Dictionary of weights

        Returns:
            Normalized weights summing to 1.0
        """
        if not self.sources:
            return {}

        # Use equal weights if none provided
        if not weights:
            equal_weight = Decimal("1.0") / Decimal(len(self.sources))
            return dict.fromkeys(self.sources, equal_weight)

        # Validate all source names have weights
        for name in self.sources:
            if name not in weights:
                logger.warning(f"No weight provided for source {name}, using 0")
                weights[name] = Decimal("0")

        # Normalize to sum to 1.0
        total = sum(weights.values(), Decimal("0.0"))
        if total == Decimal("0"):
            # All weights are zero, fall back to equal weights
            equal_weight = Decimal("1.0") / Decimal(len(self.sources))
            return dict.fromkeys(self.sources, equal_weight)

        return {name: weight / total for name, weight in weights.items()}

    async def analyze_sentiment(self, symbol: str) -> SentimentScore:
        """
        Analyze composite sentiment from multiple sources

        Args:
            symbol: Stock ticker symbol

        Returns:
            Aggregated SentimentScore combining all sources

        Raises:
            Exception: If all sources fail (returns neutral sentiment)
        """
        if not self.sources:
            logger.warning("No sources configured for composite analyzer")
            return SentimentScore(
                score=Decimal("0.0"),
                confidence=Decimal("0.0"),
                timestamp=datetime.now(),
                reasoning="No sentiment sources configured",
            )

        # Collect sentiment from all sources
        results: dict[str, SentimentScore] = {}
        failed_sources: list[str] = []

        for name, analyzer in self.sources.items():
            try:
                result = await analyzer.analyze_sentiment(symbol)
                results[name] = result
                logger.debug(f"Source {name}: score={result.score}, confidence={result.confidence}")
            except Exception as e:
                logger.error(f"Source {name} failed: {e}")
                failed_sources.append(name)

        # Handle case where all sources failed
        if not results:
            logger.error("All sentiment sources failed")
            return SentimentScore(
                score=Decimal("0.0"),
                confidence=Decimal("0.0"),
                timestamp=datetime.now(),
                reasoning="All sentiment sources failed to provide data",
            )

        # Re-normalize weights excluding failed sources
        active_weights = self._renormalize_for_active_sources(set(results.keys()))

        # Aggregate sentiments
        return self._aggregate_sentiments(symbol, results, active_weights)

    def _renormalize_for_active_sources(self, active_sources: set[str]) -> dict[str, Decimal]:
        """
        Re-normalize weights for only active (non-failed) sources

        Args:
            active_sources: Set of source names that succeeded

        Returns:
            Re-normalized weights for active sources
        """
        active_weights = {
            name: weight for name, weight in self.weights.items() if name in active_sources
        }

        total = sum(active_weights.values(), Decimal("0.0"))
        if total == Decimal("0"):
            # All active sources had zero weight, use equal weights
            equal_weight = Decimal("1.0") / Decimal(len(active_sources))
            return dict.fromkeys(active_sources, equal_weight)

        return {name: weight / total for name, weight in active_weights.items()}

    def _aggregate_sentiments(
        self,
        symbol: str,
        results: dict[str, SentimentScore],
        weights: dict[str, Decimal],
    ) -> SentimentScore:
        """
        Aggregate sentiment scores using weighted average

        Args:
            symbol: Stock symbol
            results: Dictionary of sentiment results by source name
            weights: Normalized weights for each source

        Returns:
            Aggregated SentimentScore
        """
        # Calculate weighted average sentiment
        weighted_score = sum(results[name].score * weights[name] for name in results)

        # Calculate confidence
        # Average confidence weighted by source weights
        weighted_confidence = sum(results[name].confidence * weights[name] for name in results)

        # Apply disagreement penalty
        if len(results) > 1:
            scores = [result.score for result in results.values()]
            mean = sum(scores, Decimal("0.0")) / Decimal(len(scores))
            variance = sum((s - mean) ** 2 for s in scores) / Decimal(len(scores))
            std_dev = variance ** Decimal("0.5")

            # High disagreement reduces confidence
            if std_dev > Decimal("0.6"):
                weighted_confidence *= Decimal("0.5")  # Strong disagreement
            elif std_dev > Decimal("0.4"):
                weighted_confidence *= Decimal("0.7")  # Moderate disagreement
            elif std_dev > Decimal("0.2"):
                weighted_confidence *= Decimal("0.85")  # Slight disagreement

        # Combine themes and risk factors from all sources
        all_themes = set()
        all_risks = set()

        for result in results.values():
            all_themes.update(result.key_themes)
            all_risks.update(result.risk_factors)

        # Create reasoning
        reasoning = f"Aggregated sentiment from {len(results)} source(s): "
        reasoning += ", ".join(
            f"{name} ({results[name].score:+.2f})" for name in sorted(results.keys())
        )

        return SentimentScore(
            score=weighted_score,
            confidence=weighted_confidence,
            timestamp=datetime.now(),
            key_themes=list(all_themes)[:10],  # Limit to top 10
            risk_factors=list(all_risks)[:10],  # Limit to top 10
            reasoning=reasoning,
        )


__all__ = ["CompositeSentimentAnalyzer"]
