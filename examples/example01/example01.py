"""
Author: L. Saetta
Date last modified: 2026-07-24
License: MIT
Description: Creates an Oracle ADB connection pool for the Agent Memory examples.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

import oracledb
from oci.config import from_file

from oracleagentmemory.apis.searchscope import SearchScope
from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def create_connection_pool() -> oracledb.ConnectionPool:
    """Create and return an ADB connection pool using the local ``.env`` file.

    Returns:
        An open Oracle Database connection pool.
    """
    load_dotenv(ENV_FILE)

    return oracledb.create_pool(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PWD"],
        dsn=os.environ["DB_DSN"],
        config_dir=os.environ["WALLET_DIR"],
        wallet_location=os.environ["WALLET_DIR"],
        wallet_password=os.environ["WALLET_PWD"],
        min=int(os.environ["DB_POOL_MIN"]),
        max=int(os.environ["DB_POOL_MAX"]),
        increment=int(os.environ["DB_POOL_INCREMENT"]),
    )


# get OCI configs
# set OCI config parameters
config = from_file("~/.oci/config")
oci_key_file = str(Path(config["key_file"]).expanduser())
compartment_id = config["compartment_id"]

# connection pooling
conn_pool = create_connection_pool()

# set embedding model
oci_embedder = Embedder(
    model="oci/cohere.embed-english-v3.0",
    oci_compartment_id=config["compartment_id"],
    oci_region=config["region"],
    oci_user=config["user"],
    oci_fingerprint=config["fingerprint"],
    oci_tenancy=config["tenancy"],
    oci_key_file=oci_key_file,
)

# set language model
oci_llm = Llm(
    model="oci/openai.gpt-oss-120b",
    oci_compartment_id=config["compartment_id"],
    oci_region=config["region"],
    oci_user=config["user"],
    oci_fingerprint=config["fingerprint"],
    oci_tenancy=config["tenancy"],
    oci_key_file=oci_key_file,
)

try:
    memory = OracleAgentMemory(
        connection=conn_pool,
        embedder=oci_embedder,
        llm=oci_llm,
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        table_name_prefix="OAM_",
    )

    print("successfully connected to agent memory")
except Exception as e:
    raise (e)
