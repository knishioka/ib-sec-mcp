"""Base report class"""

from abc import ABC, abstractmethod

from ib_sec_mcp.analyzers.base import AnalysisResult


class BaseReport(ABC):
    """
    Base class for all reports

    Provides common interface for report generation
    """

    def __init__(self, results: list[AnalysisResult]):
        """
        Initialize report

        Args:
            results: List of analysis results
        """
        self.results = results

    @abstractmethod
    def render(self) -> str:
        """
        Render report

        Returns:
            Rendered report as string
        """
        pass

    @abstractmethod
    def save(self, filepath: str) -> None:
        """
        Save report to file

        Args:
            filepath: Output file path
        """
        pass
