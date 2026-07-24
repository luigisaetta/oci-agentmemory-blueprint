"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Creates an Oracle Agent Memory store backed by Oracle ADB.
"""

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path

import oracledb

from oracleagentmemory.core import (
    MemoryExtractionConfig,
    MemoryExtractionMode,
    OracleAgentMemory,
)
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm
from oracleagentmemory.apis import Message

from common import ConfigurationError, create_connection_pool, load_oci_settings

MODEL_ID = "oci/openai.gpt-oss-120b"
EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"

LOGGER = logging.getLogger(__name__)


def create_memory_store(
    connection_pool: oracledb.ConnectionPool, oci_config: dict[str, str]
) -> OracleAgentMemory:
    """Create the configured Oracle Agent Memory store.

    Args:
        connection_pool: Open ADB connection pool used for persistence.
        oci_config: Validated OCI profile values for model providers.

    Returns:
        A configured Oracle Agent Memory instance.
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
        llm=Llm(model=MODEL_ID, **oci_arguments),
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id="OAM_",
        memory_extraction_config=MemoryExtractionConfig(
            extract_memories=True,
            # this can be considered as a best practice
            extraction_mode=MemoryExtractionMode.BACKGROUND,
        ),
    )


async def main() -> int:
    """Create the memory store and close the ADB connection pool.

    Returns:
        Zero when startup succeeds; otherwise one.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    connection_pool: oracledb.ConnectionPool | None = None
    stage = "Creating the ADB connection pool"
    try:
        LOGGER.info("--------- Setup ---------")
        connection_pool = create_connection_pool()
        LOGGER.info("Created connection pool...")

        stage = "initialising the Agent Memory store"
        memory = create_memory_store(connection_pool, load_oci_settings())
        LOGGER.info("Successfully connected to Agent Memory...")

        stage = "creating the example thread"
        thread = memory.create_thread(
            user_id="user_123",
            agent_id="agent_456",
        )
        LOGGER.info("Created thread: %s..", thread.thread_id)
        LOGGER.info("------- End setup -------")
        LOGGER.info("")

        LOGGER.info("------ Adding msgs ------")
        stage = "adding example messages to the thread"
        inserted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        messages = [
            Message(
                role="user",
                content="I prefer window seats on flights.",
                timestamp=inserted_at,
            ),
            {
                "role": "assistant",
                "content": "Noted. I will keep that in mind.",
                "timestamp": inserted_at,
            },
        ]
        LOGGER.info("Queued %d messages for asynchronous insertion.", len(messages))
        message_ids = await thread.add_messages_async(messages)
        LOGGER.info("Added %d messages to the thread: %s", len(messages), message_ids)
        LOGGER.info("-------- End --------")

    except ConfigurationError as error:
        LOGGER.error("Agent Memory configuration error: %s", error)
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except ValueError:
        if stage == "creating the example thread":
            LOGGER.error(
                "Agent Memory could not create the example thread. "
                "Verify the thread, user, and agent identifiers."
            )
            LOGGER.error("Stack trace:", exc_info=True)
            return 1
        if stage == "adding example messages to the thread":
            LOGGER.error(
                "Agent Memory rejected the example messages. Verify that each "
                "message has a supported role and non-empty content."
            )
            LOGGER.error("Stack trace:", exc_info=True)
            return 1
        LOGGER.info(
            "Agent Memory rejected a value while %s. "
            "Verify the local ADB and OCI configuration.",
            stage,
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except Exception as error:  # OCI and database SDKs expose several error types.
        LOGGER.error(
            "Agent Memory failed while %s (%s). "
            "Check the local ADB and OCI configuration.",
            stage,
            type(error).__name__,
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    finally:
        if connection_pool is not None:
            connection_pool.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
