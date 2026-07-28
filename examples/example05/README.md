# Example 05: Search Customer-Support Messages by User Scope

## Purpose

Example 05 shows the effect of `user_id` scoping when searching raw Oracle
Agent Memory messages. It creates two customer-support threads in the same
ADB-backed memory store: one owned by `user1` and one owned by `user2`. Each
thread receives six messages about delayed deliveries and tracking updates.
The twelve sample messages have distinct UTC timestamps, one second apart, in
their persisted chronological order.

The fixed query, `delivery delay tracking update`, is intentionally relevant to
both conversations. This makes the isolation boundary visible: the search for
`user1` can return only `user1` messages, and the equivalent search for
`user2` can return only `user2` messages.

## The three searches

The example makes three client-level calls using the same query:

1. A call without `user_id`. Oracle Agent Memory rejects it with `ValueError`.
   The example logs that expected rejection rather than treating it as a
   successful cross-user search.
2. A call scoped to `user1` with `record_types=["message"]`.
3. A call scoped to `user2` with `record_types=["message"]`.

Before the calls, the command logs the exact query text so the shared search
input is visible alongside the three different scope outcomes.

Each logged search result includes the persisted message timestamp. This is the
application event time supplied with `Message`, rather than a database row
creation time that may be shared by messages inserted in the same batch.

Client-level Oracle Agent Memory search requires an explicit user scope. This
is an intentional protection against cross-user retrieval. The result order is
based on relevance and can vary with embeddings, stored data, and database
search configuration; use the logged `user_id` and content to observe the
scope, not an exact ranking.

## Memory and security boundary

The two threads are short-term persisted conversation state. Their raw messages
are stored in the ADB-backed Agent Memory store selected by `MEMORY_STORE_ID`.
Automatic memory extraction is disabled, so this example does not add derived
long-term memories and its searches contain only raw `message` records.

`user_id` is an ownership and retrieval filter, not authentication. A
production backend must take the user ID from the authenticated principal and
must not let a caller select another user's scope.

## Run the example

Configure ADB, the OCI profile, and `MEMORY_STORE_ID` as described in the
[Quick Start](../../QUICKSTART.md), then run from the repository root:

```bash
conda activate oci-agentmemory-blueprint
python -m examples.example05.example05
```

The example logs generated thread IDs only indirectly through message IDs and
logs fixed, non-sensitive sample text. The ADB connection pool closes on both
success and failure.

## Reset before running again

Every execution creates two new threads and persists another twelve sample
messages. If you want to avoid accumulating duplicate sample conversations,
reset the Agent Memory store before running this example again.

[Example 04](../example04/README.md) can perform that reset:

```bash
python -m examples.example04.example04
```

This operation is destructive. It recreates all Oracle Agent Memory-managed
objects for the store selected by `MEMORY_STORE_ID`; it does not delete only
the messages created by Example 05. It therefore removes every thread, message,
memory, profile, and managed retrieval object in that store. Do not run it
against a store that contains data you need to retain.
