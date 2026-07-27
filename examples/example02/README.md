# Example 02: Build a Context Card from a Stored Conversation

## Purpose

Example 02 shows how Oracle Agent Memory turns persisted conversation state
into a compact **Context Card**. The card contains the topics, summary, useful
derived information, and recent messages needed to continue a conversation
without passing the complete thread history to an LLM.

The example uses a fixed customer-support conversation about a delayed package:
five customer requests and five support replies. It is deliberately small and
contains no real customer data.

## Flow

```text
10 customer-support messages
        │
        ▼
Oracle Agent Memory thread persisted in Oracle ADB
        │
        ▼
Context Card: topics + summary + relevant information + recent messages
        │
        ▼
card.content available as prompt_context for a subsequent LLM turn
```

The example creates an ADB-backed Agent Memory client and thread, then calls
`thread.add_messages(messages)` to persist the raw conversation state. It
subsequently calls `thread.get_context_card(...)` and assigns `card.content`
to `prompt_context`.

Example 02 stops at that boundary: it makes the compact context available for
the next LLM prompt but does not invoke an LLM itself. An application can add
`prompt_context` to its next agent prompt alongside the new user request.

## Run the example

Complete the repository [Quick Start](../../QUICKSTART.md) first, including
the ADB wallet, the repository-root `.env` file, and the OCI profile in
`~/.oci/config`. Then run this command from the repository root:

```bash
conda activate oci-agentmemory-blueprint
python -m examples.example02.example02
```

The log reports the generated thread ID, the number of persisted messages, and
the generated Context Card. The fixed conversation and the function that turns
it into Agent Memory `Message` objects are in [`messages.py`](messages.py).

## Context Card retrieval

After inserting the conversation, the example retrieves the card with:

```python
card = thread.get_context_card(
    max_relevant_results=10,
    min_relevant_results_by_type={
        "preference": 1,
        "guideline": 1,
    },
)
prompt_context = card.content
```

`max_relevant_results` limits the amount of relevant derived information that
the card can include. `min_relevant_results_by_type` requests representation
for the named memory types when relevant memories are available. The Context
Card is still useful when `relevant_information` is empty: its summary, topics,
and recent messages retain the compact conversation state needed for a follow-up
turn.

## Generated Context Card

This output was generated from the example conversation. The `topics` and
`summary` capture the overall support case, while `recent_messages` preserves
the latest raw turns. In a production system, treat both the stored messages
and the generated card as governed customer data.

```xml
<context_card>
  <topics>
    <topic>refund or alternative options</topic>
    <topic>updated delivery date</topic>
    <topic>out-for-delivery notification</topic>
    <topic>package delayed</topic>
    <topic>order ord-2048</topic>
    <topic>order kept open</topic>
    <topic>event urgency</topic>
  </topics>
  <summary>
    The user reported a missed delivery for order ORD-2048 and asked for an updated delivery date and notification details. The assistant explained a weather delay with a new expected delivery tomorrow, confirmed an out-for-delivery email alert, and outlined options if the package does not arrive in time, keeping the order open. The user confirmed they will wait for the update.
  </summary>
  <relevant_information></relevant_information>
  <recent_messages>
    <message>
      <timestamp>2026-07-27T09:25:04.720123Z</timestamp>
      <role>assistant</role>
      <content>Yes. We will send an email with tracking details when the package is out for delivery.</content>
    </message>
    <message>
      <timestamp>2026-07-27T09:25:04.720123Z</timestamp>
      <role>user</role>
      <content>I need the item for an event. What happens if it does not arrive tomorrow?</content>
    </message>
    <message>
      <timestamp>2026-07-27T09:25:04.720123Z</timestamp>
      <role>assistant</role>
      <content>If it misses the updated date, contact us and we will review delivery options or a refund.</content>
    </message>
    <message>
      <timestamp>2026-07-27T09:25:04.720123Z</timestamp>
      <role>user</role>
      <content>Thank you. Please keep the order open while I wait for the update.</content>
    </message>
    <message>
      <timestamp>2026-07-27T09:25:04.720123Z</timestamp>
      <role>assistant</role>
      <content>You are welcome. Your order remains open, and we will continue monitoring the delivery.</content>
    </message>
  </recent_messages>
</context_card>
```

## Memory lifecycle and trade-offs

The thread is the short-term conversation state. Its persistence boundary is
Oracle Agent Memory backed by ADB: `add_messages` returns persisted message IDs
before the connection pool is closed. The Context Card is a compact retrieval
view over that stored state; it does not replace the underlying thread.

The example enables background extraction for long-term memories. Raw messages
are therefore persisted before derived-memory extraction necessarily completes.
This reduces the latency of inserting a conversation, but a Context Card
requested immediately afterwards can have empty or incomplete
`relevant_information`. Workflows that require freshly extracted long-term
memory must wait for that processing or use an appropriate synchronous
extraction strategy.

The example's fixed customer and agent IDs make the ownership boundary visible.
Production applications should derive equivalent user, agent, and tenant scope
from authenticated identities, apply retention and deletion policies, and avoid
including sensitive customer data in logs or prompts unless authorised.
