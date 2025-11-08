"""Pytest configuration for sentiment analyzer tests"""

import pytest


@pytest.fixture(autouse=True)
def clear_sentiment_cache():
    """Clear sentiment cache before each test"""
    from ib_sec_mcp.analyzers.sentiment.news import NewsSentimentAnalyzer

    NewsSentimentAnalyzer.clear_cache()
    yield
    NewsSentimentAnalyzer.clear_cache()
