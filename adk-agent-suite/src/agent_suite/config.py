"""Configuration is loaded at the entry point, never by importing an agent."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mode: str = "demo"
    model: str = "gemini-flash-latest"
    database_path: str = "data/suite.db"
    database_url: str = ""
    session_database_url: str = "sqlite+aiosqlite:///data/sessions.db"
    workspace_root: Path = Path("examples")
    catalog_mcp_url: str = ""
    cli_binary: str = "gemini"
    cli_timeout: int = 90
    review_test_mode: str = "skip"
    concurrency: int = 4
    request_timeout: int = 180

    @classmethod
    def from_env(cls, mode: str | None = None) -> "Settings":
        load_dotenv(override=False)
        settings = cls(
            mode=mode or os.getenv("AGENT_MODE", "demo"),
            model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
            database_path=os.getenv("DATABASE_PATH", "data/suite.db"),
            database_url=os.getenv("DATABASE_URL", ""),
            session_database_url=os.getenv(
                "SESSION_DATABASE_URL", "sqlite+aiosqlite:///data/sessions.db"
            ),
            workspace_root=Path(os.getenv("WORKSPACE_ROOT", "examples")).resolve(),
            catalog_mcp_url=os.getenv("CATALOG_MCP_URL", ""),
            cli_binary=os.getenv("GEMINI_CLI_BINARY", "gemini"),
            cli_timeout=int(os.getenv("GEMINI_CLI_TIMEOUT", "90")),
            review_test_mode=os.getenv("REVIEW_TEST_MODE", "skip"),
            concurrency=int(os.getenv("SUITE_CONCURRENCY", "4")),
            request_timeout=int(os.getenv("SUITE_REQUEST_TIMEOUT", "180")),
        )
        if settings.mode not in {"demo", "live"}:
            raise ValueError("AGENT_MODE must be demo or live")
        if settings.review_test_mode not in {"skip", "docker", "trusted"}:
            raise ValueError("REVIEW_TEST_MODE must be skip, docker, or trusted")
        if not 1 <= settings.cli_timeout <= 180 or not 1 <= settings.concurrency <= 32:
            raise ValueError("Invalid timeout or concurrency")
        return settings


def api_identities() -> dict[str, str]:
    tokens = json.loads(os.getenv("API_TOKENS", "{}"))
    if not isinstance(tokens, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) or len(k) < 24 or not v
        for k, v in tokens.items()
    ):
        raise ValueError("API_TOKENS must map tokens (24+ characters) to customer IDs")
    return tokens
