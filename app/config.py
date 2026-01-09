"""Configuration loading for the CleanSlate application."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


def _parse_bool(raw_value: str, key: str) -> bool:
    normalized = str(raw_value).strip().lower()
    truthy = {"1", "true", "yes", "on", "y", "t"}
    falsy = {"0", "false", "no", "off", "n", "f"}

    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    raise ConfigError(f"Invalid boolean for {key}: {raw_value}")


def _get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        if required and default is None:
            raise ConfigError(f"Environment variable {key} is required")
        if default is None:
            raise ConfigError(f"Environment variable {key} is empty")
        return default
    return value.strip()


@dataclass(frozen=True)
class AppConfig:
    daemon_mode: bool
    watch_dir: Path
    output_dir: Path
    rclone_remote_name: str
    rclone_dest_path: str
    firebase_enabled: bool
    firebase_credentials: Optional[Path]
    verbose_logging: bool


_DEFAULTS = {
    "DAEMON_MODE": "true",
    "WATCH_DIR": "/data/watch",
    "OUTPUT_DIR": "/data/clean",
    "RCLONE_REMOTE_NAME": "gdrive",
    "RCLONE_DEST_PATH": "backups",
    "FIREBASE_CREDENTIALS": "/app/firebase-service-account.json",
}


def load_config() -> AppConfig:
    """Load configuration from environment with sensible defaults."""

    daemon_mode_raw = _get_env("DAEMON_MODE", default=_DEFAULTS["DAEMON_MODE"], required=True)
    watch_dir_raw = _get_env("WATCH_DIR", default=_DEFAULTS["WATCH_DIR"], required=True)
    output_dir_raw = _get_env("OUTPUT_DIR", default=_DEFAULTS["OUTPUT_DIR"], required=True)
    rclone_remote_name = _get_env(
        "RCLONE_REMOTE_NAME", default=_DEFAULTS["RCLONE_REMOTE_NAME"], required=True
    )
    rclone_dest_path = _get_env(
        "RCLONE_DEST_PATH", default=_DEFAULTS["RCLONE_DEST_PATH"], required=True
    )
    
    firebase_enabled_raw = _get_env("FIREBASE_ENABLED", default="true", required=False)
    firebase_enabled = _parse_bool(firebase_enabled_raw, "FIREBASE_ENABLED")
    
    verbose_logging_raw = _get_env("VERBOSE_LOGGING", default="false", required=False)
    verbose_logging = _parse_bool(verbose_logging_raw, "VERBOSE_LOGGING")
    
    # Only require Firebase credentials if Firebase is enabled
    firebase_credentials: Optional[Path] = None
    if firebase_enabled:
        firebase_credentials_raw = _get_env(
            "FIREBASE_CREDENTIALS", default=_DEFAULTS["FIREBASE_CREDENTIALS"], required=True
        )
        firebase_credentials = Path(firebase_credentials_raw)

    return AppConfig(
        daemon_mode=_parse_bool(daemon_mode_raw, "DAEMON_MODE"),
        watch_dir=Path(watch_dir_raw),
        output_dir=Path(output_dir_raw),
        rclone_remote_name=rclone_remote_name,
        rclone_dest_path=rclone_dest_path,
        firebase_enabled=firebase_enabled,
        firebase_credentials=firebase_credentials,
        verbose_logging=verbose_logging,
    )
