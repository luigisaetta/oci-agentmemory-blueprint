# Example 01: Asynchronous Thread Messages

## Run the example

Complete the repository [Quick Start](../../QUICKSTART.md) first, including the
ADB wallet, the repository-root `.env` file, and the OCI profile in
`~/.oci/config`. Then run this command from the repository root:

```bash
conda activate oci-agentmemory-blueprint
python -m examples.example01.example01
```

The command creates an Oracle Agent Memory store backed by Oracle ADB, creates
a thread, and appends two sample messages. Oracle Agent Memory generates the
thread ID and the example logs it. The message timestamp is generated in UTC
immediately before the insert.

## What the example demonstrates

The example keeps the ADB and OCI configuration boundary in
[`common.py`](../../common.py). It then configures Oracle Agent Memory with an
OCI embedder and LLM, creates a thread for one user and agent, and appends a
user preference and an assistant acknowledgement.

The thread-message write uses `add_messages_async`. The application logs that
the messages have been queued immediately before awaiting their result. The
example awaits the result before closing the ADB connection pool; this is
required for a short-lived command-line program to avoid cancelling the write.

## Reading the logs

With the example logger at `INFO`, the output shows both application milestones
and internal Oracle Agent Memory operations. A typical sequence is:

1. `Created connection pool` — the wallet-based ADB pool is available.
2. `Successfully connected to Agent Memory` and `Created thread` — the memory
   store and its conversation boundary are ready.
3. `Queued 2 messages for asynchronous insertion` — the application is about
   to await the asynchronous write; the final write has not completed yet.
4. Oracle Agent Memory loggers report operations such as LLM generation,
   embedding, search, and database writes. These entries identify the internal
   component that completed each step.
5. `Added 2 messages to the thread` — the asynchronous write returned the
   persisted message IDs.

The exact internal log sequence depends on the SDK version, configured models,
and whether a memory extraction is due for the thread. Never copy exception
stack traces, OCI details, wallet paths, or database details into shared logs
or tickets.

## Why memory extraction runs in the background

The example enables automatic extraction and configures:

```python
MemoryExtractionConfig(
    extract_memories=True,
    extraction_mode=MemoryExtractionMode.BACKGROUND,
)
```

Extracting long-term memories may require LLM calls, embedding requests, vector
searches, and additional ADB writes. Running that work inline can make a thread
append take several seconds, even when the raw conversation message has already
been accepted. Background extraction lets the append return after the raw write
is complete and performs due extraction work separately.

This trade-off is deliberate:

| Benefit | Trade-off |
| --- | --- |
| Faster response after the raw thread message is persisted. | Extracted memories can appear later than the source message. |
| Lower latency for an interactive agent turn. | A query immediately after the append can observe stale derived memory. |
| Expensive LLM and embedding work is not on the critical message-write path. | If the background task cannot be scheduled or the process stops, extraction can be delayed or may not complete. |

For a production service, keep the process alive long enough to supervise
background work and monitor failures. For workflows that require a newly
extracted memory immediately, use inline extraction or explicitly wait for the
required processing before retrieving memory.
