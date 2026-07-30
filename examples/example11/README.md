# Example 11: Thread Chatbot Backend

Example 11 is a durable, user-scoped chatbot with a FastAPI backend and a
separate Next.js frontend.
Oracle Agent Memory persists the user and assistant messages in ADB-backed
threads. `langchain-oci` invokes OCI Generative AI to produce the assistant
answer from the persisted thread history and the model's pretrained knowledge.

## Operations

| Operation | API | Behaviour |
| --- | --- | --- |
| Create | `POST /api/users/{user_id}/threads` | Creates a new user-owned thread. |
| Recent list | `GET /api/users/{user_id}/threads?limit=10` | Lists up to ten populated threads, newest message first. |
| Resume | `GET /api/users/{user_id}/threads/{thread_id}` | Loads the complete ordered history of an owned thread. |
| Ask | `POST /api/users/{user_id}/threads/{thread_id}/questions` | Generates and persists a user question followed by the assistant answer. |

The question body is:

```json
{"question": "What did I ask earlier?"}
```

## Model and memory boundary

The backend obtains the selected thread's Oracle Agent Memory Context Card and
builds the model input from that card plus the current user question. The
visible prompt construction is in `backend/prompts.py`. It does not use RAG,
vector search, web lookup, tools, or external retrieval. The model can use only
that thread-derived context and its pretrained knowledge.

Thread messages are durable short-term conversation state in the store selected
by `MEMORY_STORE_ID`. Automatic Agent Memory extraction is disabled. ADB and
OCI credentials never reach an API response.

`user_id` scopes retrieval but is not authentication. A production backend
must derive user and tenant identity from the authenticated principal rather
than accepting a caller-controlled path value.

The demo API permits browser requests from any origin and does not allow
credentials, so a local frontend can be developed independently. This is not a
production CORS policy: deploy an explicit trusted-origin allow-list before
exposing the API outside a controlled development environment.

## OCI authentication and local run

`ChatOCIGenAI` uses OCI API-key authentication (`auth_type="API_KEY"`) and the
`DEFAULT` profile in `~/.oci/config`, the same local profile mechanism used by
the Agent Memory client. Configure the ADB settings, OCI profile, and
`MEMORY_STORE_ID` as documented in the [Quick Start](../../QUICKSTART.md).
Set `GENAI_REGION` and `GENAI_MODEL_ID` in `.env`; the region determines the
OCI Generative AI endpoint and the model ID selects the chat model.

```bash
conda activate oci-agentmemory-blueprint
pip install -r examples/example11/backend/requirements.txt
./examples/example11/backend/start_server.sh
```

The script binds to `127.0.0.1:8001` by default. Set `EXAMPLE11_API_HOST` or
`EXAMPLE11_API_PORT` before starting it to override the local bind address or
port. The API documentation is available at `http://127.0.0.1:8001/docs`.
The configured model must be available in `GENAI_REGION` and the profile
principal must be allowed to invoke it.

In a second terminal, start the ChatGPT-like frontend:

```bash
cd examples/example11/frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`. The username input maps to the backend `user_id`;
applying a new username clears the current chat and loads that user's recent
threads. `NEXT_PUBLIC_API_URL` defaults to `http://127.0.0.1:8001` and can be
set when the backend is served elsewhere.
