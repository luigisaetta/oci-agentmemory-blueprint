# Example 06: List a User's Populated Threads

## Purpose

Example 06 lists the conversation threads that contain at least one persisted
message for a selected `user_id`. Results are ordered by the newest message in
each thread, newest first. It is useful for presenting recent conversations
after the application has already authenticated the user.

The default user is `user1`, which lets the example inspect the sample data
created by [Example 05](../example05/README.md). Supply `--user-id` to inspect
another user scope.

## How thread discovery works

Oracle Agent Memory does not provide a supported client-level API for listing
threads in this example's SDK version. The example therefore wraps a temporary
private-store workaround in `list_populated_threads`:

```python
messages = client._store.list(
    record_type="message",
    user_id=user_id,
    limit=None,
)
thread_ids = {
    message.thread_id
    for message in messages
    if message.thread_id is not None
}
```

It then finds the most recent timestamp among each thread's messages and sorts
the thread IDs in descending order. When two threads have the same newest
timestamp, their IDs provide a stable secondary ordering.

Only threads with messages appear. Empty threads cannot be discovered by this
message-based workaround. The private `_store` attribute is version-sensitive:
replace this implementation with a supported Oracle Agent Memory thread-list
API when one is available.

## Memory and security boundary

This is a read-only inspection of raw, short-term conversation messages held
in the ADB-backed store selected by `MEMORY_STORE_ID`. It does not retrieve or
create long-term memories, add messages, change retention, or delete data.
The displayed activity timestamp is the newest application message timestamp,
not a thread creation time.

`user_id` scopes retrieval but does not authenticate a caller. In production,
derive it from the authenticated principal and enforce user and tenant
authorization before calling the listing function. Do not accept an arbitrary
user ID from an untrusted client.

## Run the example

Configure ADB, the OCI profile, and `MEMORY_STORE_ID` as described in the
[Quick Start](../../QUICKSTART.md), then run from the repository root:

```bash
conda activate oci-agentmemory-blueprint
python -m examples.example06.example06
```

To list another user scope:

```bash
python -m examples.example06.example06 --user-id customer_123
```

The command logs one `thread_id` and its latest-message timestamp per result,
or reports that no populated thread exists for the requested user. The ADB
connection pool closes on both success and handled failure.
