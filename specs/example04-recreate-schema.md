# Example 04 recreate managed schema

## Scope

Add a small, explicit maintenance example that resets the Oracle Agent Memory
database objects belonging to the memory store selected by `MEMORY_STORE_ID`.
It is for a
development or approved maintenance cleanup, not for normal application
startup.

## Behaviour

* Importing the example must not open an ADB connection, read the OCI profile,
  invoke OCI, or issue database DDL.
* The command must reuse the shared ADB pool and OCI-profile configuration
  helpers from `common.py`.
* It must initialise `OracleAgentMemory` with the configured shared memory
  store ID and `SchemaPolicy.RECREATE`.
* The example must disable automatic memory extraction because it writes no
  messages and needs no LLM.
* Successful initialisation must log that managed objects were recreated, then
  close the Agent Memory instance and ADB pool.
* Configuration, validation, and unexpected errors must produce a concise,
  non-sensitive message, a local stack trace, a non-zero exit status, and pool
  cleanup.

## Safety and persistence boundary

`SchemaPolicy.RECREATE` drops and recreates the managed Oracle Agent Memory
objects for the configured store. This permanently removes its persisted
threads, messages, memories, profiles, and managed retrieval data. It must not
be used against a production store without an approved backup and maintenance
procedure.

The example does not issue generic `DROP TABLE` or `DROP INDEX` statements and
does not affect unrelated objects in the database schema. The database account
must have the privileges required for the SDK to manage its objects.

## Acceptance criteria

* Unit tests verify the configured store ID, `SchemaPolicy.RECREATE`, disabled
  extraction, successful closure, and ADB-pool closure after success and
  failure.
* Documentation describes the destructive boundary, execution command,
  prerequisites, recovery limitation, and required return values.
* The root example index and changelog link to the example.
