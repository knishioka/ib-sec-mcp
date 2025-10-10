"""Configuration management"""

from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ib_sec_mcp.api.models import APICredentials


class Config(BaseSettings):
    """
    Application configuration loaded from environment variables

    Configuration:
        QUERY_ID=your_query_id
        TOKEN=your_token

    Note: A single Flex Query can return data for multiple accounts.
    Configure multiple accounts in your IB Flex Query settings.
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
    def create_directories(cls, v: Union[str, Path]) -> Path:
        """Ensure directories exist"""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v

    def get_credentials(self) -> APICredentials:
        """
        Get API credentials from environment

        Returns:
            APICredentials for Flex Query access
        """
        if not self.query_id or not self.token:
            raise ValueError("QUERY_ID and TOKEN must be set in environment")

        return APICredentials(
            query_id=self.query_id,
            token=self.token,
            account_alias="Default",
        )

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
