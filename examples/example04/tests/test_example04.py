"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Unit tests for the destructive Agent Memory schema recreation example.
"""

import importlib.util
import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "example04.py"
SPEC = importlib.util.spec_from_file_location("example04", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
example04 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example04)

VALID_OCI_SETTINGS = {
    "compartment_id": "ocid1.compartment.oc1..example",
    "region": "eu-frankfurt-1",
    "user": "ocid1.user.oc1..example",
    "fingerprint": "00:11:22:33",
    "tenancy": "ocid1.tenancy.oc1..example",
    "key_file": "~/.oci/oci_api_key.pem",
}
MEMORY_STORE_ID = "OAM_"


def test_create_recreated_memory_store_uses_recreate_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure the existing store ID for destructive recreation."""
    embedder_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(example04, "Embedder", embedder_factory)
    monkeypatch.setattr(example04, "OracleAgentMemory", memory_factory)
    connection_pool = Mock()

    example04.create_recreated_memory_store(
        connection_pool, VALID_OCI_SETTINGS, MEMORY_STORE_ID
    )

    assert embedder_factory.call_args.kwargs["model"] == example04.EMBEDDING_MODEL_ID
    assert memory_factory.call_args.kwargs["connection"] is connection_pool
    assert memory_factory.call_args.kwargs["memory_store_id"] == MEMORY_STORE_ID
    assert (
        memory_factory.call_args.kwargs["schema_policy"]
        == example04.SchemaPolicy.RECREATE
    )
    extraction_config = memory_factory.call_args.kwargs["memory_extraction_config"]
    assert extraction_config.extract_memories is False


def test_main_closes_memory_and_pool_on_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Close resources whether schema recreation succeeds or fails."""
    connection_pool = Mock()
    memory = Mock()
    monkeypatch.setattr(example04, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example04, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example04, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(
        example04, "create_recreated_memory_store", Mock(return_value=memory)
    )
    caplog.set_level(logging.INFO, logger=example04.LOGGER.name)

    assert example04.main() == 0
    memory.close.assert_called_once_with()
    connection_pool.close.assert_called_once_with()
    assert "permanently deleted" in caplog.text
    assert "Recreated managed Agent Memory objects" in caplog.text

    connection_pool.reset_mock()
    monkeypatch.setattr(
        example04,
        "create_recreated_memory_store",
        Mock(side_effect=RuntimeError("sensitive detail")),
    )

    assert example04.main() == 1
    memory.close.assert_called_once_with()
    connection_pool.close.assert_called_once_with()
    assert "RuntimeError: sensitive detail" in caplog.text
