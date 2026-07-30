# Example 06 user thread listing

## Scope

Add an Oracle Agent Memory example that lists the populated conversation
threads for one supplied user. The list is ordered by the most recent message
in each thread, newest first.

## Behaviour

* Importing the example must not read configuration, connect to ADB, invoke
  OCI, or create database objects.
* The command accepts `--user-id`; it defaults to the non-sensitive example
  value `user1` so it can inspect data created by Example 05.
* It reuses the shared ADB, OCI profile, and `MEMORY_STORE_ID` helpers from
  `common.py`.
* It creates an Agent Memory client with automatic memory extraction disabled.
* A dedicated function wraps the currently necessary private-store workaround:
  it calls `client._store.list(record_type="message", user_id=user_id,
  limit=None)` and considers only messages whose `thread_id` is not `None`.
* A thread is listed only when it has at least one persisted message. Empty
  threads are intentionally absent because the workaround discovers threads
  through message records.
* The function determines each listed thread's activity time from the latest
  message timestamp and returns entries in descending activity order. Ties are
  resolved deterministically by thread ID.
* The command logs each thread ID and its latest-message timestamp, or a clear
  informational message when no populated thread exists for the user.
* The ADB pool closes after success and all handled failures.

## Persistence and security boundary

The example reads raw `message` records from the ADB-backed Agent Memory
store. It does not retrieve long-term memories and does not modify messages,
threads, or retention data. Ordering reflects application message timestamps,
not a thread creation timestamp.

`user_id` is a retrieval scope, not authentication. A production application
must derive it from the authenticated principal and enforce tenant and user
authorization before invoking this workaround. The use of the private `_store`
attribute is version-sensitive; applications should replace it when Oracle
Agent Memory exposes a supported thread-listing API.

## Acceptance criteria

* Unit tests verify the private-store call arguments, exclusion of messages
  without a thread ID, reverse chronological ordering, deterministic tie
  handling, and the empty result.
* Unit tests verify CLI user-ID handling, client configuration, logging, and
  cleanup after success and failure.
* Documentation explains the message-only limitation, persistence boundary,
  ordering definition, security limitation, and private-API trade-off.
