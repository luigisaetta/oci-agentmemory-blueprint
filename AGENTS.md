# AGENTS.md

This repository contains a blueprint, examples, and implementation guidance for adopting Oracle Agent Memory in enterprise AI agents. Its focus is on managing short-term and long-term agent memory with Oracle Autonomous Database (Oracle ADB) as the external persistence layer.

## Repository purpose

Keep the repository focused on one goal: make it faster and safer to adopt Oracle Agent Memory with Oracle ADB through clear, practical, and production-aware examples.

All changes must preserve this purpose. Avoid adding unrelated agent frameworks, demos, deployment targets, or abstractions unless they are explicitly required by the specification being implemented.

## Language and documentation

* All documentation, source-code comments, and Markdown files must be written in English.
* Keep documentation practical, accurate, and close to the implementation.
* Explain the memory behaviour, persistence boundary, and trade-offs of every example.
* Document public behaviour whenever it changes.
* Update local execution and OCI deployment instructions whenever a change affects runtime behaviour.
* Do not claim support for an Oracle Agent Memory API, configuration option, or behaviour unless it is verified by the implemented example or authoritative documentation.

## Spec-driven development workflow

Follow this workflow for significant features, fixes, refactorings, deployment changes, and memory-persistence changes:

1. Read the relevant existing specification.
2. If no relevant specification exists, create one under `specs/` before implementation.
3. Review the specification for scope, behaviour, acceptance criteria, error handling, configuration, and test expectations.
4. Implement code according to the specification.
5. Add or update unit tests.
6. Run the relevant formatting, linting, testing, and coverage checks.
7. Update `CHANGELOG.md` when the change is significant.
8. Summarise what changed and which checks were run.

Code must not be generated for significant behaviour until the relevant specification exists and has clear acceptance criteria.

## Codex working rules

When working in this repository, Codex should:

* Inspect the existing project structure before editing.
* Prefer small, coherent changes over broad rewrites.
* Write code that a human can read, understand, and maintain; prefer clear,
  direct control flow over unnecessary abstraction.
* Reuse existing modules, helpers, configuration patterns, and test fixtures before adding new ones.
* Preserve user changes already present in the working tree.
* Avoid speculative changes that are not requested by the user or required by the specification.
* Do not create commits unless explicitly asked.
* Do not add production dependencies without a clear reason.
* Do not run destructive commands or discard existing changes unless explicitly requested.
* Do not hard-code secrets, tenancy-specific identifiers, database connection details, API keys, private endpoints, or local machine paths.
* When uncertain, document the assumption, leave a clear TODO, or ask for clarification.

## Python environment

Use the `oci-agentmemory-blueprint` Conda environment for local development and tests.

If an environment definition exists, prefer it for setup. If the environment already exists, activate `oci-agentmemory-blueprint` before running checks.

Do not assume globally installed Python packages are available.

## Required checks

Run the relevant checks before considering work complete.

At a minimum, use the project standard tools for:

* Python formatting with `black`.
* Python linting with `pylint`.
* Unit testing with `pytest`.
* Coverage reporting when tests or behaviour are affected.

The target unit test coverage is above 80 percent.

If a check cannot be run because the environment or dependencies are missing, state that clearly in the final summary and explain what prevented the check.

## Python code conventions

Every Python source file must start with a multiline header using this format:

```python
"""
Author: L. Saetta
Date last modified: YYYY-MM-DD
License: MIT
Description: Brief description of the responsibilities and functions contained in this file.
"""
```

Use the actual modification date when creating or updating a Python source file.

All generated Python code must include accurate docstrings for modules, classes, methods, and functions where applicable.

Docstrings must follow the Google Python docstring format and clearly describe purpose, arguments, return values, raised exceptions, and relevant side effects.

## Agent-memory design expectations

* Make the distinction between short-term memory, long-term memory, and conversation or execution state explicit.
* Document the memory lifecycle: creation, retrieval, update, retention, deletion, and recovery where applicable.
* Keep memory schemas, namespaces, user or tenant isolation, and retrieval behaviour visible and easy to audit.
* Prefer deterministic and testable agent behaviour in examples.
* Isolate Oracle Agent Memory and Oracle ADB integration from core agent logic where practical.
* Define and test the Oracle ADB persistence boundary with mocks or fakes.
* Explain how an example handles failures, retries, idempotency, and concurrent access when relevant.
* Do not include sensitive data in sample memories, prompts, logs, or test fixtures.

## OCI configuration and security

Never commit or hard-code API keys, private keys, passwords, OCI tenancy OCIDs, user OCIDs, compartment OCIDs, database credentials, private endpoints, local machine paths, or customer- and environment-specific identifiers.

Use environment variables, configuration files excluded from version control, or documented placeholders.

When adding configuration, document its variable name, purpose, whether it is required, a safe example value, and where it is used.

## Testing expectations

New functionality must include unit tests written with the project standard testing framework.

Tests should cover successful memory creation, retrieval, updates, validation failures, error handling, memory isolation, configuration loading, retention or deletion behaviour, and Oracle ADB integration boundaries using mocks or fakes where applicable.

Tests should avoid real OCI or Oracle ADB calls unless explicitly marked as integration tests.

## Dependency policy

Before adding a dependency, check whether the repository already has an equivalent library or helper. Prefer standard-library functionality when practical, add dependencies to the appropriate environment or requirements file, explain why they are needed, and update documentation if setup changes.

Do not introduce new frameworks unless the specification requires them.

## Changelog policy

Update `CHANGELOG.md` when a change is significant, including features, fixes, refactorings, specification updates, deployment changes, documentation updates, and test-strategy changes.

Keep changelog entries concise and understandable.

## Definition of done

A change is done only when:

* The relevant specification has been written or updated.
* The implementation conforms to the specification.
* The relevant formatting, linting, testing, and coverage checks have been considered.
* Unit tests have been written or updated when behaviour changes.
* Documentation has been updated when public behaviour, setup, or deployment changes.
* `CHANGELOG.md` has been updated when required.
* Any inability to run checks has been clearly documented.
