# Example 05 user-scoped message search

## Scope

Add a readable Oracle Agent Memory example that demonstrates how client-level
message retrieval is isolated by `user_id`. The example creates two separate
customer-support threads in the same configured ADB-backed memory store and
searches them using one deliberately overlapping delivery-delay query.

## Behaviour

* Importing the example must not read configuration, connect to ADB, invoke
  OCI, or create database objects.
* The example reuses the shared ADB, OCI profile, and `MEMORY_STORE_ID`
  configuration helpers from `common.py`.
* It creates one thread for `user1` and one thread for `user2`, both associated
  with the fixed support agent ID `support_agent`.
* Each thread receives five English customer-support messages, for ten stored
  messages in total. Both conversations contain delivery-delay and tracking
  language so the same query is relevant to both users.
* Automatic memory extraction is disabled. The example is about raw persisted
  message retrieval and should not create derived long-term memories.
* It runs the same query three times for message records:
  1. without a `user_id`, which the client API rejects with `ValueError`;
  2. with `user_id="user1"`;
  3. with `user_id="user2"`.
* The command logs the expected unscoped-query rejection and the content,
  message role, and scoped user ID of each returned scoped result. It does not
  claim that relevance ranking is deterministic.
* The ADB pool closes after success and all handled failures.

## Isolation and persistence boundary

`user_id` is an ownership and retrieval-isolation scope, not an authentication
mechanism. A production application must derive the requested user ID from its
authenticated principal and must not accept it unchecked from a caller.

The explicit unscoped client search is intentionally rejected by Oracle Agent
Memory. This prevents one client-level search from returning records belonging
to multiple users. The two scoped searches can each return only the messages
owned by their selected user, even though both user conversations use similar
language and are stored in the same ADB-backed memory store.

## Acceptance criteria

* Unit tests verify the two thread scopes, ten message roles and contents, the
  three search calls, expected unscoped-search handling, and resource cleanup.
* Unit tests verify that both scoped calls use the same query, restrict results
  to `record_types=["message"]`, and use `user1` and `user2` respectively.
* Documentation explains the persistence boundary, the rejected unscoped
  search, the security limitation of `user_id`, and ranking variability.
