# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Changed

* Made the Oracle Agent Memory connection example safe to import and improved
  its local configuration validation and shutdown behaviour.
* Simplified the example startup flow by creating the ADB connection pool
  directly with `oracledb.create_pool`.
* Moved shared ADB and OCI configuration helpers into `common.py` for reuse by
  future examples.
