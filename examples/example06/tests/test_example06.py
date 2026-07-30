"""
Author: L. Saetta
Date last modified: 2026-07-30
License: MIT
Description: Unit tests for the user-scoped Agent Memory thread-listing example.
"""

# pylint: disable=protected-access

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "example06.py"
SPEC = importlib.util.spec_from_file_location("example06", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
example06 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example06)

VALID_OCI_SETTINGS = {
    "compartment_id": "ocid1.compartment.oc1..example",
    "region": "eu-frankfurt-1",
    "user": "ocid1.user.oc1..example",
    "fingerprint": "00:11:22:33",
    "tenancy": "ocid1.tenancy.oc1..example",
    "key_file": "~/.oci/oci_api_key.pem",
}
MEMORY_STORE_ID = "OAM"


def test_list_populated_threads_uses_workaround_and_recent_activity_order() -> None:
    """Discover message-bearing threads and order them by newest message."""
    client = Mock()
    client._store.list.return_value = [
        SimpleNamespace(thread_id="thread-a", timestamp="2026-07-30T10:00:00Z"),
        SimpleNamespace(thread_id="thread-b", timestamp="2026-07-30T11:00:00Z"),
        SimpleNamespace(thread_id=None, timestamp="2026-07-30T12:00:00Z"),
        SimpleNamespace(thread_id="thread-a", timestamp="2026-07-30T13:00:00Z"),
    ]

    activities = example06.list_populated_threads(client, "user1")

    client._store.list.assert_called_once_with(
        record_type="message", user_id="user1", limit=None
    )
    assert activities == [
        example06.ThreadActivity("thread-a", "2026-07-30T13:00:00Z", 2),
        example06.ThreadActivity("thread-b", "2026-07-30T11:00:00Z", 1),
    ]


def test_list_populated_threads_resolves_same_timestamp_by_thread_id() -> None:
    """Keep tied latest-message timestamps deterministic."""
    client = Mock()
    client._store.list.return_value = [
        SimpleNamespace(thread_id="thread-z", timestamp="2026-07-30T10:00:00Z"),
        SimpleNamespace(thread_id="thread-a", timestamp="2026-07-30T10:00:00Z"),
    ]

    activities = example06.list_populated_threads(client, "user1")

    assert [activity.thread_id for activity in activities] == ["thread-a", "thread-z"]


def test_list_populated_threads_returns_empty_list_without_messages() -> None:
    """Report no threads when the selected user has no message records."""
    client = Mock()
    client._store.list.return_value = []

    assert example06.list_populated_threads(client, "user1") == []


def test_create_memory_store_disables_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure retrieval without derived-memory extraction."""
    embedder_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(example06, "Embedder", embedder_factory)
    monkeypatch.setattr(example06, "OracleAgentMemory", memory_factory)

    example06.create_memory_store(Mock(), VALID_OCI_SETTINGS, MEMORY_STORE_ID)

    assert embedder_factory.call_args.kwargs["model"] == example06.EMBEDDING_MODEL_ID
    assert memory_factory.call_args.kwargs["memory_store_id"] == MEMORY_STORE_ID
    assert (
        memory_factory.call_args.kwargs["schema_policy"]
        == example06.SchemaPolicy.CREATE_IF_NECESSARY
    )
    assert (
        memory_factory.call_args.kwargs["memory_extraction_config"].extract_memories
        is False
    )


def test_parse_arguments_uses_default_and_accepts_user_scope() -> None:
    """Provide a safe default while allowing an explicit scoped user ID."""
    assert example06.parse_arguments([]).user_id == example06.DEFAULT_USER_ID
    assert (
        example06.parse_arguments(["--user-id", "customer_123"]).user_id
        == "customer_123"
    )


def test_parse_arguments_rejects_empty_user_id() -> None:
    """Prevent an empty scope from reaching the private store."""
    with pytest.raises(SystemExit):
        example06.parse_arguments(["--user-id", "  "])


def test_main_logs_populated_threads_and_closes_pool(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """List the requested user scope and close the pool on success."""
    connection_pool = Mock()
    activities = [example06.ThreadActivity("thread-1", "2026-07-30T10:00:00Z", 1)]
    list_threads = Mock(return_value=activities)
    monkeypatch.setattr(example06, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example06, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example06, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example06, "create_memory_store", Mock(return_value=Mock()))
    monkeypatch.setattr(example06, "list_populated_threads", list_threads)
    caplog.set_level(logging.INFO, logger=example06.LOGGER.name)

    assert example06.main(["--user-id", "customer_123"]) == 0

    assert list_threads.call_args.args[1] == "customer_123"
    assert (
        "Thread id=thread-1 latest_message_timestamp=2026-07-30T10:00:00Z"
        in caplog.text
    )
    connection_pool.close.assert_called_once_with()


def test_main_closes_pool_when_listing_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Close the pool and report private-store failures safely."""
    connection_pool = Mock()
    monkeypatch.setattr(example06, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example06, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example06, "load_memory_store_id", lambda: MEMORY_STORE_ID)
    monkeypatch.setattr(example06, "create_memory_store", Mock(return_value=Mock()))
    monkeypatch.setattr(
        example06, "list_populated_threads", Mock(side_effect=RuntimeError())
    )
    caplog.set_level(logging.INFO, logger=example06.LOGGER.name)

    assert example06.main([]) == 1

    assert "thread-listing example failed (RuntimeError)" in caplog.text
    connection_pool.close.assert_called_once_with()
