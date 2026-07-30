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
uvicorn examples.example10.backend.app:app --reload
```

In a second terminal:

```bash
cd examples/example10/frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Set `NEXT_PUBLIC_API_URL` only when the API is
not at `http://localhost:8000`. `EXAMPLE10_CORS_ORIGINS` defaults to the local
Next.js origin; set it to a comma-separated explicit origin allow-list for
other deployments.

## Persistence and security

Messages and thread state are persisted in the store selected by
`MEMORY_STORE_ID`; automatic long-term memory extraction is disabled. Summary
and Context Card are calculated from the selected persisted thread. The
browser-provided user ID is only a demo retrieval scope, not authentication:
production systems must derive user and tenant scope from the authenticated
principal. The backend opens and closes an ADB pool for every request.

Thread discovery is message-based because this SDK version has no supported
client-level list operation. Replace that internal implementation when a public
thread-list API becomes available.
