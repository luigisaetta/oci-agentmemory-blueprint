"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Uses OCI Resource Principal authentication with Oracle Agent Memory.
"""

from datetime import datetime, timezone
import logging

import oracledb
from oci.auth.signers import get_resource_principals_signer

from oracleagentmemory.apis import Message
from oracleagentmemory.core import (
    MemoryExtractionConfig,
    MemoryExtractionMode,
    OracleAgentMemory,
)
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm

from common import (
    ConfigurationError,
    create_connection_pool,
    load_memory_store_id,
    load_resource_principal_settings,
)

MODEL_ID = "oci/openai.gpt-oss-120b"
EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"
LOGGER = logging.getLogger(__name__)


def create_memory_store(
    connection_pool: oracledb.ConnectionPool,
    resource_principal_settings: dict[str, str],
    memory_store_id: str,
) -> OracleAgentMemory:
    """Create an Agent Memory store using OCI Resource Principal credentials.

    Args:
        connection_pool: Open ADB connection pool used for persistence.
        resource_principal_settings: OCI Generative AI compartment and region.
        memory_store_id: Shared identifier for the managed Agent Memory store.

    Returns:
        A configured Oracle Agent Memory instance.

    Raises:
        EnvironmentError: If the OCI runtime has no Resource Principal.
    """
    oci_arguments = {
        "oci_compartment_id": resource_principal_settings["compartment_id"],
        "oci_region": resource_principal_settings["region"],
        "oci_signer": get_resource_principals_signer(),
    }
    return OracleAgentMemory(
        connection=connection_pool,
        embedder=Embedder(model=EMBEDDING_MODEL_ID, **oci_arguments),
        llm=Llm(model=MODEL_ID, **oci_arguments),
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id=memory_store_id,
        memory_extraction_config=MemoryExtractionConfig(
            extract_memories=True,
            extraction_mode=MemoryExtractionMode.BACKGROUND,
        ),
    )


def main() -> int:
    """Persist sample messages using OCI Resource Principal authentication.

    Returns:
        Zero when startup succeeds; otherwise one.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    connection_pool: oracledb.ConnectionPool | None = None
    try:
        LOGGER.info("--------- Setup ---------")
        connection_pool = create_connection_pool()
        LOGGER.info("Created connection pool.")

        memory = create_memory_store(
            connection_pool,
            load_resource_principal_settings(),
            load_memory_store_id(),
        )
        LOGGER.info("Successfully connected to Agent Memory with Resource Principal.")

        thread = memory.create_thread(user_id="user_123", agent_id="agent_456")
        LOGGER.info("Created thread: %s", thread.thread_id)

        inserted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        messages = [
            Message(
                role="user",
                content="I prefer window seats on flights.",
                timestamp=inserted_at,
            ),
            Message(
                role="assistant",
                content="Noted. I will keep that in mind.",
                timestamp=inserted_at,
            ),
        ]
        message_ids = thread.add_messages(messages)
        LOGGER.info("Added %d messages to the thread: %s", len(messages), message_ids)
    except ConfigurationError as error:
        LOGGER.error("Agent Memory configuration error: %s", error)
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except EnvironmentError:
        LOGGER.error(
            "OCI Resource Principal credentials are unavailable. Run this example "
            "in a configured OCI-managed runtime."
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except ValueError:
        LOGGER.error(
            "Agent Memory rejected an invalid value. Check the local ADB and "
            "Resource Principal configuration and the thread-message input."
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except Exception as error:  # OCI and database SDKs expose several error types.
        LOGGER.error(
            "Agent Memory execution failed (%s). Check the ADB, Resource "
            "Principal, and OCI Generative AI configuration.",
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
