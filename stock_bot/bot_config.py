"""
Loads and validates a per-bot JSON config file.

Usage:
    cfg = BotConfig.load("configs/bot-1.json")
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


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
    bot_name:      str
    telegram_token: str
    alert_chat_id: str
    database:      str
    logs:          str
    features:      Features = field(default_factory=Features)
    settings:      Settings = field(default_factory=Settings)

    @classmethod
    def load(cls, path: str) -> "BotConfig":
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {path}\n"
                f"Copy configs/bot-1.example.json to {path} and fill in your values."
            )
        with open(config_path) as f:
            data = json.load(f)

        features = Features(**data.pop("features", {}))
        settings = Settings(**data.pop("settings", {}))
        return cls(**data, features=features, settings=settings)
