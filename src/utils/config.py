"""Configuration management for Trading Analyzer.

Loads and validates config from YAML files. Provides defaults for missing values.
"""

from pathlib import Path
from typing import Any, Optional

import yaml


# Default configuration values
DEFAULTS = {
    "models": {
        "haiku": {
            "model_id": "claude-3-5-haiku-20241022",
            "max_tokens": 4096,
            "temperature": 0.0,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.005,
        },
        "sonnet": {
            "model_id": "claude-sonnet-4-5-20250929",
            "max_tokens": 8192,
            "temperature": 0.0,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
        },
        "opus": {
            "model_id": "claude-opus-4-6",
            "max_tokens": 16384,
            "temperature": 0.0,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
        },
    },
    "analysis": {
        "gap": {"min_gap_pct": 2.0, "lookback_bars": 100},
        "support_resistance": {
            "lookback_bars": 100,
            "swing_window": 5,
            "sensitivity": "medium",
            "round_number_interval": 10,
        },
        "supply_demand": {
            "min_move_pct": 3.0,
            "consolidation_bars": 5,
            "volume_threshold": 1.5,
        },
    },
    "data": {
        "cache_dir": "data/cache",
        "reports_dir": "data/reports",
        "samples_dir": "data/samples",
        "cache_ttl_hours": 24,
    },
    "logging": {
        "level": "INFO",
        "file": "trading_analyzer.log",
        "console": True,
    },
}


class Config:
    """Configuration manager that loads from YAML with defaults."""

    def __init__(
        self,
        config_path: str = "config/config.yaml",
        api_keys_path: Optional[str] = "config/api_keys.yaml",
    ):
        self._config = self._deep_merge(DEFAULTS, {})
        self._api_keys: dict = {}

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                user_config = yaml.safe_load(f) or {}
            self._config = self._deep_merge(DEFAULTS, user_config)

        if api_keys_path:
            keys_file = Path(api_keys_path)
            if keys_file.exists():
                with open(keys_file) as f:
                    self._api_keys = yaml.safe_load(f) or {}

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Recursively merge override into base, preferring override values."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a config value by dot-separated path.

        Example: config.get("models.haiku.model_id")
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_api_key(self, service: str) -> Optional[str]:
        """Get an API key for a service."""
        if service in self._api_keys:
            key_data = self._api_keys[service]
            if isinstance(key_data, dict):
                return key_data.get("api_key")
            return key_data
        return None

    def get_model_config(self, model_name: str) -> dict:
        """Get full config for a model tier (haiku, sonnet, opus)."""
        return self.get(f"models.{model_name}", {})

    @property
    def raw(self) -> dict:
        """Access raw config dict."""
        return self._config

    def validate(self) -> list[str]:
        """Validate config and return list of warnings/errors."""
        errors = []
        for model in ["haiku", "sonnet", "opus"]:
            mc = self.get(f"models.{model}")
            if not mc:
                errors.append(f"Missing model config for {model}")
            elif not mc.get("model_id"):
                errors.append(f"Missing model_id for {model}")
        return errors
