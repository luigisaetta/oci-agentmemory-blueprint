# Oracle Agent Memory Blueprint for Oracle ADB

[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://pylint.readthedocs.io/)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-0A9EDC)](https://docs.pytest.org/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

Build AI agents that remember the right things, for the right length of time, in the right scope.

This repository is a practical blueprint for adopting **Oracle Agent Memory**, backed by **Oracle Autonomous Database (ADB)**. It collects focused examples, reusable patterns, and implementation guidance for adding durable short-term and long-term memory to enterprise AI agents.

The goal is simple: help teams move from a stateless proof of concept to agents that can retain context, learn useful preferences, and retrieve relevant knowledge without turning memory into an opaque or risky subsystem.

## Quick Start

Start with the [Quick Start](QUICKSTART.md) to configure a local ADB wallet,
the required `.env` settings, and the OCI profile used by the examples.
Review [Best Practices](BEST_PRACTICES.md) before selecting a memory-store
identifier or sizing a production ADB connection pool.

## Why agent memory matters

Large language models are powerful within a single interaction, but they do not automatically retain the context that makes an agent genuinely useful over time. Enterprise agents often need to remember a conversation, a user preference, an unresolved task, or a validated fact while keeping data isolated, traceable, and governed.

Oracle Agent Memory and Oracle ADB provide a foundation for persisting and retrieving that information outside the model. This blueprint shows how to apply that capability deliberately, with clear memory boundaries and production-minded practices.

## What you will find here

The repository is being built as a set of progressive, self-contained examples. It will cover:

* **Short-term memory** — retain working context across turns or agent executions.
* **Long-term memory** — store and retrieve durable user preferences, facts, and learned context.
* **Memory design patterns** — decide what to remember, when to retrieve it, and when it should expire.
* **Oracle ADB integration** — use Autonomous Database as the external store for enterprise-grade persistence.
* **Isolation and governance** — design for users, sessions, tenants, sensitive data, retention, and deletion.
* **Testing and operations** — validate memory behaviour and handle failures without requiring live cloud resources for unit tests.
* **Production guidance** — configuration, security, observability, and deployment considerations for OCI.

Each example will explain its use case, architecture, configuration, expected behaviour, and the trade-offs behind its memory strategy.

## Examples

| Example | Description |
| --- | --- |
| [Example 01: Create a Memory Client and Add Thread Messages](examples/example01/README.md) | Creates an ADB-backed Agent Memory client, creates a thread, appends sample messages, and explains background memory extraction. |
| [Example 02: Build a Context Card from a Stored Conversation](examples/example02/README.md) | Persists a customer-support thread, retrieves its compact Context Card, and prepares it for a subsequent LLM turn. |
| [Example 03: Use Resource Principal with Oracle Agent Memory](examples/example03/README.md) | Uses OCI Resource Principal authentication for OCI Generative AI while retaining ADB-backed memory persistence. |
| [Example 04: Recreate an Oracle Agent Memory Schema](examples/example04/README.md) | Performs an explicit, destructive reset of the managed store selected by `MEMORY_STORE_ID` for development or approved maintenance. |
| [Example 05: Search Customer-Support Messages by User Scope](examples/example05/README.md) | Stores two overlapping support conversations and demonstrates rejected unscoped versus user-scoped message searches. |
| [Example 06: List a User's Populated Threads](examples/example06/README.md) | Lists the most recent conversation threads associated with a specified user. |
| [Example 10: Agent Memory Console](examples/example10/README.md) | Provides a FastAPI and Next.js UI for user-scoped threads, messages, summaries, Context Cards, and search. |
| [Example 11: Thread Chatbot](examples/example11/README.md) | Provides a FastAPI and Next.js chatbot that resumes ADB-backed threads and uses `langchain-oci` for contextual OCI model responses without RAG. |
| [ADB connection check](examples/test_adb_connections/test_db_connection.py) | Validates the local wallet-based ADB configuration with `SELECT 1 FROM dual` before running a memory example. |

## Who this is for

This blueprint is intended for AI application developers, solution architects, and platform teams building agents on Oracle Cloud Infrastructure. It is especially useful if you want a concrete starting point for memory-enabled agents while retaining control over where memory is stored and how it is used.

## Guiding principles

* **Memory is intentional.** Store only information that provides a clear future benefit.
* **Scope is explicit.** Separate session, user, tenant, and application memory to prevent leakage.
* **Retrieval is selective.** Bring back relevant context instead of indiscriminately injecting history into every prompt.
* **Data is governed.** Treat stored agent memory as enterprise data, with retention, deletion, and security requirements.
* **Examples stay practical.** Every pattern should be easy to understand, test, adapt, and operate.

## Repository status

The blueprint currently includes a local ADB connection check and six
progressive Oracle Agent Memory examples. Together, they cover creating an
ADB-backed memory client and thread, persisting conversation messages,
retrieving a Context Card for a subsequent LLM turn, using OCI Resource
Principal authentication for Generative AI, safely recreating a managed memory
store for approved maintenance, enforcing user-scoped raw-message search, and
listing a user's recent populated threads.

The examples make the persistence boundary, short-term conversation state,
background long-term-memory extraction, authentication, destructive
maintenance, and user-isolation trade-offs explicit. Further production
patterns will be added incrementally as they are implemented and verified.

## Contributing

Contributions should strengthen the adoption path for Oracle Agent Memory with Oracle ADB. Before adding an example or feature, review [AGENTS.md](AGENTS.md) for the repository conventions, documentation expectations, security requirements, and testing standards.

## License

This project is released under the [MIT License](LICENSE).
