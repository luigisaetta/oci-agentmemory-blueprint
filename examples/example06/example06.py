"""
Author: L. Saetta
Date last modified: 2026-07-30
License: MIT
Description: Lists populated Oracle Agent Memory threads for one user by recent activity.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Sequence

import oracledb

from oracleagentmemory.core import MemoryExtractionConfig, OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder

from common import (
    ConfigurationError,
    create_connection_pool,
    load_memory_store_id,
    load_oci_settings,
)

EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"
DEFAULT_USER_ID = "user1"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThreadActivity:
    """One populated thread and the timestamp of its newest message.

    Attributes:
        thread_id: Identifier of the persisted conversation thread.
        latest_message_timestamp: UTC timestamp supplied with its newest message.
    """

    thread_id: str
    latest_message_timestamp: str


def create_memory_store(
    connection_pool: oracledb.ConnectionPool,
    oci_config: dict[str, str],
    memory_store_id: str,
) -> OracleAgentMemory:
    """Create the ADB-backed store used for message-only thread discovery.

    Args:
        connection_pool: Open ADB connection pool used for persistence.
        oci_config: Validated OCI profile values for the embedding provider.
        memory_store_id: Shared identifier for the managed Agent Memory store.

    Returns:
        An Agent Memory client with automatic extraction disabled.
    """
    oci_arguments = {
        "oci_compartment_id": oci_config["compartment_id"],
        "oci_region": oci_config["region"],
        "oci_user": oci_config["user"],
        "oci_fingerprint": oci_config["fingerprint"],
        "oci_tenancy": oci_config["tenancy"],
        "oci_key_file": str(Path(oci_config["key_file"]).expanduser()),
    }
    return OracleAgentMemory(
        connection=connection_pool,
        embedder=Embedder(model=EMBEDDING_MODEL_ID, **oci_arguments),
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id=memory_store_id,
        memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
    )


def parse_timestamp(timestamp: object) -> datetime:
    """Parse a persisted message timestamp as a timezone-aware UTC value.

    Args:
        timestamp: ISO 8601 timestamp stored on a message record.

    Returns:
        The equivalent timezone-aware timestamp.

    Raises:
        ValueError: If the timestamp is not a timezone-aware ISO 8601 value.
    """
    if isinstance(timestamp, datetime):
        parsed_timestamp = timestamp
    elif isinstance(timestamp, str):
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        raise ValueError("Message timestamp must be an ISO 8601 value.")

    if parsed_timestamp.tzinfo is None:
        raise ValueError("Message timestamp must include a timezone.")
    return parsed_timestamp.astimezone(timezone.utc)


def list_populated_threads(
    client: OracleAgentMemory, user_id: str
) -> list[ThreadActivity]:
    """List a user's message-bearing threads by newest message first.

    This is a temporary workaround for the absence of a supported thread-listing
    API. It intentionally uses the private store only to discover raw message
    records belonging to the selected user.

    Args:
        client: Configured Agent Memory client to query.
        user_id: Owner scope whose populated threads are requested.

    Returns:
        Thread activity entries ordered by latest message timestamp descending.

    Raises:
        ValueError: If a discovered message has an invalid timestamp.
    """
    # pylint: disable=protected-access
    messages = client._store.list(
        record_type="message",
        user_id=user_id,
        limit=None,
    )
    thread_ids = {
        message.thread_id for message in messages if message.thread_id is not None
    }

    latest_messages: dict[object, tuple[datetime, str]] = {}
    for message in messages:
        if message.thread_id not in thread_ids:
            continue
        message_timestamp = parse_timestamp(message.timestamp)
        latest_for_thread = latest_messages.get(message.thread_id)
        if latest_for_thread is None or message_timestamp > latest_for_thread[0]:
            latest_messages[message.thread_id] = (
                message_timestamp,
                message.timestamp,
            )

    activities = [
        ThreadActivity(
            thread_id=str(thread_id), latest_message_timestamp=latest_timestamp
        )
        for thread_id, (_, latest_timestamp) in latest_messages.items()
    ]
    return sorted(
        activities,
        key=lambda activity: (
            -parse_timestamp(activity.latest_message_timestamp).timestamp(),
            activity.thread_id,
        ),
    )


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the user scope for the thread-listing command.

    Args:
        arguments: Optional command-line arguments, excluding the program name.

    Returns:
        Parsed command arguments with a non-empty user ID.
    """
    parser = argparse.ArgumentParser(
        description="List populated Oracle Agent Memory threads for one user."
    )
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help="User scope to inspect (default: %(default)s).",
    )
    parsed_arguments = parser.parse_args(arguments)
    if not parsed_arguments.user_id.strip():
        parser.error("--user-id must not be empty.")
    return parsed_arguments


def main(arguments: Sequence[str] | None = None) -> int:
    """List populated threads in one user scope and close the ADB pool.

    Args:
        arguments: Optional command-line arguments, excluding the program name.

    Returns:
        Zero when listing succeeds; otherwise one.
    """
    parsed_arguments = parse_arguments(arguments)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    connection_pool: oracledb.ConnectionPool | None = None
    try:
        connection_pool = create_connection_pool()

        memory = create_memory_store(
            connection_pool, load_oci_settings(), load_memory_store_id()
        )

        # we add the timestamp of the last message to be able to sort threads
        activities = list_populated_threads(memory, parsed_arguments.user_id)

        if not activities:
            LOGGER.info(
                "No populated threads found for user_id=%s.",
                parsed_arguments.user_id,
            )

        LOGGER.info("Found %s threads.", len(activities))
        
        for activity in activities:
            LOGGER.info(
                "Thread id=%s latest_message_timestamp=%s",
                activity.thread_id,
                activity.latest_message_timestamp,
            )
    except ConfigurationError as error:
        LOGGER.error("Agent Memory configuration error: %s", error)
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except ValueError:
        LOGGER.error(
            "Agent Memory rejected an invalid value. Check the user ID, stored "
            "message timestamps, and local ADB and OCI configuration."
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except Exception as error:  # pylint: disable=broad-exception-caught
        LOGGER.error(
            "Agent Memory thread-listing example failed (%s). Check ADB and "
            "OCI configuration.",
            type(error).__name__,
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    finally:
        if connection_pool is not None:
            connection_pool.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
