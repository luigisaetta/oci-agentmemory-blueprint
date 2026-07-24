"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Safely creates an Oracle Agent Memory store backed by Oracle ADB.
"""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import oracledb
from dotenv import dotenv_values
from oci.config import from_file

from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
OCI_CONFIG_FILE = Path("~/.oci/config")
MODEL_ID = "oci/openai.gpt-oss-120b"
EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"

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


def load_database_settings(
    environment: Mapping[str, str | None] | None = None,
    dotenv_path: Path = ENV_FILE,
) -> dict[str, str]:
    """Load and validate the ADB settings required by the connection pool.

    Args:
        environment: Optional configuration mapping, primarily for tests. When
            omitted, values are loaded from ``dotenv_path``.
        dotenv_path: Path to the local dotenv configuration file.

    Returns:
        A mapping containing the validated database settings.

    Raises:
        ConfigurationError: If a required setting is missing, blank, or if a
            pool-size setting is not a valid positive integer.
    """
    if environment is None:
        environment = dotenv_values(dotenv_path=dotenv_path)

    missing_settings = [
        setting
        for setting in REQUIRED_DATABASE_SETTINGS
        if not (environment.get(setting) or "").strip()
    ]
    if missing_settings:
        raise ConfigurationError(
            "Missing required ADB settings: " + ", ".join(missing_settings)
        )

    settings = {
        setting: (environment[setting] or "").strip()
        for setting in REQUIRED_DATABASE_SETTINGS
    }
    for setting in ("DB_POOL_MIN", "DB_POOL_MAX", "DB_POOL_INCREMENT"):
        try:
            if int(settings[setting]) < 1:
                raise ValueError
        except ValueError as error:
            raise ConfigurationError(
                f"{setting} must be a positive integer."
            ) from error
    if int(settings["DB_POOL_MAX"]) < int(settings["DB_POOL_MIN"]):
        raise ConfigurationError(
            "DB_POOL_MAX must be greater than or equal to DB_POOL_MIN."
        )

    return settings


def create_connection_pool(
    settings: Mapping[str, str] | None = None,
    pool_factory: Callable[..., oracledb.ConnectionPool] | None = None,
) -> oracledb.ConnectionPool:
    """Create an ADB connection pool from validated local settings.

    Args:
        settings: Validated database settings. When omitted, they are loaded
            from the repository-root `.env` file.
        pool_factory: Optional pool factory, used by unit tests.

    Returns:
        An open Oracle Database connection pool.
    """
    if settings is None:
        settings = load_database_settings()
    if pool_factory is None:
        pool_factory = oracledb.create_pool

    return pool_factory(
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


def load_oci_settings(
    config_path: Path = OCI_CONFIG_FILE,
    config_loader: Callable[..., Mapping[str, Any]] | None = None,
) -> Mapping[str, Any]:
    """Load and validate the OCI profile used by the model providers.

    Args:
        config_path: OCI configuration file to load. Home-directory syntax is
            expanded before passing the path to the OCI SDK.
        config_loader: Optional OCI configuration loader, used by unit tests.

    Returns:
        The validated OCI profile mapping.

    Raises:
        ConfigurationError: If the OCI profile omits a required setting.
    """
    if config_loader is None:
        config_loader = from_file
    config = config_loader(file_location=str(config_path.expanduser()))
    missing_settings = [
        setting for setting in REQUIRED_OCI_SETTINGS if not config.get(setting)
    ]
    if missing_settings:
        raise ConfigurationError(
            "Missing required OCI settings: " + ", ".join(missing_settings)
        )
    return config


def create_memory_store(
    connection_pool: oracledb.ConnectionPool, oci_config: Mapping[str, Any]
) -> OracleAgentMemory:
    """Create the configured Oracle Agent Memory store.

    Args:
        connection_pool: Open ADB connection pool used for persistence.
        oci_config: Validated OCI configuration for the embedding and LLM
            providers.

    Returns:
        A configured Oracle Agent Memory instance.
    """
    oci_arguments = {
        "oci_compartment_id": oci_config["compartment_id"],
        "oci_region": oci_config["region"],
        "oci_user": oci_config["user"],
        "oci_fingerprint": oci_config["fingerprint"],
        "oci_tenancy": oci_config["tenancy"],
        "oci_key_file": str(Path(oci_config["key_file"]).expanduser()),
    }
    oci_embedder = Embedder(model=EMBEDDING_MODEL_ID, **oci_arguments)
    oci_llm = Llm(model=MODEL_ID, **oci_arguments)
    return OracleAgentMemory(
        connection=connection_pool,
        embedder=oci_embedder,
        llm=oci_llm,
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id="OAM_",
    )


def main() -> int:
    """Create the memory store and close its temporary ADB connection pool.

    Returns:
        Zero when the store is initialised successfully; otherwise one.
    """
    connection_pool: oracledb.ConnectionPool | None = None
    try:
        oci_config = load_oci_settings()
        connection_pool = create_connection_pool()
        create_memory_store(connection_pool, oci_config)
    except Exception as error:  # The OCI SDK exposes several provider-specific errors.
        print(
            "Agent Memory startup failed "
            f"({type(error).__name__}). Check local ADB and OCI configuration."
        )
        return 1
    finally:
        if connection_pool is not None:
            connection_pool.close()

    print("Successfully connected to Agent Memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
