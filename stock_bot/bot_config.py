"""
Loads and validates a per-bot JSON config file.

Secret values (token, chat ID) use ${ENV_VAR} placeholders in the JSON
and are resolved from environment variables at load time, so config files
are safe to commit to git.

Usage:
    cfg = BotConfig.load("configs/bot-1.json")
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


def _resolve_env(value: str) -> str:
    """Replace ${VAR_NAME} with the corresponding environment variable."""
    def replacer(match):
        var = match.group(1)
        resolved = os.environ.get(var)
        if resolved is None:
            raise EnvironmentError(
                f"Config references ${{{var}}} but that environment variable is not set.\n"
                f"Add it to your .env file."
            )
        return resolved
    return re.sub(r"\$\{([^}]+)\}", replacer, value)


@dataclass
class Features:
    watchlist:    bool = True
    alerts:       bool = True
    price_alerts: bool = True
    holdings:     bool = True
    reports:      bool = True


@dataclass
class Settings:
    alert_cooldown_hours:        int = 2
    check_interval_market_hours: int = 1800
    check_interval_off_hours:    int = 3600


@dataclass
class BotConfig:
    bot_name:       str
    telegram_token: str
    alert_chat_id:  str
    database:       str
    logs:           str
    features:       Features = field(default_factory=Features)
    settings:       Settings = field(default_factory=Settings)

    @classmethod
    def load(cls, path: str) -> "BotConfig":
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {path}\n"
                f"Check that the file exists and the path is correct."
            )
        with open(config_path) as f:
            data = json.load(f)

        # Resolve ${ENV_VAR} placeholders in string fields
        for key in ("telegram_token", "alert_chat_id"):
            if key in data:
                data[key] = _resolve_env(data[key])

        features = Features(**data.pop("features", {}))
        settings = Settings(**data.pop("settings", {}))
        return cls(**data, features=features, settings=settings)
