"""
Author: L. Saetta
Date last modified: 2026-07-30
License: MIT
Description: FastAPI service for the Example 10 Oracle Agent Memory Console.
"""

from datetime import datetime, timezone
import os
from pathlib import Path

import oracledb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from oracleagentmemory.apis import Message
from oracleagentmemory.core import MemoryExtractionConfig, OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder

from common import create_connection_pool, load_memory_store_id, load_oci_settings
from examples.example06.example06 import list_populated_threads

APP_NAME = "Example 10 Agent Memory Console"
EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"
CORS_ORIGINS = os.getenv(
    "EXAMPLE10_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")


class ThreadCreate(BaseModel):
    """Input used to create a user-owned conversation thread."""

    agent_id: str = Field(default="console_agent", min_length=1, max_length=100)


class MessageCreate(BaseModel):
    """Input used to append a message to an existing thread."""

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


def create_memory_store(pool: oracledb.ConnectionPool) -> OracleAgentMemory:
    """Create an ADB-backed client without automatic long-term extraction."""
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
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id=load_memory_store_id(),
        memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
    )


def validate_identifier(value: str, label: str) -> str:
    """Reject blank path identifiers before accessing persistence."""
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{label} must not be empty.")
    return value


def with_memory(callback):
    """Run a callback with a short-lived pool and safely map service errors."""
    pool = None
    try:
        pool = create_connection_pool()
        return callback(create_memory_store(pool))
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400, detail="Invalid Agent Memory input."
        ) from error
    except Exception as error:  # pylint: disable=broad-exception-caught
        raise HTTPException(
            status_code=503, detail="Agent Memory is unavailable."
        ) from error
    finally:
        if pool is not None:
            pool.close()


def owned_thread(memory: OracleAgentMemory, user_id: str, thread_id: str):
    """Return a thread only when its persisted owner matches the user scope."""
    thread = memory.get_thread(thread_id)
    if thread.user_id != user_id:
        raise HTTPException(status_code=404, detail="Thread not found for this user.")
    return thread


app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a dependency-free service health response."""
    return {"status": "ok"}


@app.get("/api/users/{user_id}/threads")
def threads(user_id: str) -> list[dict[str, str]]:
    """List the selected user's message-bearing threads by latest activity."""
    user_id = validate_identifier(user_id, "user_id")
    return with_memory(
        lambda memory: [
            entry.__dict__ for entry in list_populated_threads(memory, user_id)
        ]
    )


@app.post("/api/users/{user_id}/threads")
def create_thread(user_id: str, request: ThreadCreate) -> dict[str, str]:
    """Create an empty thread; it becomes listable after its first message."""
    user_id = validate_identifier(user_id, "user_id")
    return with_memory(
        lambda memory: {
            "thread_id": memory.create_thread(
                user_id=user_id, agent_id=request.agent_id
            ).thread_id
        }
    )


@app.post("/api/users/{user_id}/threads/{thread_id}/messages")
def add_message(user_id: str, thread_id: str, request: MessageCreate) -> dict[str, str]:
    """Append one timestamped user or assistant message to an owned thread."""
    user_id, thread_id = validate_identifier(user_id, "user_id"), validate_identifier(
        thread_id, "thread_id"
    )

    def insert(memory):
        thread = owned_thread(memory, user_id, thread_id)
        thread.add_messages(
            [
                Message(
                    role=request.role,
                    content=request.content,
                    timestamp=datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                )
            ]
        )
        return {"thread_id": thread_id}

    return with_memory(insert)


@app.get("/api/users/{user_id}/threads/{thread_id}/messages")
def messages(user_id: str, thread_id: str) -> list[dict[str, str]]:
    """Return messages for the selected user's populated thread."""
    user_id, thread_id = validate_identifier(user_id, "user_id"), validate_identifier(
        thread_id, "thread_id"
    )
    return with_memory(
        lambda memory: [
            {
                "role": item.role,
                "content": item.content,
                "timestamp": item.timestamp or "",
            }
            for item in owned_thread(memory, user_id, thread_id).get_messages()
        ]
    )


@app.get("/api/users/{user_id}/threads/{thread_id}/insights")
def insights(user_id: str, thread_id: str) -> dict[str, str]:
    """Generate the selected thread's current summary and Context Card."""
    user_id, thread_id = validate_identifier(user_id, "user_id"), validate_identifier(
        thread_id, "thread_id"
    )

    def read(memory):
        thread = owned_thread(memory, user_id, thread_id)
        return {
            "summary": thread.get_summary().content,
            "context_card": thread.get_context_card().content,
        }

    return with_memory(read)


@app.get("/api/users/{user_id}/messages/search")
def search(user_id: str, q: str) -> list[dict[str, str]]:
    """Search raw message records strictly within the selected user scope."""
    user_id, q = validate_identifier(user_id, "user_id"), validate_identifier(q, "q")

    def run(memory):
        return [
            {
                "content": result.content,
                "thread_id": str(result.record.thread_id),
                "role": result.record.role,
                "timestamp": str(result.record.timestamp),
            }
            for result in memory.search(
                q, user_id=user_id, record_types=["message"], max_results=10
            )
        ]

    return with_memory(run)
