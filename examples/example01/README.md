# Example 01: Create a Memory Client and Add Thread Messages

## Run the example

Complete the repository [Quick Start](../../QUICKSTART.md) first, including the
ADB wallet, the repository-root `.env` file, and the OCI profile in
`~/.oci/config`. Then run this command from the repository root:

```bash
conda activate oci-agentmemory-blueprint
python -m examples.example01.example01
```

The command creates an Oracle Agent Memory client backed by Oracle ADB, creates
a thread, and adds two sample messages. Oracle Agent Memory generates the
thread ID and the example logs it. Both messages receive the UTC timestamp
generated immediately before insertion.

## What the example shows

Example 01 is a small end-to-end starting point for using Oracle Agent Memory.
It demonstrates three steps:

1. **Create an Agent Memory client.** `create_memory_store` creates
   `OracleAgentMemory` with an ADB connection pool, an OCI embedder, an OCI LLM,
   and the `OAM_` memory-store ID. The ADB and OCI configuration helpers are in
   [`common.py`](../../common.py) so future examples can reuse them.
2. **Create a thread.** `memory.create_thread` creates a conversation boundary
   for `user_123` and `agent_456`. Oracle Agent Memory generates the thread ID;
   the example records it in the log for later retrieval or inspection.
3. **Add messages.** `thread.add_messages` appends a user preference and an
   assistant acknowledgement, then logs the persisted message IDs. The example
   uses the synchronous API because this short-lived command has no independent
   work to perform before it closes the ADB connection pool.

## Read the logs

At `INFO` level, the application and Oracle Agent Memory components expose the
execution sequence. A typical run contains:

1. `Created connection pool` — the wallet-based ADB pool is ready.
2. `Successfully connected to Agent Memory` — the `OracleAgentMemory` client
   is configured and the persistence boundary is available.
3. `Created thread: ...` — the conversation state has a server-generated ID.
4. Internal loggers may report LLM generation, embeddings, searches, and ADB
   writes as those operations complete.
5. `Added 2 messages to the thread: ...` — the append completed and returned
   persisted message IDs.

The exact internal log sequence depends on the SDK version, configured models,
and whether memory extraction is due. Treat exception stack traces and OCI or
database details as sensitive diagnostic output; do not copy them to shared
logs or tickets.

## Asynchronous memory extraction

The example enables automatic long-term-memory extraction in background mode:

```python
MemoryExtractionConfig(
    extract_memories=True,
    extraction_mode=MemoryExtractionMode.BACKGROUND,
)
```

Extraction can require LLM generation, embedding, vector search, and further
ADB writes. Background mode keeps that derived-memory work off the critical
path after the raw thread messages are persisted.

| Benefit | Trade-off |
| --- | --- |
| Lower latency after the raw messages are stored. | Extracted memories can appear later than their source messages. |
| Better responsiveness for interactive agent turns. | A retrieval immediately after append can observe stale derived memory. |
| LLM and embedding work does not hold up the raw message append. | If background work cannot be scheduled or the process stops, extraction can be delayed or may not complete. |

For a production service, keep the process alive long enough to monitor
background work and handle failures. If a workflow must use an extracted memory
immediately, configure inline extraction or wait for the required processing
before retrieving memory.
