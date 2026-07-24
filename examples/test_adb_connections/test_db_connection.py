"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Safely validates a local Oracle Autonomous Database connection.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import oracledb
from dotenv import dotenv_values

REQUIRED_ENVIRONMENT_VARIABLES = (
    "DB_USER",
    "DB_PWD",
    "WALLET_DIR",
    "WALLET_PWD",
    "DB_DSN",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPOSITORY_ROOT / ".env"


class ConnectionConfigurationError(ValueError):
    """Raised when required ADB connection settings are unavailable."""


@dataclass(frozen=True)
class ADBConnectionConfig:
    """Holds settings required for a wallet-based Oracle ADB connection.

    Attributes:
        user: Oracle database user name.
        password: Password for the database user.
        wallet_directory: Directory containing the extracted ADB wallet files.
        wallet_password: Password assigned when downloading the wallet.
        dsn: ADB service alias or Oracle connection string.
    """

    user: str
    password: str
    wallet_directory: str
    wallet_password: str
    dsn: str

    def as_connect_kwargs(self) -> dict[str, str]:
        """Build safe Oracle Thin-mode connection arguments.

        Returns:
            Keyword arguments accepted by ``oracledb.connect``.
        """
        return {
            "user": self.user,
            "password": self.password,
            "dsn": self.dsn,
            "config_dir": self.wallet_directory,
            "wallet_location": self.wallet_directory,
            "wallet_password": self.wallet_password,
        }


def load_connection_config(
    environment: Mapping[str, str | None] | None = None,
    dotenv_path: Path = DEFAULT_ENV_FILE,
) -> ADBConnectionConfig:
    """Load and validate the required ADB settings from ``.env``.

    Args:
        environment: Optional settings mapping, primarily for programmatic use and
            unit tests. When omitted, settings are read from ``dotenv_path``.
        dotenv_path: Path to the local dotenv file.

    Returns:
        Validated ADB connection settings.

    Raises:
        ConnectionConfigurationError: If one or more required settings are missing
            or blank.
    """
    if environment is None:
        environment = dotenv_values(dotenv_path=dotenv_path)

    missing_variables = [
        variable
        for variable in REQUIRED_ENVIRONMENT_VARIABLES
        if not (environment.get(variable) or "").strip()
    ]
    if missing_variables:
        missing_names = ", ".join(missing_variables)
        raise ConnectionConfigurationError(
            f"Missing required environment variables: {missing_names}."
        )

    return ADBConnectionConfig(
        user=environment["DB_USER"] or "",
        password=environment["DB_PWD"] or "",
        wallet_directory=environment["WALLET_DIR"] or "",
        wallet_password=environment["WALLET_PWD"] or "",
        dsn=environment["DB_DSN"] or "",
    )


def format_connection_header(config: ADBConnectionConfig) -> str:
    """Create a status message that excludes passwords.

    Args:
        config: Validated ADB connection settings.

    Returns:
        Human-readable connection details that are safe to print.
    """
    return "\n".join(
        (
            "Oracle ADB connection parameters:",
            f"  DB_USER: {config.user}",
            f"  DB_DSN: {config.dsn}",
            f"  WALLET_DIR: {config.wallet_directory}",
        )
    )


def check_connection(
    environment: Mapping[str, str | None] | None = None,
    connector: Callable[..., Any] = oracledb.connect,
    emit: Callable[[str], None] = print,
) -> int:
    """Connect to ADB, run a validation query, and report a safe status.

    Args:
        environment: Optional settings mapping. When omitted, values are loaded
            from the repository-root ``.env`` file.
        connector: Callable compatible with ``oracledb.connect``.
        emit: Function used to output messages to the command-line caller.

    Returns:
        ``0`` on success, ``1`` for a connection or validation failure, or ``2``
        when configuration is incomplete.
    """
    try:
        config = load_connection_config(environment=environment)
    except ConnectionConfigurationError as error:
        emit(f"ADB connection configuration error: {error}")
        return 2

    emit(format_connection_header(config))
    connection = None
    try:
        connection = connector(**config.as_connect_kwargs())
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM dual")
            cursor.fetchone()
    except (oracledb.Error, OSError) as error:
        emit(
            "ADB connection check failed "
            f"({type(error).__name__}). Check DB_USER, DB_PWD, WALLET_DIR, "
            "WALLET_PWD, and DB_DSN."
        )
        return 1
    finally:
        if connection is not None:
            connection.close()

    emit("ADB connection OK.")
    return 0


def main() -> int:
    """Run the ADB connectivity check from the command line.

    Returns:
        Process exit status from :func:`check_connection`.
    """
    return check_connection()


if __name__ == "__main__":
    raise SystemExit(main())
