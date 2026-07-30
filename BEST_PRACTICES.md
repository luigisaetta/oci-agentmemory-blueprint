# Oracle Agent Memory Best Practices

This guide highlights two operational choices that should be made before
running an Oracle Agent Memory workload backed by Oracle Autonomous Database
(ADB).

## Choose `MEMORY_STORE_ID` deliberately

`MEMORY_STORE_ID` identifies the Oracle Agent Memory store. Agent Memory uses
this value as the prefix for the ADB-managed tables and indexes that persist
memory-related data. The value is therefore part of the persistence boundary,
not a cosmetic label.

Choose a stable, descriptive identifier for each intended store. In this
repository, `OAM` is the example identifier and stands for Oracle Agent
Memory.

When selecting a value, consider the following:

* Use a distinct value for stores that must remain separate, such as
  development, test, and production environments.
* Configure the same value consistently for all application instances that
  are meant to use the same memory store.
* Treat the value as operational configuration: document its owner and
  purpose, restrict changes through deployment configuration, and do not use
  customer data or secrets in it.
* Follow the validation rules implemented by this blueprint: start with a
  letter, use only letters, digits, and underscores, and keep the value to at
  most 16 characters.

Before any reset or maintenance operation, verify `MEMORY_STORE_ID` against
the target environment. Store-level maintenance affects all Agent
Memory-managed objects selected by that identifier.

## Use a suitably sized ADB connection pool

Oracle Agent Memory requires database connections. For a production agent
service that stays online for extended periods, create and reuse an ADB
connection pool instead of creating a new database connection for each agent
request.

Size the pool for the expected concurrency and the database capacity available
to the service. This blueprint exposes the relevant settings through the
following environment variables:

| Variable | Purpose |
| --- | --- |
| `DB_POOL_MIN` | Connections retained by the pool when demand is low. |
| `DB_POOL_MAX` | Upper limit on concurrent connections supplied by the pool. |
| `DB_POOL_INCREMENT` | Connections added when the pool grows to meet demand. |

Set `DB_POOL_MIN` high enough to avoid repeated connection creation during
normal traffic, and set `DB_POOL_MAX` to cover peak in-flight database work
without exceeding the capacity allocated to the application. Account for all
service replicas when calculating the total possible connections: the combined
maximum across replicas must remain appropriate for the ADB service and its
other workloads. Monitor pool wait time, connection use, request latency, and
database resource consumption after deployment, then adjust the limits from
observed load rather than relying only on initial estimates.

Do not share a pool across processes. Create one pool per long-running service
process, reuse it for that process's requests, and close it during an orderly
service shutdown.

For local setup and variable examples, see the [Quick Start](QUICKSTART.md).
