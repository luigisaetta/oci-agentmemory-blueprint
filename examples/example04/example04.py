"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Recreates the managed Oracle Agent Memory schema for a maintenance cleanup.
"""

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

EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"
LOGGER = logging.getLogger(__name__)


def create_recreated_memory_store(
    connection_pool: oracledb.ConnectionPool,
    oci_config: dict[str, str],
    memory_store_id: str,
) -> OracleAgentMemory:
    """Drop and recreate the configured managed Agent Memory objects.

    Args:
        connection_pool: Open ADB connection pool used for schema management.
        oci_config: Validated OCI profile values for the embedding provider.
        memory_store_id: Shared identifier for the managed Agent Memory store.

    Returns:
        An Agent Memory instance after its managed schema has been recreated.
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
        schema_policy=SchemaPolicy.RECREATE,
        memory_store_id=memory_store_id,
        memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
    )


def main() -> int:
    """Recreate the managed schema and close all local resources.

    Returns:
        Zero when schema recreation succeeds; otherwise one.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    connection_pool: oracledb.ConnectionPool | None = None
    memory: OracleAgentMemory | None = None
    try:
        memory_store_id = load_memory_store_id()
        LOGGER.warning(
            "Recreating managed Agent Memory objects for store %s. Existing "
            "Agent Memory data in this store will be permanently deleted.",
            memory_store_id,
        )
        connection_pool = create_connection_pool()
        memory = create_recreated_memory_store(
            connection_pool, load_oci_settings(), memory_store_id
        )
        LOGGER.info(
            "Recreated managed Agent Memory objects for store %s.", memory_store_id
        )
    except ConfigurationError as error:
        LOGGER.error("Agent Memory configuration error: %s", error)
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except ValueError:
        LOGGER.error(
            "Agent Memory rejected the recreation configuration. Check the "
            "ADB and OCI configuration and the managed store compatibility."
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    except Exception as error:  # pylint: disable=broad-exception-caught
        # OCI and database SDKs expose several error types.
        LOGGER.error(
            "Agent Memory schema recreation failed (%s). Check ADB access, "
            "managed-object privileges, and OCI configuration.",
            type(error).__name__,
        )
        LOGGER.error("Stack trace:", exc_info=True)
        return 1
    finally:
        if memory is not None:
            memory.close()
        if connection_pool is not None:
            connection_pool.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
