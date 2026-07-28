"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Unit tests for the customer-support conversation memory example.
"""

import importlib.util
from datetime import datetime
import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
from examples.example02.messages import build_customer_support_messages

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "example02.py"
SPEC = importlib.util.spec_from_file_location("example02", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
example02 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example02)

VALID_OCI_SETTINGS = {
    "compartment_id": "ocid1.compartment.oc1..example",
    "region": "eu-frankfurt-1",
    "user": "ocid1.user.oc1..example",
    "fingerprint": "00:11:22:33",
    "tenancy": "ocid1.tenancy.oc1..example",
    "key_file": "~/.oci/oci_api_key.pem",
}
MEMORY_STORE_ID = "OAM_"


def test_build_customer_support_messages_has_ten_alternating_english_messages() -> None:
    """Build five English customer requests and five support replies."""
    messages = build_customer_support_messages("2026-07-27T10:00:00Z")

    assert len(messages) == 10
    assert [message.role for message in messages] == [
        "user",
        "assistant",
    ] * 5
    assert all(message.content.isascii() for message in messages)
    assert all(message.timestamp == "2026-07-27T10:00:00Z" for message in messages)


def test_create_memory_store_builds_oci_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass OCI values to the embedder, LLM, and memory store."""
    embedder_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(example02, "Embedder", embedder_factory)
    monkeypatch.setattr(example02, "OracleAgentMemory", memory_factory)
    connection_pool = Mock()

    example02.create_memory_store(connection_pool, VALID_OCI_SETTINGS, MEMORY_STORE_ID)

    assert embedder_factory.call_args.kwargs["model"] == example02.EMBEDDING_MODEL_ID
    assert memory_factory.call_args.kwargs["connection"] is connection_pool
    assert memory_factory.call_args.kwargs["memory_store_id"] == MEMORY_STORE_ID


def test_main_persists_conversation_and_closes_pool(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Persist ten timestamped messages and close the pool after success."""
    connection_pool = Mock()
    memory = Mock()
    memory.create_thread.return_value.add_messages.return_value = [
        f"message-{index}" for index in range(10)
    ]
    memory.create_thread.return_value.get_context_card.return_value.content = (
        "compact context"
    )
    monkeypatch.setattr(example02, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example02, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example02, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example02, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example02.LOGGER.name)

    assert example02.main() == 0

    connection_pool.close.assert_called_once_with()
    assert "Created thread:" in caplog.text
    assert "Persisted 10 customer-support messages" in caplog.text
    assert "Generated Context Card: compact context" in caplog.text
    assert "thread_id" not in memory.create_thread.call_args.kwargs
    messages = memory.create_thread.return_value.add_messages.call_args.args[0]
    assert len(messages) == 10
    assert [message.role for message in messages] == ["user", "assistant"] * 5
    assert all(message.timestamp == messages[0].timestamp for message in messages)
    datetime.fromisoformat(messages[0].timestamp.replace("Z", "+00:00"))
    memory.create_thread.return_value.get_context_card.assert_called_once_with(
        max_relevant_results=10,
        min_relevant_results_by_type={
            "preference": 1,
            "guideline": 1,
        },
    )


def test_main_closes_pool_when_message_persistence_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Close the pool and report validation errors without message content."""
    connection_pool = Mock()
    memory = Mock()
    memory.create_thread.return_value.add_messages.side_effect = ValueError()
    monkeypatch.setattr(example02, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example02, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example02, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example02, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example02.LOGGER.name)

    assert example02.main() == 1

    assert "rejected an invalid value" in caplog.text
    assert "My package" not in caplog.text
    connection_pool.close.assert_called_once_with()
