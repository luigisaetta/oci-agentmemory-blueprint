# Example 02 customer-support thread

## Scope

Add a self-contained customer-support conversation example that persists ten
English messages in an Oracle Agent Memory thread backed by Oracle ADB, then
retrieves a compact Context Card from that stored conversation. The example
reuses the configuration helpers from `common.py` and duplicates the small
memory-store setup from Example 01 to keep the example readable on its own.
The fixed conversation and its message builder are kept in the local
`examples/example02/messages.py` module so the persistence flow remains easy
to follow.

The example loads the shared `MEMORY_STORE_ID` from the process environment or
repository-root `.env` so it uses the same managed Agent Memory objects as the
other examples.

## Behaviour

* Importing the module has no ADB, OCI, or Oracle Agent Memory side effects.
* The command creates an ADB connection pool, creates an `OracleAgentMemory`
  store, and creates one thread for a fixed example customer and support agent.
* The thread receives exactly ten messages: five customer requests and five
  plausible support-agent replies in English about a delayed package.
* All messages receive one UTC timestamp generated immediately before the
  insertion. The example uses synchronous insertion and logs the number of
  persisted messages and returned IDs.
* After persistence, the command retrieves a Context Card with
  `thread.get_context_card`, logs its content, and assigns the compact card
  content to `prompt_context` for use by a subsequent LLM turn. The example
  does not invoke that subsequent LLM turn.
* Automatic long-term-memory extraction runs in background mode. The raw
  conversation is persisted before derived memories are necessarily available.
* The ADB pool closes whether the command succeeds or fails. Configuration,
  validation, and unexpected errors result in a non-zero exit status and a
  concise, non-sensitive status message followed by a local stack trace.

## Memory boundary

The thread is short-term conversation state for the fixed example customer and
agent. Oracle Agent Memory persists that raw state in ADB. The Context Card is
a compact retrieval view containing a summary, topics, relevant information,
and recent messages for a later LLM turn. Background extraction may later
create derived long-term memories, so an immediate card retrieval must not
assume that extracted information is available.

## Acceptance criteria

* Unit tests verify that the conversation contains exactly ten alternating
  `user` and `assistant` messages and that their content is in English.
* Unit tests verify successful insertion, shared UTC timestamps, generated
  thread IDs, failure handling, and connection-pool closure.
* Unit tests verify Context Card retrieval and that its content is prepared for
  the subsequent LLM prompt.
* Documentation explains execution, the persistence boundary, and the
  background-extraction consistency trade-off.
* Documentation includes the generated Context Card reference for the fixed
  example conversation.
* No secrets or customer-sensitive values are logged or committed.
