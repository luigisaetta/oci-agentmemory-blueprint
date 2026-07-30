# Example 10 Agent Memory Console

## Scope

Add a two-tier demonstration application: a FastAPI backend in
`examples/example10/backend/` and a Next.js frontend in
`examples/example10/frontend/`. It presents Oracle Agent Memory thread
features through a browser while keeping all OCI and ADB access on the server.

## Behaviour

* The browser supplies a user scope; the backend exposes only user-scoped
  thread, message, context-card, summary, and message-search operations.
* Users can create a thread, append `user` or `assistant` messages, list
  populated threads by their latest message descending, select a thread, and
  view its messages, summary, and Context Card.
* A message search requires `user_id` and searches only `message` records.
* Thread discovery uses the message-record workaround from Example 06; only
  threads with messages are listed.
* The API configures explicit local CORS origins through `EXAMPLE10_CORS_ORIGINS`.
  The Next.js development server explicitly permits local `127.0.0.1` HMR
  requests through `allowedDevOrigins`.
* The frontend navigation switches between distinct Recent Threads, Thread, and
  Search views; it does not merely scroll the current page.
* Summary and Context Card generation displays an in-progress state until the
  API responds. The XML-like Context Card is rendered as an expandable
  structured tree, with a raw-text fallback for malformed or non-XML content.
* `backend/start_server.sh` starts the FastAPI server from any working
  directory, using Uvicorn reload mode and optional `EXAMPLE10_API_HOST` and
  `EXAMPLE10_API_PORT` overrides.
* Oracle/ADB configuration remains server-side and uses `common.py` helpers.
  No browser bundle, frontend environment variable, log, or API response may
  expose credentials or OCI profile values.
* The backend creates one connection pool per request and always closes it.
  Automatic long-term memory extraction runs in background mode after message
  writes, so derived memories may not be immediately available. An OCI LLM is
  also configured for summary and Context Card generation.

## API

* `GET /health`
* `GET /api/users/{user_id}/threads`
* `POST /api/users/{user_id}/threads`
* `POST /api/users/{user_id}/threads/{thread_id}/messages`
* `GET /api/users/{user_id}/threads/{thread_id}/messages`
* `GET /api/users/{user_id}/threads/{thread_id}/insights`
* `GET /api/users/{user_id}/messages/search?q=...`

The backend returns 400 for invalid user IDs or message input, 404 for an
unknown or out-of-scope thread, and 503 for safe configuration or persistence
failures. It does not expose internal exception details.

## Acceptance criteria

* Backend unit tests cover user validation, user-scoped thread ordering,
  creation, message insertion, selected-thread isolation, summary/context-card
  serialization, search scoping, errors, and connection-pool cleanup.
* The frontend has a left navigation rail and usable loading, empty, error, and
  success states for all listed workflows.
* Documentation covers local setup, separate frontend/backend commands,
  persistence and security boundaries, CORS configuration, and the private API
  trade-off.
