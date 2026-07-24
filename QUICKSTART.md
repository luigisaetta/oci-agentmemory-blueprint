# Quick Start

This guide covers the first prerequisite for the examples in this repository: configuring a local connection to Oracle Autonomous Database (ADB).

## Configure the local ADB connection

You need the following before continuing:

* An Oracle Autonomous Database instance that you can reach from your local network.
* A database user and its password. Use a dedicated application user rather than `ADMIN`.
* An ADB wallet downloaded from the OCI Console.
* The password used when downloading the wallet and an ADB service alias from its `tnsnames.ora` file.

### 1. Download and extract the wallet

From the OCI Console, download the client credentials wallet for the target Autonomous Database. Keep the downloaded ZIP file and its password private.

Extract the wallet into the repository-local `wallet_dir/` directory:

```bash
unzip /path/to/Wallet_<database-name>.zip -d wallet_dir
```

The `wallet_dir/` directory is ignored by Git. Do not move the wallet files into a tracked directory or commit them to the repository.

After extraction, the directory should contain the wallet files, including `tnsnames.ora`, `sqlnet.ora`, and the client credential files supplied by Oracle.

### 2. Create the local environment file

Create a local configuration file from the safe template:

```bash
cp .env.sample .env
```

`.env` is ignored by Git and must remain local to your machine.

### 3. Set the ADB connection variables

Set the following values in `.env`:

| Variable | Description | Safe example |
| --- | --- | --- |
| `DB_USER` | Dedicated Oracle database user for the application. | `agent_memory_app` |
| `DB_PWD` | Password for `DB_USER`. | Leave this secret out of documentation and source control. |
| `WALLET_DIR` | Path to the extracted ADB wallet directory. | `./wallet_dir` |
| `WALLET_PWD` | Password associated with the downloaded wallet. | Leave this secret out of documentation and source control. |
| `DB_DSN` | ADB service alias or connection string. Prefer an alias from `wallet_dir/tnsnames.ora`. | `mydatabase_high` |
| `DB_POOL_MIN` | Minimum number of connections kept in the ADB connection pool. | `1` |
| `DB_POOL_MAX` | Maximum number of connections allowed in the ADB connection pool. | `5` |
| `DB_POOL_INCREMENT` | Number of connections added when the pool needs to grow. | `1` |

For example, your local `.env` will use the variable names from the template with values specific to your database and environment:

```dotenv
DB_USER=<application-user>
DB_PWD=<application-password>
WALLET_DIR=./wallet_dir
WALLET_PWD=<wallet-password>
DB_DSN=<service-alias-from-tnsnames-ora>
DB_POOL_MIN=1
DB_POOL_MAX=5
DB_POOL_INCREMENT=1
```

Do not use the `ADMIN` account for the application connection. Create and grant a least-privilege database user appropriate to the schema and operations required by the example you are running.

> The wallet, `.env`, database password, and wallet password are sensitive. Do not commit them, include them in logs, or share them in issue reports.

Continue with the connection-verification example below once these settings are in place.

## Test the ADB connection

Activate the project Conda environment and run the first example from the repository root:

```bash
conda activate oci-agentmemory-blueprint
python examples/test_adb_connections/test_db_connection.py
```

The utility loads the repository-root `.env`, establishes a wallet-based connection with `oracledb`, and executes `SELECT 1 FROM dual`.

It prints only the non-sensitive `DB_USER`, `DB_DSN`, and `WALLET_DIR` values. It never prints `DB_PWD` or `WALLET_PWD`.

| Exit code | Meaning |
| --- | --- |
| `0` | The ADB connection and validation query succeeded. |
| `1` | The connection or validation query failed. Check credentials, wallet path, DSN, and network access. |
| `2` | Required variables are missing or blank in `.env`. |
