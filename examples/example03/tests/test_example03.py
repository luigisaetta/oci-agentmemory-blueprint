"""
Author: L. Saetta
Date last modified: 2026-07-27
License: MIT
Description: Unit tests for the Resource Principal Agent Memory example.
"""

import importlib.util
from datetime import datetime
import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "example03.py"
SPEC = importlib.util.spec_from_file_location("example03", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
example03 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example03)

RESOURCE_PRINCIPAL_SETTINGS = {
    "compartment_id": "ocid1.compartment.oc1..example",
    "region": "eu-frankfurt-1",
}


def test_create_memory_store_uses_only_resource_principal_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass the Resource Principal signer instead of OCI API-key settings."""
    signer = Mock()
    embedder_factory = Mock(return_value=Mock())
    llm_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(
        example03, "get_resource_principals_signer", Mock(return_value=signer)
    )
    monkeypatch.setattr(example03, "Embedder", embedder_factory)
    monkeypatch.setattr(example03, "Llm", llm_factory)
    monkeypatch.setattr(example03, "OracleAgentMemory", memory_factory)

    example03.create_memory_store(Mock(), RESOURCE_PRINCIPAL_SETTINGS)

    expected_arguments = {
        "oci_compartment_id": "ocid1.compartment.oc1..example",
        "oci_region": "eu-frankfurt-1",
        "oci_signer": signer,
    }
    assert embedder_factory.call_args.kwargs == {
        "model": example03.EMBEDDING_MODEL_ID,
        **expected_arguments,
    }
    assert llm_factory.call_args.kwargs == {
        "model": example03.MODEL_ID,
        **expected_arguments,
    }


def test_main_persists_messages_and_closes_pool(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Persist timestamped messages and close the pool on success."""
    connection_pool = Mock()
    memory = Mock()
    memory.create_thread.return_value.add_messages.return_value = [
        "message-1",
        "message-2",
    ]
    monkeypatch.setattr(example03, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(
        example03,
        "load_resource_principal_settings",
        lambda: RESOURCE_PRINCIPAL_SETTINGS,
    )
    monkeypatch.setattr(example03, "create_memory_store", Mock(return_value=memory))
    caplog.set_level(logging.INFO, logger=example03.LOGGER.name)

    assert example03.main() == 0

    connection_pool.close.assert_called_once_with()
    assert "Resource Principal" in caplog.text
    added_messages = memory.create_thread.return_value.add_messages.call_args.args[0]
    assert len(added_messages) == 2
    assert all(
        message.timestamp == added_messages[0].timestamp for message in added_messages
    )
    datetime.fromisoformat(added_messages[0].timestamp.replace("Z", "+00:00"))


def test_main_reports_unavailable_resource_principal_and_closes_pool(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Report unavailable runtime credentials without exposing configuration."""
    connection_pool = Mock()
    monkeypatch.setattr(example03, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(
        example03,
        "load_resource_principal_settings",
        lambda: RESOURCE_PRINCIPAL_SETTINGS,
    )
    monkeypatch.setattr(
        example03,
        "create_memory_store",
        Mock(side_effect=EnvironmentError("unavailable")),
    )
    caplog.set_level(logging.INFO, logger=example03.LOGGER.name)

    assert example03.main() == 1

    assert "Resource Principal credentials are unavailable" in caplog.text
    assert "unavailable" in caplog.text
    connection_pool.close.assert_called_once_with()


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (example03.ConfigurationError("missing settings"), "configuration error"),
        (ValueError(), "rejected an invalid value"),
        (RuntimeError(), "execution failed (RuntimeError)"),
    ],
)
def test_main_reports_other_failures_and_closes_pool(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    expected_message: str,
) -> None:
    """Report expected failure categories without leaking message content."""
    connection_pool = Mock()
    monkeypatch.setattr(example03, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(
        example03,
        "load_resource_principal_settings",
        lambda: RESOURCE_PRINCIPAL_SETTINGS,
    )
    monkeypatch.setattr(
        example03,
        "create_memory_store",
        Mock(side_effect=error),
    )
    caplog.set_level(logging.INFO, logger=example03.LOGGER.name)

    assert example03.main() == 1

    assert expected_message in caplog.text
    connection_pool.close.assert_called_once_with()
