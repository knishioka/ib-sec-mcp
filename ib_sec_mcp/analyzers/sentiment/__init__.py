"""
Sentiment analysis module for stock market analysis

Provides sentiment analysis from multiple sources including news articles,
social media, and analyst ratings.
"""

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore
from ib_sec_mcp.analyzers.sentiment.composite import CompositeSentimentAnalyzer
from ib_sec_mcp.analyzers.sentiment.news import NewsSentimentAnalyzer

__all__ = [
    "BaseSentimentAnalyzer",
    "SentimentScore",
    "NewsSentimentAnalyzer",
    "CompositeSentimentAnalyzer",
]
