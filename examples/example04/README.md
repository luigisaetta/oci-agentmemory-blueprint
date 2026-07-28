# Example 04: Recreate an Oracle Agent Memory Schema

## Purpose

Example 04 performs a destructive maintenance cleanup of the managed Oracle
Agent Memory objects for the memory store selected by `MEMORY_STORE_ID`. It asks the SDK to drop and
recreate the store's tables, indexes, and managed retrieval structures through
`SchemaPolicy.RECREATE`.

Use this only for a disposable development database or an approved maintenance
operation. It permanently removes the store's threads, raw messages, extracted
and manually added memories, profiles, and retrieval data. There is no
application-level recovery after a successful reset; restore an ADB backup if
recovery is needed.

## Persistence and safety boundary

The reset applies only to Oracle Agent Memory objects managed for the configured
the configured `memory_store_id`. It does not issue generic `DROP TABLE` or `DROP INDEX`
commands and must not remove unrelated application objects from the same ADB
schema.

Stop application instances using this store before running it. Run it using the
schema-owner account, or an account with the privileges that Oracle Agent
Memory needs to drop and create its managed objects. Do not use this policy for
normal application startup; use `SchemaPolicy.REQUIRE_EXISTING` after the
maintenance operation.

The example configures the same OCI embedding provider as Example 01 so that
the recreated store is compatible with the blueprint's shared configuration.
It disables automatic memory extraction because it does not write messages and
does not need an LLM.

## Required configuration

Use the ADB and OCI profile configuration in the [Quick Start](../../QUICKSTART.md).
Set `MEMORY_STORE_ID` to the exact store that you intend to reset; it is shared
by all examples and is not a secret.
The database account must be allowed to manage the Agent Memory schema objects;
a least-privilege runtime account intended only for normal reads and writes may
not have sufficient DDL privileges.

## Run the example

From the repository root:

```bash
conda activate oci-agentmemory-blueprint
python -m examples.example04.example04
```

The command logs a destructive-operation warning before connecting and reports
success only after the SDK has recreated the managed objects. It closes the
Agent Memory client and ADB connection pool on both success and failure. It
does not log passwords, OCI private keys, or message content.

## Operational trade-offs

`SchemaPolicy.RECREATE` is appropriate for resetting a broken development
schema or intentionally discarding test data. It is not a selective retention
tool. For a specific conversation use `delete_thread(thread_id)`; for a single
user use `delete_user(user_id, cascade=True)`. Those operations preserve other
users and stores.
