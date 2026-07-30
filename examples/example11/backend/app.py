"""
Author: L. Saetta
Date last modified: 2026-07-30
License: MIT
Description: FastAPI chatbot backend using Oracle Agent Memory threads and LangChain OCI.
"""

from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
from typing import Callable, Iterator

import oracledb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_oci import ChatOCIGenAI
from oracleagentmemory.apis import Message
from oracleagentmemory.core import MemoryExtractionConfig, OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm
from pydantic import BaseModel, Field

from common import (
    create_connection_pool,
    load_genai_chat_settings,
    load_memory_store_id,
    load_oci_settings,
)
from examples.example06.example06 import list_populated_threads
from examples.example11.backend.prompts import build_chat_prompt

APP_NAME = "Example 11 Thread Chatbot"
EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"
MEMORY_LLM_MODEL_ID = "oci/openai.gpt-oss-120b"


class ThreadCreate(BaseModel):
    """Request body used to create a chatbot thread.

    Attributes:
        agent_id: Optional application identifier associated with the thread.
    """

    agent_id: str = Field(default="chatbot_agent", min_length=1, max_length=100)


class QuestionCreate(BaseModel):
    """Request body containing one user question.

    Attributes:
        question: Non-empty question sent to the chatbot model.
    """

    question: str = Field(min_length=1, max_length=8000)


def validate_identifier(value: str, label: str) -> str:
    """Reject blank user and thread identifiers.

    Args:
        value: Identifier supplied through a path parameter.
        label: Name used in the safe validation message.

    Returns:
        A stripped non-empty identifier.

    Raises:
        HTTPException: If the value is blank.
    """
    stripped_value = value.strip()
    if not stripped_value:
        raise HTTPException(status_code=400, detail=f"{label} must not be empty.")
    return stripped_value


def create_memory_store(pool: oracledb.ConnectionPool) -> OracleAgentMemory:
    """Create the ADB-backed thread store used by the chatbot.

    Args:
        pool: Open ADB connection pool used for thread persistence.

    Returns:
        Configured Agent Memory client with derived-memory extraction disabled.
    """
    settings = load_oci_settings()
    arguments = {
        "oci_compartment_id": settings["compartment_id"],
        "oci_region": settings["region"],
        "oci_user": settings["user"],
        "oci_fingerprint": settings["fingerprint"],
        "oci_tenancy": settings["tenancy"],
        "oci_key_file": str(Path(settings["key_file"]).expanduser()),
    }
    return OracleAgentMemory(
        connection=pool,
        embedder=Embedder(model=EMBEDDING_MODEL_ID, **arguments),
        llm=Llm(model=MEMORY_LLM_MODEL_ID, **arguments),
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id=load_memory_store_id(),
        memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
    )


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOCIGenAI:
    """Create and cache the OCI API-key authenticated LangChain chat client.

    Returns:
        Reusable OCI Generative AI chat-model client.
    """
    chat_settings = load_genai_chat_settings()
    oci_settings = load_oci_settings()
    return ChatOCIGenAI(
        model_id=chat_settings["model_id"],
        service_endpoint=(
            f"https://inference.generativeai.{chat_settings['region']}.oci.oraclecloud.com"
        ),
        compartment_id=oci_settings["compartment_id"],
        auth_type="API_KEY",
        auth_profile="DEFAULT",
    )


def with_memory(callback: Callable[[OracleAgentMemory], object]) -> object:
    """Run an API operation with a short-lived ADB connection pool.

    Args:
        callback: Operation receiving a configured Agent Memory client.

    Returns:
        Value returned by the operation.

    Raises:
        HTTPException: With a safe HTTP error for invalid or unavailable services.
    """
    pool: oracledb.ConnectionPool | None = None
    try:
        pool = create_connection_pool()
        return callback(create_memory_store(pool))
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid chatbot input.") from error
    except Exception as error:  # pylint: disable=broad-exception-caught
        raise HTTPException(
            status_code=503, detail="Chatbot service is unavailable."
        ) from error
    finally:
        if pool is not None:
            pool.close()


