"""Configuration management"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ib_sec_mcp.api.models import APICredentials
from ib_sec_mcp.utils.logger import get_logger, mask_sensitive

logger = get_logger(__name__)


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
    query_id: str | None = Field(None, description="Single account query ID")
    token: str | None = Field(None, description="Single account token")

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
    trading_fee_usd: float = Field(
        75.0, description="Default trading fee in USD for ETF swap calculations"
    )

    @field_validator("data_dir", "raw_data_dir", "processed_data_dir", mode="before")
    @classmethod
    def create_directories(cls, v: str | Path) -> Path:
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
        logger.debug("Attempting to load credentials from environment")

        # Check if credentials exist in environment
        query_id_exists = bool(self.query_id)
        token_exists = bool(self.token)

        logger.debug(f"QUERY_ID present: {query_id_exists}")
        logger.debug(f"TOKEN present: {token_exists}")

        if not self.query_id or not self.token:
            logger.error("Missing credentials: QUERY_ID and TOKEN must be set in environment")
            raise ValueError("QUERY_ID and TOKEN must be set in environment")

        # Log masked credentials for debugging
        logger.debug(f"Loaded credentials: QUERY_ID={mask_sensitive(self.query_id, 4)}")
        logger.debug(f"Loaded credentials: TOKEN={mask_sensitive(self.token, 4)}")

        credentials = APICredentials(
            query_id=self.query_id,
            token=self.token,
            account_alias="Default",
        )

        logger.info("Credentials loaded successfully")
        return credentials

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Config":
        """
        Load configuration from .env file

        Args:
            env_file: Path to .env file (default: .env in current directory)

        Returns:
            Config instance
        """
        # Determine .env file path
        env_path = Path(env_file) if env_file else Path.cwd() / ".env"

        logger.debug(f"Loading configuration from: {env_path}")
        logger.debug(f"Current working directory: {Path.cwd()}")
        logger.debug(f".env file exists: {env_path.exists()}")

        # Check environment before loading .env
        query_id_before = os.getenv("QUERY_ID")
        token_before = os.getenv("TOKEN")
        logger.debug(
            f"Environment before load: QUERY_ID={bool(query_id_before)}, TOKEN={bool(token_before)}"
        )

        # Load .env file
        loaded = load_dotenv(env_file) if env_file else load_dotenv()

        logger.debug(f"dotenv load_dotenv() returned: {loaded}")

        # Check environment after loading .env
        query_id_after = os.getenv("QUERY_ID")
        token_after = os.getenv("TOKEN")
        logger.debug(
            f"Environment after load: QUERY_ID={bool(query_id_after)}, TOKEN={bool(token_after)}"
        )

        if query_id_after:
            logger.debug(f"QUERY_ID value: {mask_sensitive(query_id_after, 4)}")
        if token_after:
            logger.debug(f"TOKEN value: {mask_sensitive(token_after, 4)}")

        config = cls()
        logger.info(f"Configuration loaded from {env_path}")

        return config
