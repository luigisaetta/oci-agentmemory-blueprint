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
  persists the question and generated assistant answer in that order before
  returning the answer.
* `backend/prompts.py` owns the visible, deterministic prompt construction.
  The Context Card is marked as untrusted reference material, while the current
  question remains a separate user message.
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
* The backend closes its ADB pool after each request. It maps invalid input to
  400, out-of-scope threads to 404, and configuration, model, or persistence
  failures to 503 without leaking credentials or internal errors.

## Dependencies and testing

Add `langchain-oci` to `environment.yml` and the example backend requirements.
Unit tests must mock the ADB/Agent Memory and LangChain OCI boundaries, proving
thread ordering and truncation, ownership, model history construction,
user/assistant persistence order, errors, and cleanup.
