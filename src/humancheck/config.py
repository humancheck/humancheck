"""Configuration management for Humancheck."""
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class HumancheckConfig(BaseSettings):
    """Main configuration for Humancheck platform.

    Configuration can be loaded from:
    1. Environment variables (prefixed with HUMANCHECK_)
    2. YAML configuration file (humancheck.yaml)
    3. Default values
    """

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, description="API port")

    # Streamlit Configuration
    streamlit_host: str = Field(default="0.0.0.0", description="Streamlit host address")
    streamlit_port: int = Field(default=8501, description="Streamlit port")

    # Database Configuration
    storage: str = Field(default="sqlite", description="Storage backend (sqlite or postgresql)")
    db_path: str = Field(default="./humancheck.db", description="Database file path for SQLite")
    db_url: Optional[str] = Field(default=None, description="Database URL for PostgreSQL")

    # Review Configuration
    confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which reviews are required"
    )
    require_review_for: list[str] = Field(
        default=["high-stakes", "compliance"],
        description="Task types that always require review"
    )
    default_reviewers: list[str] = Field(
        default=["admin@example.com"],
        description="Default reviewer email addresses"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # MCP Configuration
    mcp_server_name: str = Field(default="humancheck", description="MCP server name")
    mcp_version: str = Field(default="0.1.0", description="MCP server version")

    # Security Configuration
    enable_auth: bool = Field(default=False, description="Enable authentication")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")


    model_config = SettingsConfigDict(
        env_prefix="HUMANCHECK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def get_database_url(self) -> str:
        """Get the database URL based on configuration.

        Returns:
            Database URL string
        """
        if self.db_url:
            return self.db_url

        if self.storage == "sqlite":
            # Ensure path is absolute
            db_path = Path(self.db_path)
            if not db_path.is_absolute():
                db_path = Path.cwd() / db_path
            return f"sqlite+aiosqlite:///{db_path}"
        elif self.storage == "postgresql":
            raise ValueError(
                "PostgreSQL selected but db_url not provided. "
                "Set HUMANCHECK_DB_URL or db_url in config file."
            )
        else:
            raise ValueError(f"Unknown storage backend: {self.storage}")

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "HumancheckConfig":
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            HumancheckConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid configuration file: {config_path}")

        return cls(**data)

    def to_yaml(self, config_path: str | Path) -> None:
        """Save configuration to YAML file.

        Args:
            config_path: Path to save configuration file
        """
        config_path = Path(config_path)

        # Convert to dict and remove None values
        data = self.model_dump(exclude_none=True)

        with open(config_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def create_default_config(cls, config_path: str | Path) -> "HumancheckConfig":
        """Create a default configuration file.

        Args:
            config_path: Path to save configuration file

        Returns:
            HumancheckConfig instance with default values
        """
        config = cls()
        config.to_yaml(config_path)
        return config


# Global configuration instance
_config: Optional[HumancheckConfig] = None


def init_config(config_path: Optional[str | Path] = None) -> HumancheckConfig:
    """Initialize the global configuration.

    Args:
        config_path: Optional path to YAML configuration file.
                    If not provided, uses environment variables and defaults.

    Returns:
        HumancheckConfig instance
    """
    global _config

    if config_path:
        _config = HumancheckConfig.from_yaml(config_path)
    else:
        # Try to load from default location
        default_paths = [
            Path("humancheck.yaml"),
            Path("humancheck.yml"),
            Path(".humancheck.yaml"),
            Path.home() / ".humancheck" / "config.yaml",
        ]

        for path in default_paths:
            if path.exists():
                _config = HumancheckConfig.from_yaml(path)
                return _config

        # No config file found, use defaults and env vars
        _config = HumancheckConfig()

    return _config


def get_config() -> HumancheckConfig:
    """Get the global configuration instance.

    Returns:
        HumancheckConfig instance

    Raises:
        RuntimeError: If configuration has not been initialized
    """
    if _config is None:
        # Auto-initialize with defaults
        return init_config()
    return _config
