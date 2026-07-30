"""
Author: L. Saetta
Date last modified: 2026-07-30
License: MIT
Description: Shared local OCI and Oracle Autonomous Database configuration helpers.
"""

import os
from pathlib import Path
import re

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
REQUIRED_RESOURCE_PRINCIPAL_SETTINGS = (
    "GENAI_COMPARTMENT_ID",
    "GENAI_REGION",
)
REQUIRED_GENAI_CHAT_SETTINGS = (
    "GENAI_REGION",
    "GENAI_MODEL_ID",
)
MEMORY_STORE_ID_SETTING = "MEMORY_STORE_ID"
MEMORY_STORE_ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,15}")


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


def load_resource_principal_settings() -> dict[str, str]:
    """Load OCI Generative AI settings for Resource Principal authentication.

    Process environment variables take precedence over repository-root `.env`
    values so OCI-managed runtimes can supply deployment configuration.

    Returns:
        The compartment ID and region required by OCI Generative AI providers.

    Raises:
        ConfigurationError: If the compartment ID or region is missing.
    """
    environment = dotenv_values(ENV_FILE)
    settings = {
        name: os.environ.get(name) or environment.get(name) or ""
        for name in REQUIRED_RESOURCE_PRINCIPAL_SETTINGS
    }
    missing_settings = [name for name, value in settings.items() if not value.strip()]
    if missing_settings:
        raise ConfigurationError(
            "Missing required Resource Principal settings: "
            + ", ".join(missing_settings)
        )
    return {
        "compartment_id": settings["GENAI_COMPARTMENT_ID"],
        "region": settings["GENAI_REGION"],
    }


def load_genai_chat_settings() -> dict[str, str]:
    """Load OCI chat-model region and ID from local configuration.

    Process environment values take precedence over repository-root `.env`
    values, allowing an approved deployment environment to override the local
    chatbot settings without embedding them in source code.

    Returns:
        The region and model ID required by the Example 11 LangChain client.

    Raises:
        ConfigurationError: If the configured region or model ID is missing.
    """
    environment = dotenv_values(ENV_FILE)
    settings = {
        name: os.environ.get(name) or environment.get(name) or ""
        for name in REQUIRED_GENAI_CHAT_SETTINGS
    }
    missing_settings = [name for name, value in settings.items() if not value.strip()]
    if missing_settings:
        raise ConfigurationError(
            "Missing required Generative AI settings: " + ", ".join(missing_settings)
        )
    return {
        "region": settings["GENAI_REGION"],
        "model_id": settings["GENAI_MODEL_ID"],
    }


def load_memory_store_id() -> str:
    """Load and validate the shared Oracle Agent Memory store identifier.

    The process environment takes precedence over the repository-root `.env`
    file. The value must meet the Oracle Agent Memory `memory_store_id`
    naming requirements so every example addresses the same managed objects.

    Returns:
        The configured memory store identifier.

    Raises:
        ConfigurationError: If the identifier is missing or has an invalid
            format.
    """
    environment = dotenv_values(ENV_FILE)
    memory_store_id = (
        os.environ.get(MEMORY_STORE_ID_SETTING)
        or environment.get(MEMORY_STORE_ID_SETTING)
        or ""
    ).strip()
    if not memory_store_id:
        raise ConfigurationError(f"Missing required setting: {MEMORY_STORE_ID_SETTING}")
    if not MEMORY_STORE_ID_PATTERN.fullmatch(memory_store_id):
        raise ConfigurationError(
            f"{MEMORY_STORE_ID_SETTING} must start with a letter, contain only "
            "letters, numbers, or underscores, and be at most 16 characters."
        )
    return memory_store_id
