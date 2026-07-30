"""
Author: L. Saetta
Date last modified: 2026-07-30
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
VALID_RESOURCE_PRINCIPAL_SETTINGS = {
    "GENAI_COMPARTMENT_ID": "ocid1.compartment.oc1..example",
    "GENAI_REGION": "eu-frankfurt-1",
}
VALID_GENAI_CHAT_SETTINGS = {
    "GENAI_REGION": "eu-frankfurt-1",
    "GENAI_MODEL_ID": "meta.llama-3.3-70b-instruct",
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


def test_load_resource_principal_settings_prefers_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load non-secret OCI settings without an OCI API-key profile."""
    monkeypatch.setattr(
        common, "dotenv_values", Mock(return_value=VALID_RESOURCE_PRINCIPAL_SETTINGS)
    )
    monkeypatch.setenv("GENAI_REGION", "us-chicago-1")

    assert common.load_resource_principal_settings() == {
        "compartment_id": "ocid1.compartment.oc1..example",
        "region": "us-chicago-1",
    }

    monkeypatch.delenv("GENAI_REGION")
    monkeypatch.setattr(common, "dotenv_values", Mock(return_value={}))
    with pytest.raises(common.ConfigurationError, match="GENAI_COMPARTMENT_ID"):
        common.load_resource_principal_settings()


def test_load_genai_chat_settings_requires_model_and_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load the chatbot model configuration from environment or `.env`."""
    monkeypatch.setattr(
        common, "dotenv_values", Mock(return_value=VALID_GENAI_CHAT_SETTINGS)
    )
    monkeypatch.setenv("GENAI_MODEL_ID", "meta.llama-4-scout-17b-16e-instruct")

    assert common.load_genai_chat_settings() == {
        "region": "eu-frankfurt-1",
        "model_id": "meta.llama-4-scout-17b-16e-instruct",
    }

    monkeypatch.delenv("GENAI_MODEL_ID")
    monkeypatch.setattr(common, "dotenv_values", Mock(return_value={}))
    with pytest.raises(common.ConfigurationError, match="GENAI_REGION"):
        common.load_genai_chat_settings()


def test_load_memory_store_id_prefers_environment_and_validates_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load one shared store ID and reject invalid managed-object names."""
    monkeypatch.setattr(
        common, "dotenv_values", Mock(return_value={"MEMORY_STORE_ID": "OAM_"})
    )
    monkeypatch.setenv("MEMORY_STORE_ID", "TEAM_MEMORY_1")

    assert common.load_memory_store_id() == "TEAM_MEMORY_1"

    monkeypatch.setenv("MEMORY_STORE_ID", "1_invalid")
    with pytest.raises(common.ConfigurationError, match="must start with a letter"):
        common.load_memory_store_id()

    monkeypatch.delenv("MEMORY_STORE_ID")
    monkeypatch.setattr(common, "dotenv_values", Mock(return_value={}))
    with pytest.raises(common.ConfigurationError, match="Missing required setting"):
        common.load_memory_store_id()
