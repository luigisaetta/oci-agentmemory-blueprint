"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Shared local OCI and Oracle Autonomous Database configuration helpers.
"""

from pathlib import Path

import oracledb
from dotenv import dotenv_values
from oci.config import from_file

ENV_FILE = Path(__file__).resolve().parent / ".env"
OCI_CONFIG_FILE = Path("~/.oci/config")
REQUIRED_DATABASE_SETTINGS = (
    "DB_USER",
    "DB_PWD",
    "DB_DSN",
    "WALLET_DIR",
    "WALLET_PWD",
    "DB_POOL_MIN",
    "DB_POOL_MAX",
    "DB_POOL_INCREMENT",
)
REQUIRED_OCI_SETTINGS = (
    "compartment_id",
    "region",
    "user",
    "fingerprint",
    "tenancy",
    "key_file",
)


class ConfigurationError(ValueError):
    """Raised when local ADB or OCI configuration is incomplete."""


def load_database_settings() -> dict[str, str]:
    """Load and validate ADB settings from the repository-root `.env` file.

    Returns:
        The validated settings required to create the ADB connection pool.

    Raises:
        ConfigurationError: If a setting is missing or a pool size is invalid.
    """
    environment = dotenv_values(ENV_FILE)
    missing_settings = [
        name
        for name in REQUIRED_DATABASE_SETTINGS
        if not (environment.get(name) or "").strip()
    ]
    if missing_settings:
        raise ConfigurationError(
            "Missing required ADB settings: " + ", ".join(missing_settings)
        )

    settings = {name: (environment[name] or "") for name in REQUIRED_DATABASE_SETTINGS}
    for name in ("DB_POOL_MIN", "DB_POOL_MAX", "DB_POOL_INCREMENT"):
        if not settings[name].isdigit() or int(settings[name]) < 1:
            raise ConfigurationError(f"{name} must be a positive integer.")
    if int(settings["DB_POOL_MAX"]) < int(settings["DB_POOL_MIN"]):
        raise ConfigurationError(
            "DB_POOL_MAX must be greater than or equal to DB_POOL_MIN."
        )
    return settings


def create_connection_pool() -> oracledb.ConnectionPool:
    """Create an ADB connection pool using the validated local settings.

    Returns:
        An open Oracle Database connection pool.
    """
    settings = load_database_settings()
    return oracledb.create_pool(
        user=settings["DB_USER"],
        password=settings["DB_PWD"],
        dsn=settings["DB_DSN"],
        config_dir=settings["WALLET_DIR"],
        wallet_location=settings["WALLET_DIR"],
        wallet_password=settings["WALLET_PWD"],
        min=int(settings["DB_POOL_MIN"]),
        max=int(settings["DB_POOL_MAX"]),
        increment=int(settings["DB_POOL_INCREMENT"]),
    )


def load_oci_settings() -> dict[str, str]:
    """Load and validate the OCI profile used by model providers.

    Returns:
        The OCI profile values required to configure model providers.

    Raises:
        ConfigurationError: If a required OCI profile setting is missing.
    """
    config = from_file(str(OCI_CONFIG_FILE.expanduser()))
    missing_settings = [name for name in REQUIRED_OCI_SETTINGS if not config.get(name)]
    if missing_settings:
        raise ConfigurationError(
            "Missing required OCI settings: " + ", ".join(missing_settings)
        )
    return {name: config[name] for name in REQUIRED_OCI_SETTINGS}
