import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        self.moonshot_api_key: str = os.getenv("MOONSHOT_API_KEY", "")
        self.moonshot_base_url: str = os.getenv(
            "MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"
        )
        self.redis_host: str = os.getenv("REDIS_HOST", "localhost")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self) -> None:
        """Validate required settings."""
        if not self.moonshot_api_key:
            raise ValueError(
                "MOONSHOT_API_KEY is required. Get one from https://platform.moonshot.ai/"
            )


settings = Settings()

