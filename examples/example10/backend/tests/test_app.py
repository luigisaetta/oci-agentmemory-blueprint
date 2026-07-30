"""
Author: L. Saetta
Date last modified: 2026-07-30
License: MIT
Description: Unit tests for the Example 10 FastAPI memory-client configuration.
"""

from unittest.mock import Mock

import pytest

from examples.example10.backend import app as console_app


def test_create_memory_store_configures_llm_for_thread_insights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Make summary and Context Card generation available to selected threads."""
    oci_settings = {
        "compartment_id": "compartment",
        "region": "region",
        "user": "user",
        "fingerprint": "fingerprint",
        "tenancy": "tenancy",
        "key_file": "~/.oci/key.pem",
    }
    embedder_factory = Mock(return_value=Mock())
    llm_factory = Mock(return_value=Mock())
    memory_factory = Mock()
    monkeypatch.setattr(console_app, "load_oci_settings", lambda: oci_settings)
    monkeypatch.setattr(console_app, "load_memory_store_id", lambda: "OAM")
    monkeypatch.setattr(console_app, "Embedder", embedder_factory)
    monkeypatch.setattr(console_app, "Llm", llm_factory)
    monkeypatch.setattr(console_app, "OracleAgentMemory", memory_factory)

    console_app.create_memory_store(Mock())

    assert llm_factory.call_args.kwargs["model"] == console_app.LLM_MODEL_ID
    assert memory_factory.call_args.kwargs["llm"] is llm_factory.return_value
    extraction_config = memory_factory.call_args.kwargs["memory_extraction_config"]
    assert extraction_config.extract_memories is True
    assert (
        extraction_config.extraction_mode == console_app.MemoryExtractionMode.BACKGROUND
    )
