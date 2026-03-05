"""
集中配置管理：从环境变量读取所有可调参数。
"""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "").strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip()

    DASHSCOPE_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-plus-latest")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080"
    ).split(",")

    @property
    def cors_origins(self) -> list:
        if "*" in self.ALLOWED_ORIGINS:
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS if o.strip()]

    @property
    def api_key(self) -> str:
        return self.DASHSCOPE_API_KEY or self.OPENAI_API_KEY

    @property
    def base_url(self) -> str:
        if self.OPENAI_BASE_URL:
            return self.OPENAI_BASE_URL
        if self.DASHSCOPE_API_KEY:
            return self.DASHSCOPE_BASE
        return ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
