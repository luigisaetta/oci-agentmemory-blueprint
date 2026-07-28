"""
Author: L. Saetta
Date last modified: 2026-07-27
License: MIT
Description: Persists a customer-support conversation in Oracle Agent Memory.
"""

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

from common import ConfigurationError, create_connection_pool, load_oci_settings
from examples.example02.messages import build_customer_support_messages

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
            extraction_mode=MemoryExtractionMode.BACKGROUND,
        ),
    )


def main() -> int:
    """Persist the customer-support conversation and close the ADB pool.

    Returns:
        Zero when persistence succeeds; otherwise one.
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

        # create the memory store
        memory = create_memory_store(connection_pool, load_oci_settings())
        LOGGER.info("Successfully connected to Agent Memory.")
        thread = memory.create_thread(
            user_id="customer_123", agent_id="support_agent_456"
        )
        LOGGER.info("Created thread: %s", thread.thread_id)

        # Add the fixed conversation from messages.py.
        inserted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        messages = build_customer_support_messages(inserted_at)
        message_ids = thread.add_messages(messages)
        LOGGER.info(
            "Persisted %d customer-support messages: %s", len(messages), message_ids
        )

        # get the context card
        card = thread.get_context_card(
            max_relevant_results=10,
            min_relevant_results_by_type={
                "preference": 1,
                "guideline": 1,
            },
        )

        prompt_context = card.content
        LOGGER.info("Generated Context Card: %s", prompt_context)

        # the context card can be used passing it to an LLM

        # if we want only the summary
        summary = thread.get_summary()
        LOGGER.info("Summary: %s", summary.content)

    except ConfigurationError as error:
        LOGGER.error("Agent Memory configuration error: %s", error)
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except ValueError:
        LOGGER.error(
            "Agent Memory rejected an invalid value. Check the local ADB and "
            "OCI configuration and the thread-message input."
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except Exception as error:  # OCI and database SDKs expose several error types.
        LOGGER.error(
            "Agent Memory execution failed (%s). "
            "Check the local ADB and OCI configuration.",
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
