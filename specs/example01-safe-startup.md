# Example 01 safe startup

## Scope

Make `examples/example01/example01.py` safe to import and predictable to run as
a command-line connectivity example. The example creates an Oracle Agent Memory
store backed by Oracle ADB and adds two sample messages to a named thread; it
does not change the configured models.

## Behaviour

* Importing the module must not read local configuration, open an ADB pool, call
  OCI, or create database objects.
* Shared helpers in `common.py` load and validate the required ADB settings
  from the repository-root `.env` file and create the ADB connection pool
  directly with `oracledb.create_pool`.
* The OCI configuration path must expand `~` before it is passed to the OCI SDK.
* The example must require the OCI settings used to initialise the embedder and
  LLM, including `compartment_id`.
* On success it creates `OracleAgentMemory`, reports a non-sensitive success
  message, adds sample messages to a named thread, and closes the ADB pool.
* Missing or invalid configuration and startup failures must produce a concise,
  non-sensitive error message and a non-zero exit status.

## Acceptance criteria

* Unit tests confirm that module import has no external side effects.
* Unit tests cover missing ADB settings, home-directory expansion for OCI
  configuration, successful startup, and pool closure on both success and
  failure.
* No password, wallet password, or private-key content is printed.
* Each run lets Oracle Agent Memory generate a thread ID and reports it after
  success. A `ValueError` identifies invalid thread identifiers or example
  message fields, without printing stored values.
* The sample messages use the UTC timestamp generated immediately before their
  insertion.
* The example logs when asynchronous message insertion is queued, then awaits
  completion before closing the ADB connection pool.
* Automatic memory extraction runs in background mode. Raw thread messages are
  persisted before due derived-memory extraction completes.
* Each startup failure logs a concise status message and its complete Python
  traceback for local troubleshooting.
