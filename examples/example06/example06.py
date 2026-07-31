"""
Author: L. Saetta
Date last modified: 2026-07-31
License: MIT
Description: Lists populated Oracle Agent Memory threads for one user by recent activity.
"""

import argparse
import logging
from pathlib import Path
from typing import Sequence

import oracledb

from oracleagentmemory.core import MemoryExtractionConfig, OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder

from agent_memory import list_populated_threads
from common import (
    ConfigurationError,
    create_connection_pool,
    load_memory_store_id,
    load_oci_settings,
)

EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"
DEFAULT_USER_ID = "user1"
LOGGER = logging.getLogger(__name__)


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
