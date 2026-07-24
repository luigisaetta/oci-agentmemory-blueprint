"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Creates an Oracle Agent Memory store backed by Oracle ADB.
"""

from pathlib import Path

import oracledb

from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm

from common import create_connection_pool, load_oci_settings

MODEL_ID = "oci/openai.gpt-oss-120b"
EMBEDDING_MODEL_ID = "oci/cohere.embed-multilingual-v3.0"


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
    )


def main() -> int:
    """Create the memory store and close the ADB connection pool.

    Returns:
        Zero when startup succeeds; otherwise one.
    """
    connection_pool: oracledb.ConnectionPool | None = None
    try:
        connection_pool = create_connection_pool()
        create_memory_store(connection_pool, load_oci_settings())
    except Exception as error:  # OCI and database SDKs expose several error types.
        print(
            "Agent Memory startup failed "
            f"({type(error).__name__}). Check local ADB and OCI configuration."
        )
        return 1
    finally:
        if connection_pool is not None:
            connection_pool.close()

    print("Successfully connected to Agent Memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
