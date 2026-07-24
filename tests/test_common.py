"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Unit tests for shared ADB and OCI configuration helpers.
"""

# pylint: disable=duplicate-code

from pathlib import Path
from unittest.mock import Mock

import pytest

import common

VALID_DATABASE_SETTINGS = {
    "DB_USER": "demo_user",
    "DB_PWD": "database-password",
    "DB_DSN": "demo_medium",
    "WALLET_DIR": "/safe/local/wallet",
    "WALLET_PWD": "wallet-password",
    "DB_POOL_MIN": "1",
    "DB_POOL_MAX": "5",
    "DB_POOL_INCREMENT": "1",
}
VALID_OCI_SETTINGS = {
    "compartment_id": "ocid1.compartment.oc1..example",
    "region": "eu-frankfurt-1",
    "user": "ocid1.user.oc1..example",
    "fingerprint": "00:11:22:33",
    "tenancy": "ocid1.tenancy.oc1..example",
    "key_file": "~/.oci/oci_api_key.pem",
}


def test_load_database_settings_rejects_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject missing settings and invalid pool sizes before connecting."""
    monkeypatch.setattr(
        common,
        "dotenv_values",
        Mock(return_value=VALID_DATABASE_SETTINGS | {"DB_PWD": ""}),
    )
    with pytest.raises(common.ConfigurationError, match="DB_PWD"):
        common.load_database_settings()

    monkeypatch.setattr(
        common,
        "dotenv_values",
        Mock(return_value=VALID_DATABASE_SETTINGS | {"DB_POOL_MIN": "0"}),
    )
    with pytest.raises(common.ConfigurationError, match="DB_POOL_MIN"):
        common.load_database_settings()


def test_create_connection_pool_uses_oracledb_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create the pool through the Oracle driver with local settings."""
    pool_factory = Mock(return_value=Mock())
    monkeypatch.setattr(
        common, "dotenv_values", Mock(return_value=VALID_DATABASE_SETTINGS)
    )
    monkeypatch.setattr(common.oracledb, "create_pool", pool_factory)

    common.create_connection_pool()

    assert pool_factory.call_args.kwargs == {
        "user": "demo_user",
        "password": "database-password",
        "dsn": "demo_medium",
        "config_dir": "/safe/local/wallet",
        "wallet_location": "/safe/local/wallet",
        "wallet_password": "wallet-password",
        "min": 1,
        "max": 5,
        "increment": 1,
    }


def test_load_oci_settings_expands_path_and_validates_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expand the OCI path and reject incomplete profiles."""
    loader = Mock(return_value=VALID_OCI_SETTINGS)
    monkeypatch.setattr(common, "from_file", loader)

    assert common.load_oci_settings() == VALID_OCI_SETTINGS
    assert loader.call_args.args[0] == str(Path("~/.oci/config").expanduser())

    monkeypatch.setattr(
        common,
        "from_file",
        Mock(return_value=VALID_OCI_SETTINGS | {"compartment_id": ""}),
    )
    with pytest.raises(common.ConfigurationError, match="compartment_id"):
        common.load_oci_settings()
