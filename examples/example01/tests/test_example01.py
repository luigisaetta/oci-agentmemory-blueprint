"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Unit tests for the safe Oracle Agent Memory startup example.
"""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import oci.config
import oracledb
import pytest

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "example01.py"
SPEC = importlib.util.spec_from_file_location("example01", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
example01 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example01)

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


def test_import_does_not_open_connections_or_load_oci_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep importing the example free of configuration and connection side effects."""
    pool_factory = Mock()
    config_loader = Mock()
    monkeypatch.setattr(oracledb, "create_pool", pool_factory)
    monkeypatch.setattr(oci.config, "from_file", config_loader)
    import_spec = importlib.util.spec_from_file_location(
        "example01_import_check", EXAMPLE_PATH
    )
    assert import_spec is not None and import_spec.loader is not None
    imported_module = importlib.util.module_from_spec(import_spec)

    import_spec.loader.exec_module(imported_module)

    pool_factory.assert_not_called()
    config_loader.assert_not_called()


def test_load_database_settings_rejects_missing_values() -> None:
    """Report missing setting names without revealing their values."""
    incomplete_settings = VALID_DATABASE_SETTINGS | {"DB_PWD": ""}

    with pytest.raises(example01.ConfigurationError, match="DB_PWD"):
        example01.load_database_settings(environment=incomplete_settings)


def test_load_database_settings_validates_pool_sizes() -> None:
    """Reject non-positive pool sizes before connecting to the database."""
    invalid_settings = VALID_DATABASE_SETTINGS | {"DB_POOL_MIN": "0"}

    with pytest.raises(example01.ConfigurationError, match="DB_POOL_MIN"):
        example01.load_database_settings(environment=invalid_settings)

    assert example01.load_database_settings(environment=VALID_DATABASE_SETTINGS) == (
        VALID_DATABASE_SETTINGS
    )


def test_load_oci_settings_expands_home_directory() -> None:
    """Pass an expanded OCI config path to the OCI SDK boundary."""
    loader = Mock(return_value=VALID_OCI_SETTINGS)

    result = example01.load_oci_settings(config_loader=loader)

    assert result == VALID_OCI_SETTINGS
    assert loader.call_args.kwargs["file_location"] == str(
        Path("~/.oci/config").expanduser()
    )


def test_load_oci_settings_rejects_missing_profile_values() -> None:
    """List absent OCI profile keys without exposing configuration values."""
    incomplete_settings = VALID_OCI_SETTINGS | {"compartment_id": ""}

    with pytest.raises(example01.ConfigurationError, match="compartment_id"):
        example01.load_oci_settings(
            config_loader=Mock(return_value=incomplete_settings)
        )


def test_create_connection_pool_uses_validated_settings() -> None:
    """Pass wallet and pool settings to the database factory."""
    pool_factory = Mock(return_value=Mock())

    example01.create_connection_pool(
        settings=VALID_DATABASE_SETTINGS, pool_factory=pool_factory
    )

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


def test_create_connection_pool_loads_default_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the default setting loader and Oracle pool factory when omitted."""
    pool_factory = Mock(return_value=Mock())
    monkeypatch.setattr(
        example01, "load_database_settings", lambda: VALID_DATABASE_SETTINGS
    )
    monkeypatch.setattr(example01.oracledb, "create_pool", pool_factory)

    example01.create_connection_pool()

    assert pool_factory.call_count == 1


def test_load_oci_settings_uses_default_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the OCI SDK loader when no test loader is supplied."""
    loader = Mock(return_value=VALID_OCI_SETTINGS)
    monkeypatch.setattr(example01, "from_file", loader)

    example01.load_oci_settings()

    assert loader.call_count == 1


def test_create_memory_store_builds_oci_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass validated OCI parameters to the embedder and LLM providers."""
    embedder = Mock()
    llm = Mock()
    memory_store = Mock()
    embedder_factory = Mock(return_value=embedder)
    llm_factory = Mock(return_value=llm)
    memory_factory = Mock(return_value=memory_store)
    monkeypatch.setattr(example01, "Embedder", embedder_factory)
    monkeypatch.setattr(example01, "Llm", llm_factory)
    monkeypatch.setattr(example01, "OracleAgentMemory", memory_factory)
    connection_pool = Mock()

    result = example01.create_memory_store(connection_pool, VALID_OCI_SETTINGS)

    assert result is memory_store
    provider_arguments = {
        "oci_compartment_id": VALID_OCI_SETTINGS["compartment_id"],
        "oci_region": VALID_OCI_SETTINGS["region"],
        "oci_user": VALID_OCI_SETTINGS["user"],
        "oci_fingerprint": VALID_OCI_SETTINGS["fingerprint"],
        "oci_tenancy": VALID_OCI_SETTINGS["tenancy"],
        "oci_key_file": str(Path(VALID_OCI_SETTINGS["key_file"]).expanduser()),
    }
    embedder_factory.assert_called_once_with(
        model=example01.EMBEDDING_MODEL_ID, **provider_arguments
    )
    llm_factory.assert_called_once_with(model=example01.MODEL_ID, **provider_arguments)
    memory_factory.assert_called_once_with(
        connection=connection_pool,
        embedder=embedder,
        llm=llm,
        schema_policy=example01.SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id="OAM_",
    )


def test_main_closes_pool_after_successful_initialisation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Close the ADB pool after the memory store has been created."""
    connection_pool = Mock()
    monkeypatch.setattr(example01, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example01, "create_connection_pool", lambda: connection_pool)
    memory_factory = Mock()
    monkeypatch.setattr(example01, "create_memory_store", memory_factory)

    assert example01.main() == 0

    memory_factory.assert_called_once_with(connection_pool, VALID_OCI_SETTINGS)
    connection_pool.close.assert_called_once_with()
    assert "Successfully connected to Agent Memory." in capsys.readouterr().out


def test_main_closes_pool_after_startup_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Close the ADB pool and hide error details when startup fails."""
    connection_pool = Mock()
    monkeypatch.setattr(example01, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example01, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(
        example01,
        "create_memory_store",
        Mock(side_effect=RuntimeError("sensitive internal detail")),
    )

    assert example01.main() == 1

    connection_pool.close.assert_called_once_with()
    output = capsys.readouterr().out
    assert "RuntimeError" in output
    assert "sensitive internal detail" not in output
