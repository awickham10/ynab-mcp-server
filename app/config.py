"""Configuration management for YNAB MCP Server."""

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings


class YNABConfig(BaseSettings):
    """YNAB MCP Server configuration."""

    # OAuth settings — must match the YNAB OAuth app you create
    YNAB_CLIENT_ID: str = "your-ynab-client-id"
    YNAB_CLIENT_SECRET: SecretStr = SecretStr("your-ynab-client-secret")
    YNAB_BASE_URL: AnyHttpUrl = "http://localhost:8000"
    YNAB_READ_ONLY: bool = False

    # FastMCP session persistence (required for multi-replica / restartable
    # deployments — without these, FastMCP's HS256 signing key and OAuth client
    # storage are ephemeral and clients lose their sessions on every restart).
    # Not YNAB-specific; these belong to the FastMCP OAuth proxy itself.
    JWT_SIGNING_KEY: SecretStr | None = None
    STORAGE_ENCRYPTION_KEY: SecretStr | None = None
    REDIS_URL: SecretStr | None = None  # Railway injects this when Redis is attached

    # API settings
    ynab_api_base_url: str = "https://api.ynab.com/v1"
    request_timeout: int = 30
    max_retries: int = 3

    # Server settings
    server_name: str = "YNAB MCP Server"
    server_version: str = "1.0.0"

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


config = YNABConfig()
