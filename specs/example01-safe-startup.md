# Example 01 safe startup

## Scope

Make `examples/example01/example01.py` safe to import and predictable to run as
a command-line connectivity example. The example continues to create an Oracle
Agent Memory store backed by Oracle ADB; it does not add memory operations or
change the configured models.

## Behaviour

* Importing the module must not read local configuration, open an ADB pool, call
  OCI, or create database objects.
* Running the module loads and validates the required ADB settings from the
  repository-root `.env` file.
* The OCI configuration path must expand `~` before it is passed to the OCI SDK.
* The example must require the OCI settings used to initialise the embedder and
  LLM, including `compartment_id`.
* On success it creates `OracleAgentMemory`, reports a non-sensitive success
  message, and closes the ADB pool.
* Missing or invalid configuration and startup failures must produce a concise,
  non-sensitive error message and a non-zero exit status.

## Acceptance criteria

* Unit tests confirm that module import has no external side effects.
* Unit tests cover missing ADB settings, home-directory expansion for OCI
  configuration, successful startup, and pool closure on both success and
  failure.
* No password, wallet password, or private-key content is printed.
