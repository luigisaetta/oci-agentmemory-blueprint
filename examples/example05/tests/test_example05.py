"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Unit tests for the user-scoped Agent Memory search example.
"""

import importlib.util
import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from examples.example05.messages import build_user1_messages, build_user2_messages

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "example05.py"
SPEC = importlib.util.spec_from_file_location("example05", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
example05 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example05)

VALID_OCI_SETTINGS = {
    "compartment_id": "ocid1.compartment.oc1..example",
    "region": "eu-frankfurt-1",
    "user": "ocid1.user.oc1..example",
    "fingerprint": "00:11:22:33",
    "tenancy": "ocid1.tenancy.oc1..example",
    "key_file": "~/.oci/oci_api_key.pem",
}
MEMORY_STORE_ID = "OAM"


def test_message_builders_create_ten_overlapping_customer_support_messages() -> None:
    """Create two timestamped conversations with similar search language."""
    timestamp = "2026-07-28T10:00:00Z"
    user1_messages = build_user1_messages(timestamp)
    user2_messages = build_user2_messages(timestamp)

    assert len(user1_messages) == 5
    assert len(user2_messages) == 5
    assert [message.role for message in user1_messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
    ]
    assert [message.role for message in user2_messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
    ]
    assert all(
        message.timestamp == timestamp for message in user1_messages + user2_messages
    )
    assert "tracking update" in user1_messages[0].content
    assert "tracking update" in user2_messages[0].content


def test_create_memory_store_disables_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure embedding retrieval without derived-memory extraction."""
    embedder_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(example05, "Embedder", embedder_factory)
    monkeypatch.setattr(example05, "OracleAgentMemory", memory_factory)

    example05.create_memory_store(Mock(), VALID_OCI_SETTINGS, MEMORY_STORE_ID)

    assert embedder_factory.call_args.kwargs["model"] == example05.EMBEDDING_MODEL_ID
    assert memory_factory.call_args.kwargs["memory_store_id"] == MEMORY_STORE_ID
    assert (
        memory_factory.call_args.kwargs["schema_policy"]
        == example05.SchemaPolicy.CREATE_IF_NECESSARY
    )
    assert (
        memory_factory.call_args.kwargs["memory_extraction_config"].extract_memories
        is False
    )


def test_main_persists_two_scopes_and_runs_three_searches(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Reject unscoped search and run the same query for each user scope."""
    connection_pool = Mock()
    memory = Mock()
    user1_thread = Mock()
    user2_thread = Mock()
    user1_thread.add_messages.return_value = [f"user1-{index}" for index in range(5)]
    user2_thread.add_messages.return_value = [f"user2-{index}" for index in range(5)]
    memory.create_thread.side_effect = [user1_thread, user2_thread]
    memory.search.side_effect = [ValueError(), [], []]
    monkeypatch.setattr(example05, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example05, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example05, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example05, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example05.LOGGER.name)

    assert example05.main() == 0

    assert [call.kwargs for call in memory.create_thread.call_args_list] == [
        {"user_id": "user1", "agent_id": example05.AGENT_ID},
        {"user_id": "user2", "agent_id": example05.AGENT_ID},
    ]
    assert len(user1_thread.add_messages.call_args.args[0]) == 5
    assert len(user2_thread.add_messages.call_args.args[0]) == 5
    inserted_at = user1_thread.add_messages.call_args.args[0][0].timestamp
    assert inserted_at == user2_thread.add_messages.call_args.args[0][0].timestamp
    datetime.fromisoformat(inserted_at.replace("Z", "+00:00"))
    assert memory.search.call_args_list[0].args == (example05.QUERY,)
    assert memory.search.call_args_list[0].kwargs == {
        "record_types": ["message"],
        "max_results": example05.MAX_RESULTS,
    }
    for call, user_id in zip(memory.search.call_args_list[1:], ["user1", "user2"]):
        assert call.args == (example05.QUERY,)
        assert call.kwargs == {
            "user_id": user_id,
            "record_types": ["message"],
            "max_results": example05.MAX_RESULTS,
        }
    assert "Unscoped client search was rejected" in caplog.text
    assert f"Running message search query: {example05.QUERY}" in caplog.text
    connection_pool.close.assert_called_once_with()


def test_main_closes_pool_when_scoped_search_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Close the pool and report retrieval errors without message content."""
    connection_pool = Mock()
    memory = Mock()
    memory.create_thread.return_value.add_messages.return_value = ["message"] * 5
    memory.search.side_effect = [ValueError(), RuntimeError()]
    monkeypatch.setattr(example05, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example05, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example05, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example05, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example05.LOGGER.name)

    assert example05.main() == 1

    assert "scoped-search example failed (RuntimeError)" in caplog.text
    connection_pool.close.assert_called_once_with()
