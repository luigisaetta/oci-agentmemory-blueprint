# Example 11 chatbot backend

## Scope

Add the FastAPI backend for Example 11, a stateful chatbot that stores each
user and assistant message in an Oracle Agent Memory thread backed by ADB. A
future frontend will consume this API but is not part of this change.

## Behaviour

* The backend uses `langchain-oci` `ChatOCIGenAI` with `auth_type="API_KEY"`
  and the `DEFAULT` OCI profile. This reuses the OCI API-key authentication
  configuration used by the local Agent Memory examples; no key material is
  exposed through the API.
* It creates one reusable LangChain OCI chat-model client per process. Its
  endpoint region is loaded from `GENAI_REGION` and its model ID from
  `GENAI_MODEL_ID` in `.env` through a validated shared `common.py` helper.
* `POST /api/users/{user_id}/threads` creates a user-owned thread.
* `GET /api/users/{user_id}/threads?limit=10` returns at most ten populated
  threads, ordered by their latest message descending, with ID, latest-message
  timestamp, and message count.
* `GET /api/users/{user_id}/threads/{thread_id}` resumes an owned thread and
  returns its complete ordered message history.
* `POST /api/users/{user_id}/threads/{thread_id}/questions` validates that the
  thread belongs to the selected user; obtains its Oracle Agent Memory Context
  Card; builds the model prompt from that card and the new user question; then
  streams generated text as server-sent events. After a successful stream it
  persists the question and complete assistant answer in that order and emits a
  completion event.
* The root-level `chat_prompts.py` module owns the visible, deterministic prompt construction.
  The XML Context Card is passed without additional wrapper tags and marked as
  untrusted reference material, while the current question remains a separate
  user message.
* Shared populated-thread discovery is imported from root-level
  `agent_memory.py`; Example 11 does not depend on another example module.
* The model receives only the Context Card derived from persisted thread state
  and its pretrained knowledge. This example performs no retrieval-augmented
  generation, vector search, web lookup, tool use, or external knowledge
  retrieval.
* Automatic Oracle Agent Memory extraction is disabled. Threads are durable
  short-term conversation state, not derived long-term memory.
* The demo enables CORS for all origins without credentials so a future local
  frontend can call the API. Production deployments must replace this with an
  explicit allow-list of trusted frontend origins.
* `backend/start_server.sh` starts the FastAPI server in reload mode from any
  working directory. `EXAMPLE11_API_HOST` and `EXAMPLE11_API_PORT` optionally
  override its default `127.0.0.1:8001` bind address.
* FastAPI creates one ADB connection pool at process startup, stores it in
  application state, and closes it at process shutdown. Each operation creates
  its own Agent Memory client using that shared pool. The backend maps invalid
  input to 400, out-of-scope threads to 404, and configuration, model, or
  persistence failures to 503 without leaking credentials or internal errors.

## Dependencies and testing

Add `langchain-oci` to `environment.yml` and the example backend requirements.
Unit tests must mock the ADB/Agent Memory and LangChain OCI boundaries, proving
thread ordering and truncation, ownership, model history construction,
user/assistant persistence order, one-pool-per-process lifecycle, errors, and
cleanup.

## Frontend

Add a separate Next.js frontend in `examples/example11/frontend/` that consumes
the FastAPI API. It provides a ChatGPT-like layout with a persistent left
sidebar and central chat panel.

* The top sidebar area contains a `username` input mapped directly to the API
  `user_id`, an Apply button, and a New Thread action.
* The bottom sidebar lists the selected user's recent populated threads. A
  click resumes its history through the backend API.
* The central panel displays chronological `user` and `assistant` messages and
  submits questions to the selected thread. The send control displays progress
  while the model is working and prevents duplicate submissions.
* Assistant content is rendered as untrusted Markdown with GitHub-Flavored
  Markdown support, including headings, tables, lists, and code blocks. User
  content remains plain text.
* Applying a different username clears the selected thread, prior messages,
  input, and visible errors before loading that user's thread list.
* `NEXT_PUBLIC_API_URL` optionally overrides the default API URL
  `http://127.0.0.1:8001`.
* The chat composer sends on Enter and adds a newline on Shift+Enter. It shows
  a spinner until the first streamed assistant token arrives, then incrementally
  renders the Markdown answer.
