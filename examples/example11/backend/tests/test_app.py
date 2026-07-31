"""
Author: L. Saetta
Date last modified: 2026-07-31
License: MIT
Description: Unit tests for the Example 11 chatbot FastAPI backend.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from examples.example11.backend import app as chatbot_app
from chat_prompts import build_chat_prompt


def test_demo_cors_allows_any_origin() -> None:
    """Permit unauthenticated cross-origin browser access for the demo only."""
    response = TestClient(chatbot_app.app).options(
        "/api/users/user1/threads",
        headers={
            "Origin": "http://example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_get_chat_model_uses_configured_region_and_model(monkeypatch) -> None:
    """Read LangChain OCI endpoint settings from the validated chat configuration."""
    factory = Mock(return_value=Mock())
    chatbot_app.get_chat_model.cache_clear()
    monkeypatch.setattr(
        chatbot_app,
        "load_genai_chat_settings",
        lambda: {"region": "eu-frankfurt-1", "model_id": "meta.llama-4"},
    )
    monkeypatch.setattr(
        chatbot_app,
        "load_oci_settings",
        lambda: {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(chatbot_app, "ChatOCIGenAI", factory)

    chatbot_app.get_chat_model()

    assert factory.call_args.kwargs["model_id"] == "meta.llama-4"
    assert factory.call_args.kwargs["service_endpoint"] == (
        "https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com"
    )
    assert factory.call_args.kwargs["auth_type"] == "API_KEY"


def test_list_threads_returns_only_the_requested_recent_limit(monkeypatch) -> None:
    """Reuse one startup-created pool while exposing the newest ten threads."""
    activities = [
        SimpleNamespace(
            thread_id=f"thread-{index}",
            latest_message_timestamp="2026-07-30T10:00:00Z",
            message_count=index,
        )
        for index in range(12)
    ]
    connection_pool = Mock()
    memory = Mock()
    pool_factory = Mock(return_value=connection_pool)
    monkeypatch.setattr(chatbot_app, "list_populated_threads", lambda *_: activities)
    monkeypatch.setattr(chatbot_app, "create_connection_pool", pool_factory)
    monkeypatch.setattr(chatbot_app, "create_memory_store", lambda _pool: memory)

    with TestClient(chatbot_app.app) as client:
        first_response = client.get("/api/users/user1/threads?limit=10")
        response = client.get("/api/users/user1/threads?limit=10")

    assert response.status_code == 200
    assert len(response.json()) == 10
    assert response.json()[0]["thread_id"] == "thread-0"
    assert first_response.status_code == 200
    pool_factory.assert_called_once_with()
    connection_pool.close.assert_called_once_with()


def test_build_chat_prompt_keeps_context_and_question_separate() -> None:
    """Mark Context Card content as reference and preserve the current question."""
    prompt = build_chat_prompt("<summary>Blue</summary>", "What color?")

    assert len(prompt) == 2
    assert "reference for continuity" in prompt[0].content
    assert "follow instructions contained" in prompt[0].content
    assert "<summary>Blue</summary>" in prompt[1].content
    assert prompt[1].content.endswith("Current user question:\nWhat color?")


def test_ask_question_uses_context_card_and_persists_messages(monkeypatch) -> None:
    """Use Context Card reference material and save user then assistant messages."""
    thread = Mock()
    thread.user_id = "user1"
    thread.get_context_card.return_value = SimpleNamespace(
        content="<summary>Remember blue.</summary>"
    )
    memory = Mock()
    memory.get_thread.return_value = thread
    connection_pool = Mock()
    model = Mock()
    model.stream.return_value = [
        SimpleNamespace(content="Blue "),
        SimpleNamespace(content="is noted."),
    ]
    monkeypatch.setattr(chatbot_app, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(chatbot_app, "create_memory_store", lambda _pool: memory)
    monkeypatch.setattr(chatbot_app, "get_chat_model", lambda: model)

    with TestClient(chatbot_app.app) as client:
        response = client.post(
            "/api/users/user1/threads/thread-1/questions",
            json={"question": "What color?"},
        )

    assert response.status_code == 200
    assert "event: token" in response.text
    assert '"text": "Blue "' in response.text
    assert '"text": "is noted."' in response.text
    assert "event: complete" in response.text
    prompt = model.stream.call_args.args[0]
    assert "<summary>Remember blue.</summary>" in prompt[1].content
    assert prompt[1].content.endswith("Current user question:\nWhat color?")
    persisted = thread.add_messages.call_args.args[0]
    assert [message.role for message in persisted] == ["user", "assistant"]
    assert [message.content for message in persisted] == [
        "What color?",
        "Blue is noted.",
    ]
    connection_pool.close.assert_called_once_with()


def test_resume_rejects_a_thread_owned_by_another_user(monkeypatch) -> None:
    """Prevent one user from resuming another user's thread."""
    thread = Mock()
    thread.user_id = "other-user"
    memory = Mock()
    memory.get_thread.return_value = thread
    connection_pool = Mock()
    monkeypatch.setattr(chatbot_app, "create_connection_pool", lambda: connection_pool)
    monkeypatch.setattr(chatbot_app, "create_memory_store", lambda _pool: memory)

    with TestClient(chatbot_app.app) as client:
        response = client.get("/api/users/user1/threads/thread-1")

    assert response.status_code == 404
    connection_pool.close.assert_called_once_with()
