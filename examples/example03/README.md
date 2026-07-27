# Example 03: Use Resource Principal with Oracle Agent Memory

## Purpose

Example 03 demonstrates Oracle Agent Memory backed by Oracle Autonomous
Database (ADB) when OCI Generative AI authentication uses an OCI Resource
Principal. This is suited to a workload running in a configured OCI-managed
environment, where the runtime identity replaces a long-lived user API key.

The example creates a memory store, creates a thread, and persists two sample
messages. The ADB thread is short-term conversation state. Background memory
extraction can create derived long-term memories after the raw messages are
persisted.

## What is new compared with Example 01

The important authentication change is in `create_memory_store`:

```python
oci_arguments = {
    "oci_compartment_id": resource_principal_settings["compartment_id"],
    "oci_region": resource_principal_settings["region"],
    "oci_signer": get_resource_principals_signer(),
}
```

The same arguments are passed to both `Embedder` and `Llm`. The signer supplies
the runtime identity for OCI Generative AI requests. Consequently, this example
does **not** load an OCI profile and does not pass `oci_user`,
`oci_fingerprint`, `oci_tenancy`, or `oci_key_file`.

Resource Principal authentication covers the OCI Generative AI boundary only.
The Python process still needs a valid ADB connection pool, including the
database credentials and wallet configuration described in the
[Quick Start](../../QUICKSTART.md).

## Required configuration

Set the normal ADB variables described in the Quick Start. Also set these
non-secret OCI Generative AI values, either as process environment variables or
in the repository-root `.env` file:

| Variable | Purpose | Safe example |
| --- | --- | --- |
| `GENAI_COMPARTMENT_ID` | Compartment authorising the selected OCI Generative AI models. | `ocid1.compartment.oc1..example` |
| `GENAI_REGION` | OCI region hosting the Generative AI inference endpoint. | `eu-frankfurt-1` |

Do not configure `~/.oci/config`, a private key, a fingerprint, or user OCIDs
for this example. OCI injects the Resource Principal credentials into supported
runtimes; the application obtains them with
`oci.auth.signers.get_resource_principals_signer()`.

## Required IAM configuration

Before running the example, create a dynamic group whose rule includes the OCI
resource executing the Python process. Grant that dynamic group access to the
same compartment configured by `GENAI_COMPARTMENT_ID`:

```text
Allow dynamic-group <dynamic-group-name> to use generative-ai-family in compartment <compartment-name>
```

Use a dynamic-group rule appropriate for the runtime type and scope it as
tightly as possible. The policy grants OCI Generative AI access; it does not
grant database access. Your network and database user must independently allow
the ADB connection.

Oracle documents Resource Principal signers for OCI SDK clients and the
Generative AI policy pattern above in its [Python SDK signing
guide](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/signing.html)
and [Generative AI IAM policy guidance](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/gen-ai-policies.html).

## Test in an OCI Data Science Notebook Session

Yes, an OCI Data Science Notebook Session is an appropriate place to test this
example. Oracle documents Resource Principal signer use from Notebook Sessions.
Create a dynamic group that includes the notebook session resource, apply the
Generative AI policy above, and run the notebook in a network location that can
reach the target ADB. You must still provide the ADB wallet and database
settings securely to the notebook environment.

For setup details, see Oracle's [Notebook Sessions
documentation](https://docs.oracle.com/en-us/iaas/Content/data-science/using/use-notebook-sessions.htm).

## Run the example

From the repository root in the configured OCI runtime:

```bash
conda activate oci-agentmemory-blueprint
python -m examples.example03.example03
```

The command logs the generated thread ID and persisted message IDs. It does not
log Resource Principal tokens, private keys, API keys, or database passwords.

## Behaviour and trade-offs

`thread.add_messages` synchronously persists the raw messages in ADB before the
connection pool closes. Automatic memory extraction is configured in background
mode, so extracted memories may become available later. A retrieval immediately
after insertion can therefore observe raw messages while missing newly derived
long-term memories.

For production, keep the workload alive long enough to monitor background work,
use least-privilege IAM and database privileges, and define retention and
deletion policies for thread content and derived memories.
