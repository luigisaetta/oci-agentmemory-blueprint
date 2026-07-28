"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Demonstrates user-scoped Oracle Agent Memory message search.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path

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
from examples.example05.messages import build_user1_messages, build_user2_messages

EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"
QUERY = "delivery delay tracking update"
AGENT_ID = "support_agent"
MAX_RESULTS = 5
LOGGER = logging.getLogger(__name__)


def create_memory_store(
    connection_pool: oracledb.ConnectionPool,
    oci_config: dict[str, str],
    memory_store_id: str,
) -> OracleAgentMemory:
    """Create the ADB-backed store used for user-scoped message retrieval.

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


def log_search_results(label: str, results: list[object]) -> None:
    """Log the scoped ownership and content returned by a search.

    Args:
        label: Description of the search scope being displayed.
        results: Search results returned by Oracle Agent Memory.
    """
    LOGGER.info("%s returned %d result(s).", label, len(results))
    for result in results:
        record = result.record
        LOGGER.info(
            "Result timestamp=%s user=%s role=%s content=%s",
            record.timestamp,
            record.user_id,
            record.role,
            result.content,
        )


def run_searches(memory: OracleAgentMemory) -> None:
    """Run one rejected and two user-scoped searches using the same query.

    Args:
        memory: Configured Agent Memory client containing both user threads.
    """
    LOGGER.info("Running message search query: %s", QUERY)
    try:
        memory.search(QUERY, record_types=["message"], max_results=MAX_RESULTS)
    except ValueError:
        LOGGER.info(
            "Unscoped client search was rejected: Oracle Agent Memory requires "
            "an explicit user_id for client-level retrieval."
        )

    LOGGER.info("")
    user1_results = memory.search(
        QUERY,
        user_id="user1",
        record_types=["message"],
        max_results=MAX_RESULTS,
    )
    log_search_results("Search scoped to user1", user1_results)

    LOGGER.info("")
    user2_results = memory.search(
        QUERY,
        user_id="user2",
        record_types=["message"],
        max_results=MAX_RESULTS,
    )
    log_search_results("Search scoped to user2", user2_results)


def main() -> int:
    """Persist two customer conversations and demonstrate scoped retrieval.

    Returns:
        Zero when persistence and all searches succeed; otherwise one.
    """
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
        inserted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        user1_messages = build_user1_messages(inserted_at)
        user2_messages = build_user2_messages(
            inserted_at, start_offset_seconds=len(user1_messages)
        )

        LOGGER.info("Persisting messages for user1.")
        user1_thread = memory.create_thread(user_id="user1", agent_id=AGENT_ID)
        user1_ids = user1_thread.add_messages(user1_messages)
        LOGGER.info("Persisted %d messages for user1: %s", len(user1_ids), user1_ids)

        LOGGER.info("")
        LOGGER.info("Persisting messages for user2.")
        user2_thread = memory.create_thread(user_id="user2", agent_id=AGENT_ID)
        user2_ids = user2_thread.add_messages(user2_messages)
        LOGGER.info("Persisted %d messages for user2: %s", len(user2_ids), user2_ids)

        LOGGER.info("")
        run_searches(memory)
    except ConfigurationError as error:
        LOGGER.error("Agent Memory configuration error: %s", error)
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except ValueError:
        LOGGER.error(
            "Agent Memory rejected an invalid value. Check the ADB and OCI "
            "configuration and the thread-message input."
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except Exception as error:  # pylint: disable=broad-exception-caught
        # OCI and database SDKs expose several error types.
        LOGGER.error(
            "Agent Memory scoped-search example failed (%s). Check the ADB and "
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
