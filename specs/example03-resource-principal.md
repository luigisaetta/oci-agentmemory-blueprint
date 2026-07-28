# Example 03 Resource Principal authentication

## Scope

Add a self-contained Oracle Agent Memory example that uses OCI Resource
Principal authentication for the OCI Generative AI LLM and embedding calls. It
duplicates the small, readable startup and message-insertion flow of Example 01
while retaining the existing ADB connection-pool helper.

The Resource Principal replaces only the OCI Generative AI API-key identity.
The ADB connection remains a separate persistence boundary and continues to
use its configured database credentials and wallet.

## Behaviour

* Importing the example must not create an ADB pool, obtain a Resource
  Principal signer, invoke OCI, or create database objects.
* The example loads `GENAI_COMPARTMENT_ID` and `GENAI_REGION` from a process
  environment variable or the repository-root `.env` file. Neither value is a
  secret.
* The example obtains its signer with
  `oci.auth.signers.get_resource_principals_signer()` immediately before it
  configures the OCI embedder and LLM.
* The command loads the shared `MEMORY_STORE_ID` from the process environment
  or repository-root `.env` and passes it to Oracle Agent Memory.
* `Embedder` and `Llm` receive `oci_compartment_id`, `oci_region`, and
  `oci_signer`. They must not receive user API-key configuration values such as
  `oci_user`, `oci_fingerprint`, `oci_tenancy`, or `oci_key_file`.
* The command creates a thread, synchronously persists the two Example 01
  sample messages with a shared UTC insertion timestamp, and closes the ADB
  pool on success and failure.
* If Resource Principal credentials are unavailable, the command exits with a
  concise, non-sensitive error message and a local stack trace.

## Configuration and IAM boundary

The OCI runtime must support Resource Principals and expose its credentials to
the process. A dynamic group must include that runtime resource and an IAM
policy must grant it Generative AI inference access in the target compartment.
The minimal example policy is:

```text
Allow dynamic-group <dynamic-group-name> to use generative-ai-family in compartment <compartment-name>
```

The target compartment must match `GENAI_COMPARTMENT_ID`. Resource Principal
authentication can be tested from an OCI Data Science Notebook Session after
its dynamic group and policy are configured. The notebook still needs network
access and ADB connection configuration for the Agent Memory persistence layer.

## Acceptance criteria

* Unit tests verify the Resource Principal signer and only the required
  compartment, region, and signer values are passed to the OCI providers.
* Unit tests cover missing Resource Principal settings, unavailable signer,
  successful startup, timestamps, and ADB pool closure.
* Documentation explains the purpose, the new authentication code, required
  configuration, IAM policy, ADB boundary, and Data Science Notebook testing.
* No private key, API key, OCI profile, or Resource Principal token is logged
  or committed.
