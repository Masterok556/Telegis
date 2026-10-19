from dataclasses import dataclass, field
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = ROOT / "data"
    static_dir: Path = ROOT / "static"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = field(default="", repr=False)
    llm_model: str = ""
    llm_reasoning_effort: str = ""
    llm_max_tokens: int = 1200
    llm_timeout_seconds: float = 15
    llm_json_mode: bool = True
    cors_origins: tuple[str, ...] = ()

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model and self.llm_base_url)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(ROOT / ".env", override=False)
        base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
        parsed = urlsplit(base)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if not parsed.hostname or (parsed.scheme != "https" and not local_http) or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("LLM_BASE_URL должен быть HTTPS URL без ключей; HTTP разрешён только для localhost")
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "15"))
        if not 1 <= timeout <= 45:
            raise ValueError("LLM_TIMEOUT_SECONDS должен быть от 1 до 45")
        effort = os.getenv("LLM_REASONING_EFFORT", "").strip()
        if effort not in {"", "none", "minimal", "low", "medium", "high", "xhigh", "max"}:
            raise ValueError("Некорректное значение LLM_REASONING_EFFORT")
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1200"))
        if not 128 <= max_tokens <= 4096:
            raise ValueError("LLM_MAX_TOKENS должен быть от 128 до 4096")
        return cls(
            llm_base_url=base,
            llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
            llm_model=os.getenv("LLM_MODEL", "").strip(),
            llm_reasoning_effort=effort,
            llm_max_tokens=max_tokens,
            llm_timeout_seconds=timeout,
            llm_json_mode=os.getenv("LLM_JSON_MODE", "true").lower() in {"1", "true", "yes"},
            cors_origins=tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()),
        )
