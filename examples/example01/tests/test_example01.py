"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Unit tests for the Oracle Agent Memory startup example.
"""

import importlib.util
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


def test_create_memory_store_builds_oci_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass OCI values to the embedder, LLM, and memory store."""
    embedder_factory = Mock(return_value=Mock())
    llm_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(example01, "Embedder", embedder_factory)
    monkeypatch.setattr(example01, "Llm", llm_factory)
    monkeypatch.setattr(example01, "OracleAgentMemory", memory_factory)
    connection_pool = Mock()

    example01.create_memory_store(connection_pool, VALID_OCI_SETTINGS)

    assert embedder_factory.call_args.kwargs["model"] == example01.EMBEDDING_MODEL_ID
    assert llm_factory.call_args.kwargs["model"] == example01.MODEL_ID
    assert memory_factory.call_args.kwargs["connection"] is connection_pool
    assert memory_factory.call_args.kwargs["memory_store_id"] == "OAM_"


def test_main_closes_pool_on_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Close the pool regardless of the memory-store startup result."""
    connection_pool = Mock()
    monkeypatch.setattr(example01, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(example01, "load_oci_settings", lambda: VALID_OCI_SETTINGS)
    monkeypatch.setattr(example01, "create_memory_store", Mock())

    assert example01.main() == 0
    connection_pool.close.assert_called_once_with()
    assert "Successfully connected" in capsys.readouterr().out

    connection_pool.reset_mock()
    monkeypatch.setattr(
        example01,
        "create_memory_store",
        Mock(side_effect=RuntimeError("sensitive detail")),
    )
    assert example01.main() == 1
    connection_pool.close.assert_called_once_with()
    assert "sensitive detail" not in capsys.readouterr().out
