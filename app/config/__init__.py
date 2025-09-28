"""
Configuration management
"""

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings


class YNABConfig(BaseSettings):
    """YNAB MCP Server configuration"""
    
    # OAuth settings - these should match the YNAB OAuth app you create
    YNAB_CLIENT_ID: str = "your-ynab-client-id"
    YNAB_CLIENT_SECRET: SecretStr = SecretStr("your-ynab-client-secret") 
    YNAB_BASE_URL: AnyHttpUrl = "http://localhost:8000"
    YNAB_READ_ONLY: bool = False
    
    # API settings
    ynab_api_base_url: str = "https://api.ynab.com/v1"
    request_timeout: int = 30
    max_retries: int = 3
    
    # Server settings
    server_name: str = "YNAB MCP Server"
    server_version: str = "1.0.0"
    
    model_config = {
        "env_prefix": "",  # No prefix since we're using explicit names
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Allow extra fields for backward compatibility
    }


# Global config instance
config = YNABConfig()