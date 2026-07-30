# Example 10: Agent Memory Console

Example 10 is a local browser console for the ADB-backed Oracle Agent Memory
patterns introduced by the earlier examples. `backend/` contains FastAPI APIs;
`frontend/` contains the Next.js interface. The browser never receives ADB,
OCI-profile, or store configuration values.

## Features

The left sidebar selects the user scope. The workspace can create a thread,
append `user` and `assistant` messages, display populated threads in descending
latest-message order, select a thread, generate its summary and Context Card,
and search only that user's raw messages. An empty thread is not shown in the
list until it has a message.

## Run locally

From the repository root, configure `.env`, the OCI profile, and
`MEMORY_STORE_ID` as in the [Quick Start](../../QUICKSTART.md). Install the
backend additions and start the API:

```bash
conda activate oci-agentmemory-blueprint
pip install -r examples/example10/backend/requirements.txt
./examples/example10/backend/start_server.sh
```

The script binds to `127.0.0.1:8000` by default. Set `EXAMPLE10_API_HOST` or
`EXAMPLE10_API_PORT` before invoking it when a different local bind address or
port is required.

In a second terminal:

```bash
cd examples/example10/frontend
npm install
npm run dev
```

The frontend requires Node.js 20.9 or later.

Open `http://localhost:3000`. Set `NEXT_PUBLIC_API_URL` only when the API is
not at `http://localhost:8000`. `EXAMPLE10_CORS_ORIGINS` defaults to both
`http://localhost:3000` and `http://127.0.0.1:3000`; set it to a comma-separated
explicit origin allow-list for other deployments. The Next.js development configuration also permits
`127.0.0.1` for its local HMR resources; restart `npm run dev` after changing
the configuration.

## Persistence and security

Messages and thread state are persisted in the store selected by
`MEMORY_STORE_ID`. Automatic long-term memory extraction runs in the background
after a message write, so derived memories can appear after the UI has already
returned a successful response. Summary and Context Card are calculated from
the selected persisted thread using the configured OCI LLM. The
browser-provided user ID is only a demo retrieval scope, not authentication:
production systems must derive user and tenant scope from the authenticated
principal. The backend opens and closes an ADB pool for every request.

Generating Summary and Context Card can take time. The UI displays a loading
indicator while the request is in progress, then renders the XML-like Context
Card as an expandable tree so its sections and values are easy to inspect.

Thread discovery is message-based because this SDK version has no supported
client-level list operation. Replace that internal implementation when a public
thread-list API becomes available.
