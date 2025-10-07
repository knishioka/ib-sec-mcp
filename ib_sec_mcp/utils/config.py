"""Configuration management"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ib_sec_mcp.api.models import APICredentials


class Config(BaseSettings):
    """
    Application configuration loaded from environment variables

    Supports both single and multi-account configurations:

    Single account:
        QUERY_ID=123
        TOKEN=abc

    Multiple accounts:
        ACCOUNT_1_QUERY_ID=123
        ACCOUNT_1_TOKEN=abc
        ACCOUNT_1_ALIAS=Main
        ACCOUNT_2_QUERY_ID=456
        ACCOUNT_2_TOKEN=def
        ACCOUNT_2_ALIAS=Trading
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Single account config
    query_id: Optional[str] = Field(None, description="Single account query ID")
    token: Optional[str] = Field(None, description="Single account token")

    # API settings
    api_timeout: int = Field(30, description="API timeout in seconds")
    api_max_retries: int = Field(3, description="Maximum API retry attempts")
    api_retry_delay: int = Field(5, description="Delay between retries in seconds")

    # Data paths
    data_dir: Path = Field(Path("data"), description="Data directory")
    raw_data_dir: Path = Field(Path("data/raw"), description="Raw data directory")
    processed_data_dir: Path = Field(Path("data/processed"), description="Processed data directory")

    # Analysis settings
    default_currency: str = Field("USD", description="Default currency for analysis")
    tax_rate: float = Field(0.30, description="Default tax rate for estimates")

    @field_validator("data_dir", "raw_data_dir", "processed_data_dir", mode="before")
    @classmethod
    def create_directories(cls, v: Path) -> Path:
        """Ensure directories exist"""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v

    def get_credentials(self) -> list[APICredentials]:
        """
        Get API credentials from environment

        Returns:
            List of APICredentials (single or multiple accounts)
        """
        credentials = []

        # Try single account config first
        if self.query_id and self.token:
            credentials.append(
                APICredentials(
                    query_id=self.query_id,
                    token=self.token,
                    account_alias="Default",
                )
            )
            return credentials

        # Try multi-account config
        account_num = 1
        while True:
            prefix = f"ACCOUNT_{account_num}_"
            query_id = os.getenv(f"{prefix}QUERY_ID")
            token = os.getenv(f"{prefix}TOKEN")

            if not query_id or not token:
                break

            account_id = os.getenv(f"{prefix}ACCOUNT_ID")
            alias = os.getenv(f"{prefix}ALIAS", f"Account {account_num}")

            credentials.append(
                APICredentials(
                    query_id=query_id,
                    token=token,
                    account_id=account_id,
                    account_alias=alias,
                )
            )
            account_num += 1

        if not credentials:
            raise ValueError(
                "No credentials found. Please set QUERY_ID/TOKEN or ACCOUNT_N_QUERY_ID/TOKEN"
            )

        return credentials

    @classmethod
    def load(cls, env_file: Optional[Path] = None) -> "Config":
        """
        Load configuration from .env file

        Args:
            env_file: Path to .env file (default: .env in current directory)

        Returns:
            Config instance
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        return cls()
