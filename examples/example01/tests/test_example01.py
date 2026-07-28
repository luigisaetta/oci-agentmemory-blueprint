"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Unit tests for the Oracle Agent Memory startup example.
"""

import importlib.util
from datetime import datetime
import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "example01.py"
SPEC = importlib.util.spec_from_file_location("example01", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
example01 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example01)

VALID_OCI_SETTINGS = {
    "compartment_id": "ocid1.compartment.oc1..example",
    "region": "eu-frankfurt-1",
    "user": "ocid1.user.oc1..example",
    "fingerprint": "00:11:22:33",
    "tenancy": "ocid1.tenancy.oc1..example",
    "key_file": "~/.oci/oci_api_key.pem",
}
MEMORY_STORE_ID = "OAM_"


def test_create_memory_store_builds_oci_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass OCI values to the embedder, LLM, and memory store."""
    embedder_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(example01, "Embedder", embedder_factory)
    monkeypatch.setattr(example01, "OracleAgentMemory", memory_factory)
    connection_pool = Mock()

    example01.create_memory_store(connection_pool, VALID_OCI_SETTINGS, MEMORY_STORE_ID)

    assert embedder_factory.call_args.kwargs["model"] == example01.EMBEDDING_MODEL_ID
    assert memory_factory.call_args.kwargs["connection"] is connection_pool
    assert memory_factory.call_args.kwargs["memory_store_id"] == MEMORY_STORE_ID


def test_main_closes_pool_on_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Close the pool regardless of the memory-store startup result."""
    connection_pool = Mock()
    memory = Mock()
    memory.create_thread.return_value.add_messages.return_value = [
        "message-1",
        "message-2",
    ]
    monkeypatch.setattr(example01, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example01, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example01, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example01, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example01.LOGGER.name)

    assert example01.main() == 0
    connection_pool.close.assert_called_once_with()
    assert "Successfully connected" in caplog.text
    assert "Created thread:" in caplog.text
    assert "thread_id" not in memory.create_thread.call_args.kwargs
    added_messages = memory.create_thread.return_value.add_messages.call_args.args[0]
    timestamps = [added_messages[0].timestamp, added_messages[1]["timestamp"]]
    assert timestamps[0] == timestamps[1]
    assert timestamps[0].endswith("Z")
    datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))

    connection_pool.reset_mock()
    monkeypatch.setattr(
        example01,
        "create_memory_store",
        Mock(side_effect=RuntimeError("sensitive detail")),
    )
    assert example01.main() == 1
    connection_pool.close.assert_called_once_with()
    assert "RuntimeError: sensitive detail" in caplog.text


def test_main_explains_value_errors_when_adding_messages(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Explain how to correct Agent Memory input validation failures."""
    connection_pool = Mock()
    memory = Mock()
    memory.create_thread.return_value.add_messages.side_effect = ValueError()
    monkeypatch.setattr(example01, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example01, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example01, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example01, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example01.LOGGER.name)

    assert example01.main() == 1

    assert "rejected an invalid value" in caplog.text
    assert "thread-message input" in caplog.text
    assert "Stack trace:" in caplog.text
    connection_pool.close.assert_called_once_with()


def test_main_explains_thread_id_collision_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Explain how to correct thread-creation validation failures."""
    connection_pool = Mock()
    memory = Mock()
    memory.create_thread.side_effect = ValueError()
    monkeypatch.setattr(example01, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example01, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example01, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example01, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example01.LOGGER.name)

    assert example01.main() == 1

    assert "rejected an invalid value" in caplog.text
    connection_pool.close.assert_called_once_with()
