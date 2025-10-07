"""Report generation module"""

from ib_sec_mcp.reports.base import BaseReport
from ib_sec_mcp.reports.console import ConsoleReport

__all__ = ["BaseReport", "ConsoleReport"]
