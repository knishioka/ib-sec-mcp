"""Base analyzer class"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.portfolio import Portfolio
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import Trade


class AnalysisResult(dict[str, Any]):
    """
    Analysis result container

    Flexible dictionary-based result with metadata
    """

    def __init__(self, analyzer_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self["analyzer"] = analyzer_name
        self["timestamp"] = None  # Set during analysis


class BaseAnalyzer(ABC):
    """
    Base class for all analyzers

    Provides common interface and utilities for analysis modules
    """

    def __init__(
        self,
        portfolio: Optional[Portfolio] = None,
        account: Optional[Account] = None,
    ):
        """
        Initialize analyzer

        Args:
            portfolio: Portfolio to analyze (for multi-account)
            account: Single account to analyze

        Raises:
            ValueError: If neither portfolio nor account is provided
        """
        if portfolio is None and account is None:
            raise ValueError("Either portfolio or account must be provided")

        self.portfolio = portfolio
        self.account = account
        self.is_multi_account = portfolio is not None

    @property
    def analyzer_name(self) -> str:
        """Get analyzer name (class name without 'Analyzer' suffix)"""
        return self.__class__.__name__.replace("Analyzer", "")

    @abstractmethod
    def analyze(self) -> AnalysisResult:
        """
        Run analysis

        Returns:
            AnalysisResult with findings
        """
        pass

    def _create_result(self, **kwargs: Any) -> AnalysisResult:
        """
        Create analysis result with metadata

        Args:
            **kwargs: Result data

        Returns:
            AnalysisResult instance
        """
        from datetime import datetime

        result = AnalysisResult(self.analyzer_name, **kwargs)
        result["timestamp"] = datetime.now().isoformat()
        result["is_multi_account"] = self.is_multi_account

        if self.is_multi_account and self.portfolio:
            result["account_count"] = self.portfolio.account_count
            result["from_date"] = self.portfolio.from_date.isoformat()
            result["to_date"] = self.portfolio.to_date.isoformat()
        elif self.account:
            result["account_id"] = self.account.account_id
            result["from_date"] = self.account.from_date.isoformat()
            result["to_date"] = self.account.to_date.isoformat()

        return result

    def get_trades(self) -> list[Trade]:
        """Get trades from portfolio or account"""
        if self.is_multi_account and self.portfolio:
            return self.portfolio.all_trades
        elif self.account:
            return self.account.trades
        return []

    def get_positions(self) -> list[Position]:
        """Get positions from portfolio or account"""
        if self.is_multi_account and self.portfolio:
            return self.portfolio.all_positions
        elif self.account:
            return self.account.positions
        return []

    def get_total_value(self) -> Decimal:
        """Get total value from portfolio or account"""
        if self.is_multi_account and self.portfolio:
            return self.portfolio.total_value
        elif self.account:
            return self.account.total_value
        return Decimal("0")

    def get_total_cash(self) -> Decimal:
        """Get total cash from portfolio or account"""
        if self.is_multi_account and self.portfolio:
            return self.portfolio.total_cash
        elif self.account:
            return self.account.total_cash
        return Decimal("0")