def get_owned_thread(memory: OracleAgentMemory, user_id: str, thread_id: str):
    """Load a thread only when its stored owner matches the requested user.

    Args:
        memory: Configured Agent Memory client.
        user_id: Requested user scope.
        thread_id: Thread to load.

    Returns:
        Owned Agent Memory thread.

    Raises:
        HTTPException: If the thread is unknown or belongs to another user.
    """
    try:
        thread = memory.get_thread(thread_id)
    except KeyError as error:
        raise HTTPException(
            status_code=404, detail="Thread not found for this user."
        ) from error
    if thread.user_id != user_id:
        raise HTTPException(status_code=404, detail="Thread not found for this user.")
    return thread


def text_from_model_response(response: object) -> str:
    """Extract non-empty text from a LangChain OCI model response.

    Args:
        response: Value returned by the LangChain model invocation.

    Returns:
        Generated assistant text.

    Raises:
        ValueError: If the model returns no usable text.
    """
    content = getattr(response, "content", response)
    if isinstance(content, str) and content.strip():
        return content.strip()
    raise ValueError("The model returned no text.")


def stream_event(event: str, payload: dict[str, str]) -> str:
    """Encode one server-sent event without exposing internal data.

    Args:
        event: Event name understood by the frontend.
        payload: JSON-safe public event data.

    Returns:
        Encoded SSE event text.
    """
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/users/{user_id}/threads")
def create_thread(user_id: str, request: ThreadCreate) -> dict[str, str]:
    """Create a new user-scoped chatbot thread."""
    user_id = validate_identifier(user_id, "user_id")
    return with_memory(
        lambda memory: {
            "thread_id": memory.create_thread(
                user_id=user_id, agent_id=request.agent_id
            ).thread_id
        }
    )


@app.get("/api/users/{user_id}/threads")
def list_threads(
    user_id: str, limit: int = Query(default=10, ge=1, le=10)
) -> list[dict[str, str | int]]:
    """Return up to ten populated threads with newest activity first."""
    user_id = validate_identifier(user_id, "user_id")
    return with_memory(
        lambda memory: [
            entry.__dict__ for entry in list_populated_threads(memory, user_id)[:limit]
        ]
    )


@app.get("/api/users/{user_id}/threads/{thread_id}")
def resume_thread(user_id: str, thread_id: str) -> dict[str, object]:
    """Resume an owned thread and return its complete chronological history."""
    user_id = validate_identifier(user_id, "user_id")
    thread_id = validate_identifier(thread_id, "thread_id")

    def read(memory: OracleAgentMemory) -> dict[str, object]:
        thread = get_owned_thread(memory, user_id, thread_id)
        return {
            "thread_id": thread_id,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp,
                }
                for message in thread.get_messages()
            ],
        }

    return with_memory(read)


@app.post("/api/users/{user_id}/threads/{thread_id}/questions")
def ask_question(
    user_id: str, thread_id: str, request: QuestionCreate
) -> StreamingResponse:
    """Stream and persist an assistant answer using the thread Context Card."""
    user_id = validate_identifier(user_id, "user_id")
    thread_id = validate_identifier(thread_id, "thread_id")

    def answer_stream() -> Iterator[str]:
        pool: oracledb.ConnectionPool | None = None
        try:
            pool = create_connection_pool()
            memory = create_memory_store(pool)
            thread = get_owned_thread(memory, user_id, thread_id)
            context_card = thread.get_context_card()
            answer_parts: list[str] = []
            for chunk in get_chat_model().stream(
                build_chat_prompt(context_card.content, request.question)
            ):
                chunk_content = getattr(chunk, "content", "")
                if isinstance(chunk_content, str) and chunk_content:
                    answer_parts.append(chunk_content)
                    yield stream_event("token", {"text": chunk_content})

            answer_text = "".join(answer_parts).strip()
            if not answer_text:
                raise ValueError("The model returned no text.")
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            thread.add_messages(
                [
                    Message(role="user", content=request.question, timestamp=timestamp),
                    Message(role="assistant", content=answer_text, timestamp=timestamp),
                ]
            )
            yield stream_event("complete", {"thread_id": thread_id})
        except HTTPException as error:
            yield stream_event("error", {"detail": str(error.detail)})
        except Exception:  # pylint: disable=broad-exception-caught
            yield stream_event("error", {"detail": "Chatbot service is unavailable."})
        finally:
            if pool is not None:
                pool.close()

    return StreamingResponse(answer_stream(), media_type="text/event-stream")
