---
extension_name: Universal Controller to ServiceNow Table Synchronization
work_item_id: initial-1
ticket_id: ""
status: pending_review
approved_by: ""
approved_at: ""
---

# Universal Extension Requirements (Refined)

**Extension Name:** Universal Controller to ServiceNow Table Synchronization
**Created:** 2026-09-10
**Work Item:** initial-1
**Initial Requirements Assessment:** High Detail
**Target Platform:** Linux

---

# Table of Contents

1. [Overview](#overview)
2. [Actions](#actions)
   - [Action 1: Validate Configuration](#action-1-validate-configuration)
   - [Action 2: Preview](#action-2-preview)
   - [Action 3: Synchronize](#action-3-synchronize)
3. [Input Requirements](#input-requirements)
   - [Core Configuration Fields](#core-configuration-fields)
   - [Dynamic Choice Fields](#dynamic-choice-fields)
   - [Source Dataset Configuration](#source-dataset-configuration)
   - [Mapping Configuration](#mapping-configuration)
4. [Output Requirements](#output-requirements)
   - [On Success](#on-success)
   - [On Error](#on-error)
5. [Authentication Requirements](#authentication-requirements)
6. [Environment Variables](#environment-variables)
7. [Operational Behavior](#operational-behavior-section)
8. [Implementation Notes](#implementation-notes)
   - [Python Compatibility](#python-compatibility)
   - [Target Platform](#target-platform)
   - [Third-Party Services and Tools](#third-party-services-and-tools-section)
   - [Error Handling](#error-handling)
   - [Resource Cleanup](#resource-cleanup)
9. [References](#references)

---

# Overview

This Universal Extension reads Universal Controller (UAC) inventory data through REST APIs and synchronizes it to ServiceNow Decision Tables and existing customer/account tables. Users configure and execute the extension through native task form fields, discovering target tables dynamically from ServiceNow and source objects from UAC.

**Integration Purpose:**

Organizations managing critical infrastructure through Universal Controller need to synchronize operational data (agents, calendars, scripts, SAP jobs) into ServiceNow for cross-platform visibility, governance, and automation. This extension enables one-way, read-only data flows from UAC to ServiceNow without modifying Controller state. Users can target existing customer/account tables, Decision Tables for operational routing, or both simultaneously, applying configured field mappings with explicit account associations.

---

# Actions

The extension implements three task actions:

## Action 1: Validate Configuration

**Functional Requirements:**

1. Verify connectivity to UAC controller using configured URL and credentials
2. Verify connectivity to ServiceNow using configured URL and authentication method
3. Test read access to at least one object from the selected source dataset (fetch 1 agent, calendar, script, or job definition)
4. Verify ServiceNow target tables exist and are accessible
5. Validate all target field identifiers match existing columns in selected tables
6. Verify Decision Table structures (if Decision Table mode is selected)
7. Validate source-to-destination field mappings for type compatibility (e.g., numeric source to numeric destination)
8. Verify all configured Business Service IDs exist in UAC and have corresponding account mappings in ServiceNow
9. Test account resolution logic: attempt to locate test account(s) using configured external-key lookup
10. Perform zero writes; report unverified permissions without attempting PATCH or POST operations

**Behavior:** Validation completes synchronously and returns pass/fail status with detailed error messages for each failed check. Validation errors block progression to Preview/Synchronize without fixing configuration.

### Input Requirements

**Required Fields for Validation:**

- UAC URL (from configured credential)
- UAC authentication (from configured credential)
- ServiceNow URL (from configured credential)
- ServiceNow authentication method (from configured credential)
- Target Mode selection (Customer Tables, Decision Tables, or Both)
- Selected target table(s)
- Selected source dataset (Agents, Calendars, Scripts, SAP/ABAP Jobs)
- Business Service selection (if applicable)
- Field mappings configuration

**Optional Fields for Validation:**

- Custom CA bundle path (via REQUESTS_CA_BUNDLE environment variable)
- HTTP timeout override (via task field or UE_HTTP_TIMEOUT environment variable)

### Output Requirements

**On Success (Validation passes):**

Return code: `0`

Status description: `Configuration validated successfully. [X] UAC objects readable, [Y] ServiceNow tables accessible, [Z] mappings compatible.`

Extension output (JSON):
```json
{
  "status": "success",
  "action": "validate_configuration",
  "validation_checks": [
    {
      "check": "UAC connectivity",
      "result": "passed",
      "details": "Successfully authenticated and retrieved controller identity."
    },
    {
      "check": "ServiceNow connectivity",
      "result": "passed",
      "details": "Successfully authenticated and retrieved instance info."
    },
    {
      "check": "Source dataset access",
      "result": "passed",
      "details": "Retrieved 1 agent successfully from UAC."
    },
    {
      "check": "Target table schema",
      "result": "passed",
      "details": "All target fields found in customer_account table."
    },
    {
      "check": "Business Service mapping",
      "result": "passed",
      "details": "3 Business Services mapped to existing ServiceNow accounts."
    },
    {
      "check": "Field mapping compatibility",
      "result": "passed",
      "details": "All source/destination field types are compatible."
    }
  ],
  "timestamp": "2026-09-10T12:55:32Z"
}
```

**On Error (Validation fails):**

Return code: `20` (validation error)

Failure Scenarios:

1. **UAC Authentication Failure**
   - Scenario: Invalid URL, credentials, or UAC service unavailable
   - Root causes: Wrong credential, network failure, UAC down, wrong base URL
   - Return code: `20`
   - Status description: `Configuration validation failed: Cannot authenticate to UAC at [URL]. Check credentials and network connectivity.`
   - Extension output: Include actual HTTP error (e.g., 401, 403, 5xx) and sanitized error message

2. **ServiceNow Authentication Failure**
   - Scenario: Invalid URL, authentication method, or ServiceNow instance down
   - Root causes: Wrong credential, wrong auth method, network failure, ServiceNow down
   - Return code: `20`
   - Status description: `Configuration validation failed: Cannot authenticate to ServiceNow at [URL]. Check credentials and authentication method.`
   - Extension output: Include actual HTTP error and sanitized message

3. **Source Dataset Not Accessible**
   - Scenario: No read access to selected dataset, dataset does not exist in UAC, or filtered selection matches zero objects
   - Root causes: Permission denied, wrong dataset type, overly restrictive filter
   - Return code: `20`
   - Status description: `Configuration validation failed: Cannot read [dataset_type]. Verify permissions and filter settings.`
   - Extension output: List which datasets were tested and their results

4. **Target Table Does Not Exist**
   - Scenario: Selected customer table, decision table, or related record table not found in ServiceNow
   - Root causes: Wrong table name, table not installed, permission denied
   - Return code: `20`
   - Status description: `Configuration validation failed: Target table [table_name] not found in ServiceNow. Verify table selection.`
   - Extension output: Show attempted table lookups and results

5. **Target Field Missing or Inaccessible**
   - Scenario: One or more destination fields in mapping do not exist in target table, or field is read-only
   - Root causes: Wrong field name, field not installed, field permission denied
   - Return code: `20`
   - Status description: `Configuration validation failed: Field [field_name] not found in table [table_name].`
   - Extension output: List each mapped field and validation result

6. **Field Type Incompatibility**
   - Scenario: Source field type cannot be converted to destination field type (e.g., non-numeric to numeric without conversion rule)
   - Root causes: No conversion rule in mapping, incompatible types
   - Return code: `20`
   - Status description: `Configuration validation failed: Field mapping [source] -> [destination] is type-incompatible. Define a conversion rule.`
   - Extension output: Show source type, destination type, and suggested resolution

7. **Business Service Not Found or Not Mapped**
   - Scenario: Selected Business Service does not exist in UAC, or Business Service has no configured account mapping
   - Root causes: Wrong Business Service ID, Business Service deleted, mapping configuration incomplete
   - Return code: `20`
   - Status description: `Configuration validation failed: Business Service [id] not found in UAC or not mapped to an account.`
   - Extension output: List available Business Services and their mapping status

8. **Account Resolution Fails**
   - Scenario: External-key lookup does not resolve to any account, resolves to multiple accounts, or account sys_id does not exist
   - Root causes: Wrong external key, no matching records, duplicate accounts, account deleted
   - Return code: `20`
   - Status description: `Configuration validation failed: Cannot uniquely resolve account using external key [key]=[value].`
   - Extension output: Show number of matches (0, 1, or multiple) and suggest correction

9. **Decision Table Structure Invalid**
   - Scenario: Selected Decision Table sys_id does not exist, or table schema does not support configured condition/result fields
   - Root causes: Wrong Decision Table ID, table deleted, field sys_ids stale
   - Return code: `20`
   - Status description: `Configuration validation failed: Decision Table [sys_id] not found or schema mismatch on field [field_sys_id].`
   - Extension output: Show Decision Table lookup results and field validation

---

## Action 2: Preview

**Functional Requirements:**

1. Collect current source data from UAC using configured filters and scope
2. Collect current target data from ServiceNow (selected tables and Decision Tables)
3. Apply source-to-destination field mappings without persisting changes
4. Generate a complete plan of all proposed changes: new records, updates, decision row changes
5. Report proposed change counts: planned creates, planned updates, planned decision changes
6. Report per-record mapping errors and validation failures without writing
7. Share identical collection/normalization/planning logic with Synchronize action
8. Return zero ServiceNow writes (read-only operation)
9. Report success or failure with full diagnostic detail

**Behavior:** Preview fetches all required data, validates completeness, applies mappings, and returns what *would* be written. The report includes record-level details (which records would change, which fields) and aggregate counts. Preview failures do not prevent later Synchronize attempts; users can fix configuration and retry.

### Input Requirements

Same as Validate Configuration, plus:

- Configuration must have passed Validate Configuration check (recommended, not enforced)
- Service-specific configuration: mappings, account associations, source filters

### Output Requirements

**On Success (Preview completes):**

Return code: `0`

Status description: `Preview completed. Proposed changes: [C] creates, [U] updates, [D] decision rows. No writes performed.`

Extension output (JSON):
```json
{
  "status": "success",
  "action": "preview",
  "run_id": "run_20260910_125532_abc123",
  "source_dataset": "agents",
  "target_mode": "both",
  "timestamp_start": "2026-09-10T12:55:32Z",
  "timestamp_end": "2026-09-10T12:55:45Z",
  "read_counts": {
    "agents_retrieved": 42,
    "agents_in_selected_business_services": 38,
    "agents_with_account_match": 36,
    "agents_with_mapping_error": 2
  },
  "proposed_changes": {
    "customer_table_creates": 0,
    "customer_table_updates": 36,
    "customer_table_unchanged": 0,
    "decision_table_row_creates": 0,
    "decision_table_row_updates": 12,
    "decision_table_row_unchanged": 24
  },
  "errors": [
    {
      "source_id": "agent_789",
      "source_name": "backup-server",
      "error_category": "account_resolution",
      "error_message": "Agent in Business Service 'Staging' has no mapped account.",
      "source_object": {
        "agent_id": "789",
        "agent_name": "backup-server",
        "business_service_id": "bs_staging"
      }
    },
    {
      "source_id": "job_456",
      "source_name": "Z_PROD_JOB",
      "error_category": "mapping_error",
      "error_message": "SAP program name 'Z_UNKNOWN' does not match any decision table input condition.",
      "source_object": {
        "task_id": "456",
        "task_name": "Z_PROD_JOB",
        "abap_program": "Z_UNKNOWN"
      }
    }
  ],
  "sample_proposed_record": {
    "table": "customer_account",
    "operation": "update",
    "target_sys_id": "12345",
    "proposed_fields": {
      "managed_agents_count": 36,
      "primary_calendar": "PROD_CALENDAR",
      "last_sync_timestamp": "2026-09-10T12:55:32Z"
    }
  }
}
```

**On Error (Preview fails):**

Return code: `20` (validation error) or `1` (runtime error depending on failure type)

Failure Scenarios:

1. **Incomplete Source Data Retrieval**
   - Scenario: Cannot fetch all pages of source data due to permission error, network failure, or page limit exceeded without continuation token
   - Root causes: Lost connection mid-fetch, ACL filtering causes incomplete pages, limit reached
   - Return code: `1`
   - Status description: `Preview failed: Incomplete source data retrieval. Retrieved [X] of estimated [Y] objects. Aborting to prevent data loss.`
   - Extension output: Show which pages succeeded/failed, total retrieved, and error details

2. **Incomplete Target Data Retrieval**
   - Scenario: Cannot fetch all target records from ServiceNow for account lookups or conflict detection
   - Root causes: Network failure, permission denied, ServiceNow down
   - Return code: `1`
   - Status description: `Preview failed: Cannot retrieve target records from ServiceNow. Aborting.`
   - Extension output: Show which tables/queries failed

3. **Mapping Validation Failure**
   - Scenario: Mapping configuration is invalid (malformed JSON, missing required fields, unknown field names in destination)
   - Root causes: Configuration error, stale field references
   - Return code: `20`
   - Status description: `Preview failed: Mapping configuration is invalid. [Detail]`
   - Extension output: Show specific mapping validation errors

4. **Authentication/Permission Errors During Preview**
   - Scenario: Credentials became invalid, permissions changed, or rate limits reached (429)
   - Root causes: Credential expired, permission revoked, too many requests
   - Return code: `1`
   - Status description: `Preview failed: Authentication or rate limit error. Retry after [delay].`
   - Extension output: Include actual HTTP status and Retry-After header if available

---

## Action 3: Synchronize

**Functional Requirements:**

1. Revalidate configuration before writing (do not blindly apply old Preview plan)
2. Collect current source data from UAC
3. Collect current target data from ServiceNow (read source of truth for conflict detection)
4. Apply field mappings and account associations
5. Issue PATCH requests to ServiceNow for record updates (only changed mapped fields)
6. Issue POST requests for new records only if explicitly enabled in configuration (disabled by default)
7. For Decision Tables: issue REST adapter or native API calls to update decision rows
8. Detect concurrent edits using ServiceNow's `sys_updated_on` timestamp; abort affected record on conflict
9. Handle transient errors (429, 5xx) with bounded exponential backoff, up to 3 retries
10. Report operation results accurately: succeeded, skipped, failed per record
11. Stop dependent work on critical failures; partial writes must be reported clearly
12. Return accurate counts of created, updated, unchanged, and failed records

**Behavior:** Synchronize performs actual writes to ServiceNow. It revalidates current target state before writing to avoid stale data issues. All writes are conservative: existing records are updated only on mapped fields, creation is opt-in, and deletion is never attempted. Transient errors trigger retry; permanent errors abort the operation.

### Input Requirements

Same as Preview action.

Additionally, users may configure per-task HTTP timeout override and other operational settings.

### Output Requirements

**On Success (All writes completed, no errors):**

Return code: `0`

Status description: `Synchronization complete. [C] created, [U] updated, [U] unchanged. [D] decision rows updated.`

Extension output (JSON):
```json
{
  "status": "success",
  "action": "synchronize",
  "run_id": "run_20260910_130015_xyz789",
  "source_dataset": "agents",
  "target_mode": "both",
  "timestamp_start": "2026-09-10T13:00:15Z",
  "timestamp_end": "2026-09-10T13:01:32Z",
  "read_counts": {
    "source_objects_retrieved": 42,
    "source_objects_processed": 38,
    "source_objects_skipped": 4
  },
  "write_results": {
    "customer_table_created": 0,
    "customer_table_updated": 36,
    "customer_table_unchanged": 0,
    "customer_table_failed": 2,
    "decision_table_rows_updated": 12,
    "decision_table_rows_created": 0,
    "decision_table_rows_failed": 0
  },
  "error_summary": {
    "total_errors": 2,
    "categories": {
      "account_resolution": 1,
      "servicenow_permission": 1
    }
  },
  "errors": [
    {
      "source_id": "agent_789",
      "source_name": "backup-server",
      "error_category": "account_resolution",
      "error_message": "Agent in Business Service 'Staging' has no mapped account.",
      "recovery_action": "Fix Business Service mapping and retry synchronization."
    },
    {
      "source_id": "agent_101",
      "source_name": "prod-app",
      "error_category": "servicenow_permission",
      "error_message": "Permission denied updating field 'managed_agents_count' on account 'ACME Corp'. Verify field ACLs.",
      "recovery_action": "Grant write permission to integration user and retry."
    }
  ]
}
```

Success Criteria:

1. All source objects with valid account mappings are written to ServiceNow
2. No duplicate records are created on retry (idempotent by stable key)
3. Only mapped fields are modified; unrelated fields remain unchanged
4. Decision Table rows are updated as configured
5. Run ID and timestamp are recorded for audit trail
6. All write operations use HTTP PATCH for updates and POST for creates (where enabled)

**On Partial Error (Some writes succeeded, some failed):**

Return code: `1`

Status description: `Synchronization completed with errors. [S] succeeded, [F] failed. Details in output.`

Extension output structure is same as Success, but status is `"partial"` and error_summary reflects failures.

Behavior on Partial Error:

- Stop processing remaining objects (Fail Fast, not Continue on Error)
- Report all completed writes
- Report all attempted but failed writes with root cause
- Recommend corrective action for each error category
- Users can fix configuration and retry; rerun will reconcile by stable key and not duplicate

**On Complete Failure (No writes completed):**

Return code: `1`

Status description: `Synchronization failed before writing. [Reason].`

Extension output (JSON):
```json
{
  "status": "failed",
  "action": "synchronize",
  "run_id": "run_20260910_130500_fail001",
  "error_category": "configuration_error|authentication_error|data_validation_error|network_error",
  "error_message": "[Detailed error message]",
  "recovery_action": "[Specific recommendation]"
}
```

Failure Scenarios:

1. **Configuration Invalid at Runtime**
   - Scenario: Configuration changed, stale field references, or account mappings deleted
   - Return code: `1`
   - Status description: `Synchronization failed: Configuration is invalid. [Detail]. No writes performed.`

2. **Authentication/Connection Lost**
   - Scenario: UAC or ServiceNow credentials became invalid, network unreachable
   - Return code: `1`
   - Status description: `Synchronization failed: Cannot connect to [service]. Verify credentials and network.`

3. **Concurrent Edit Conflict on Target**
   - Scenario: ServiceNow record was modified by another process after being read but before PATCH
   - Return code: `1` (if conflict on critical record) or partial write with per-record error
   - Status description: `Update skipped for [record]: concurrent modification detected.`
   - Strategy: Read current state, detect conflict via sys_updated_on, skip that record, continue with others

4. **Decision Table API Error**
   - Scenario: Decision Table adapter unavailable, Decision Table deleted, or row update not supported
   - Return code: `1`
   - Status description: `Synchronization failed: Decision Table update failed. [Detail].`
   - Extension output: Show which Decision Table(s) failed and reason

5. **Transient Error with Retries Exhausted**
   - Scenario: Network timeouts or ServiceNow rate limits (429) after 3 retries
   - Return code: `1`
   - Status description: `Synchronization failed: Maximum retries exceeded for ServiceNow requests.`
   - Extension output: Show which requests failed, retry counts, and Retry-After headers if available

---

# Input Requirements

## Core Configuration Fields

All core fields must be present on the task form. Visibility and conditionality are controlled by configured choices.

### Action Selection

**Field Name** (choice): `action`

- Description: Task operation to perform
- Data type: Choice / Enum
- Conditionality: Required for all task executions
- Example: "Preview"
- Default Value: "Preview"
- Available options:
  - "Validate Configuration"
  - "Preview"
  - "Synchronize"

### Universal Agent Selection

**Field Name** (text): `universal_agent`

- Description: Name or ID of the Universal Agent on which this extension will execute and perform API calls
- Data type: Text
- Conditionality: Required
- Example: "uac-agent-prod-01"
- Applicability: All actions
- Default Value: None (user must select)

### UAC Connection

**Field Name** (credential): `uac_credential`

- Description: Credential object containing UAC controller URL and authentication (Basic auth or token-based)
- Data type: Credential (from UAC credential store)
- Conditionality: Required
- Example: Credential named "uac-production" with URL "https://uac.example.com" and Basic auth
- Applicability: All actions
- Default Value: None (user must select)

### ServiceNow Connection

**Field Name** (credential): `servicenow_credential`

- Description: Credential object containing ServiceNow instance URL and authentication method (Basic auth or OAuth 2.0)
- Data type: Credential (from UAC credential store)
- Conditionality: Required
- Example: Credential named "servicenow-prod" with URL "https://acme.service-now.com" and Basic auth
- Applicability: All actions
- Default Value: None (user must select)

### Target Mode Selection

**Field Name** (choice): `target_mode`

- Description: Which target type(s) to synchronize to
- Data type: Choice / Enum
- Conditionality: Required
- Example: "Both Customer Tables and Decision Tables"
- Applicability: All actions
- Default Value: "Customer Tables"
- Available options:
  - "Customer Tables" (synchronize to existing customer/account and related inventory tables)
  - "Decision Tables" (synchronize to ServiceNow Decision Table row definitions)
  - "Both Customer Tables and Decision Tables" (synchronize to both target types in one run)
- Shows/Hides:
  - If "Customer Tables" or "Both": show `customer_table`, `target_fields`, `field_mappings_customer`, `account_association_config`
  - If "Decision Tables" or "Both": show `decision_table`, `decision_mapping_config`

### Source Dataset Selection

**Field Name** (choice): `source_dataset`

- Description: Which UAC inventory type to collect and synchronize
- Data type: Choice / Enum
- Conditionality: Required
- Example: "Agents"
- Applicability: All actions
- Default Value: "Agents"
- Available options:
  - "Agents" (UAC Agent definitions)
  - "Calendars" (UAC Calendar definitions with optional custom days)
  - "Scripts" (UAC Script definitions)
  - "SAP/ABAP Jobs" (UAC SAP task definitions with ABAP steps)
- Shows/Hides:
  - Each dataset shows different discovery/filter options based on dataset type
  - All show `source_scope` choice for filtering

### Source Scope Selection

**Field Name** (choice): `source_scope`

- Description: Filtering strategy for source objects within the selected dataset
- Data type: Choice / Enum
- Conditionality: Required
- Example: "By Business Service"
- Applicability: All actions
- Default Value: "All Objects"
- Available options:
  - "All Objects" (fetch all objects of the selected dataset type, no filtering)
  - "By Business Service" (fetch objects associated with a specific Business Service; shows `business_service` choice field)
  - "Selected Object" (fetch a single specific object; shows `source_object` dynamic choice field)
- Shows/Hides:
  - If "By Business Service": show `business_service` dynamic choice field
  - If "Selected Object": show `source_object` dynamic choice field
  - If "All Objects": show neither

---

## Dynamic Choice Fields

All dynamic choice fields execute on the selected Universal Agent using configured credentials. Dependencies are declared so the SDK provides necessary input fields to the handler at both configuration and execution time.

### Business Service Selection

**Field Name** (choice): `business_service`

- Description: Restrict source objects to those associated with a specific Business Service
- Data type: Choice with @dynamic_choice_command
- Conditionality: Required if `source_scope` = "By Business Service"
- Handler name: `business_service`
- Handler dependencies:
  - `uac_credential` (to authenticate REST calls to UAC)
  - `universal_agent` (to resolve deployment context)
- Example: "Production | bs_prod_001"
- Applicability: All actions when filtering by Business Service
- Display format: "[Label] | [Business Service ID]" (label for human readability; ID for automation)
- Discovery behavior:
  - Fetch all Business Services from UAC: GET /resources/businessservice/list
  - Display results as label + stable ID
  - Support pagination (100 items max); indicate truncation
  - Support search/filter to narrow results
  - Distinguish no matches from authentication/network errors

### Source Object Selection

**Field Name** (choice): `source_object`

- Description: Select a single specific source object to synchronize (when scope is "Selected Object")
- Data type: Choice with @dynamic_choice_command
- Conditionality: Required if `source_scope` = "Selected Object"
- Handler name: `source_object`
- Handler dependencies:
  - `uac_credential`
  - `universal_agent`
  - `source_dataset` (Agent, Calendar, Script, or SAP Job)
  - `business_service` (optional; if present, filter to objects in this Business Service)
- Example: "prod-app-01 | agent_prod_app_01" or "Z_SYNC_PROD | task_prod_abap_123"
- Applicability: All actions when scope is "Selected Object"
- Display format: "[Label (type)] | [Stable ID]"
- Discovery behavior:
  - Fetch objects of the selected dataset type using configured scope and filters
  - For selected dataset type, use appropriate UAC endpoint:
    - Agents: GET /resources/agent/list or GET /resources/agent/listadv
    - Calendars: GET /resources/calendar/list
    - Scripts: GET /resources/script/list
    - SAP Jobs: POST /resources/task/list (filtered by type=taskSap)
  - Display with meaningful labels (Agent hostname, Calendar name, Script name, Task name)
  - Support pagination and search
  - Return stable ID for configuration persistence

### Customer Table Selection

**Field Name** (choice): `customer_table`

- Description: Select the target customer/account table in ServiceNow
- Data type: Choice with @dynamic_choice_command
- Conditionality: Required if `target_mode` includes "Customer Tables"
- Handler name: `customer_table`
- Handler dependencies:
  - `servicenow_credential` (to fetch ServiceNow table metadata)
  - `universal_agent`
- Example: "customer_account" or "account"
- Applicability: All actions when target mode is Customer Tables or Both
- Display format: "[Table Label (technical name)]"
- Discovery behavior:
  - Query sys_db_object table in ServiceNow to find tables holding customer/account data
  - Filter for tables accessible to the integration credential (have read/write access)
  - Return technical table name as identifier, human-readable table label for display
  - Support pagination (100 items max) and search/filter by name
  - Distinguish no matches from permission/authentication errors

### Target Fields

**Field Name** (choice, multi-select): `target_fields`

- Description: Select which columns in the target customer table to include in mappings
- Data type: Choice / Multi-select with @dynamic_choice_command
- Conditionality: Required if `target_mode` includes "Customer Tables"
- Handler name: `target_field`
- Handler dependencies:
  - `servicenow_credential`
  - `universal_agent`
  - `customer_table` (fetch fields from this specific table)
- Example: ["managed_agents_count", "primary_calendar", "last_sync_timestamp"]
- Applicability: All actions when target mode includes Customer Tables
- Display format: "[Field Label (type)] | [field_name]"
- Discovery behavior:
  - Fetch column metadata from sys_dictionary for the selected customer_table
  - Return field name as identifier, field label + type for display
  - Include inherited fields from parent tables (if customer_table has parents)
  - Filter out read-only/system fields (sys_*, internal fields)
  - Support pagination and search by field name/label
  - Indicate field type (String, Integer, DateTime, Reference, etc.) to aid mapping

### Decision Table Selection

**Field Name** (choice): `decision_table`

- Description: Select the target Decision Table in ServiceNow
- Data type: Choice with @dynamic_choice_command
- Conditionality: Required if `target_mode` includes "Decision Tables"
- Handler name: `decision_table`
- Handler dependencies:
  - `servicenow_credential`
  - `universal_agent`
- Example: "agent_assignment | dt_sys_id_12345"
- Applicability: All actions when target mode includes Decision Tables or Both
- Display format: "[Table Name] | [sys_id]"
- Discovery behavior:
  - Query sn_decision_table table to find all Decision Table definitions
  - Return sys_id as canonical identifier (stable, never changes if renamed)
  - Display table name + description for human readability
  - Support pagination (100 items max) and search by name
  - Distinguish no results from permission/authentication errors

### Decision Input and Result Fields

**Field Name** (choice, multi-select): `decision_inputs`, `decision_results`

- Description: Input condition fields and result/answer fields within the selected Decision Table
- Data type: Choice / Multi-select with @dynamic_choice_command
- Conditionality: Required if `target_mode` includes "Decision Tables"
- Handler names: `decision_input`, `decision_result`
- Handler dependencies:
  - `servicenow_credential`
  - `universal_agent`
  - `decision_table` (fetch inputs/results from this table)
- Example: ["environment | sys_id_input_001", "assignment_queue | sys_id_result_002"]
- Applicability: All actions when target mode includes Decision Tables
- Display format: "[Field Label] | [Field sys_id]"
- Discovery behavior:
  - Fetch Decision Table structure from ServiceNow (query sn_decision_table_input, sn_decision_table_result tables)
  - Return field sys_id as canonical identifier (stable)
  - Display field name and data type for clarity
  - Support pagination and search
  - Maintain separate lists for inputs and results

### Customer Record Selection

**Field Name** (choice): `customer_record`

- Description: Explicitly select a single customer/account record for single-account synchronization (optional)
- Data type: Choice with @dynamic_choice_command
- Conditionality: Optional; if omitted, use configured account association logic (Business Service mapping)
- Handler name: `customer_record`
- Handler dependencies:
  - `servicenow_credential`
  - `universal_agent`
  - `customer_table` (fetch records from this table)
- Example: "ACME Corp | 12345abcd"
- Applicability: All actions when target mode includes Customer Tables
- Display format: "[Account Name] | [sys_id]"
- Discovery behavior:
  - Fetch existing account records from the selected customer_table
  - Return sys_id as identifier, account name for display
  - Support pagination (100 items max) and search by account name
  - This field is for explicit single-account override; use account_association_config for multi-account mappings

---

## Source Dataset Configuration

### Agents Dataset (when source_dataset = "Agents")

**Fields to collect from UAC /resources/agent/list:**
- Agent ID (stable source identifier)
- Agent name (display name, may change)
- Host name
- OS type / Agent type
- Current status (active, inactive, suspended, decommissioned)
- Version
- Business Service associations
- Last update timestamp

**No additional dataset-specific configuration required;** filtering by Business Service or Single Object applies.

### Calendars Dataset (when source_dataset = "Calendars")

**Fields to collect from UAC:**
- Calendar ID (stable source identifier)
- Calendar name
- Business Service associations
- Business days configuration
- Custom days (via GET /resources/calendar/customdays?calendarid=<id>)
- Last update timestamp

**Additional configuration field:**

**Field Name** (checkbox): `include_calendar_custom_days`

- Description: Include custom business days and holiday definitions in synchronization
- Data type: Checkbox / Boolean
- Conditionality: Optional
- Default Value: Checked (true)
- When enabled, fetch and include custom day details in the mapping output

### Scripts Dataset (when source_dataset = "Scripts")

**Fields to collect from UAC /resources/script/list:**
- Script ID (stable source identifier)
- Script name
- Script type (description of script category/purpose)
- Description
- Business Service associations
- Update metadata (timestamp)
- **Exclude:** Script body/content (never retrieve or output full script code)

**No additional dataset-specific configuration required.**

### SAP/ABAP Jobs Dataset (when source_dataset = "SAP/ABAP Jobs")

**Fields to collect from UAC /resources/task/list (filtered by type=taskSap):**
- Task ID (stable source identifier)
- Task name
- Business Service associations
- ABAP steps (may require POST /resources/task/list with TaskQueryFilterWsData JSON or GET /resources/task/listadv)
  - ABAP Step ID / order
  - Program name
  - Variant name
  - Agent / connection reference

**Additional SAP filtering field:**

**Field Name** (choice): `sap_filter_strategy`

- Description: Filtering strategy for SAP task discovery
- Data type: Choice / Enum
- Conditionality: Optional; affects how SAP tasks are discovered
- Default Value: "By Business Service and Type"
- Available options:
  - "By Business Service and Type" (fetch SAP tasks in the selected Business Service, filtered by task type)
  - "By Job Name Partial Match" (fetch SAP tasks matching a partial name pattern; requires `sap_job_name_filter` text field)
  - "All SAP Tasks" (fetch all SAP tasks without filtering)
- Shows/Hides:
  - If "By Job Name Partial Match": show `sap_job_name_filter` text field

**Field Name** (text): `sap_job_name_filter`

- Description: Partial name pattern to match SAP task names (e.g., "Z_PROD_" to match Z_PROD_01, Z_PROD_02, etc.)
- Data type: Text
- Conditionality: Required only if `sap_filter_strategy` = "By Job Name Partial Match"
- Example: "Z_PROD_"
- Applicability: SAP/ABAP Jobs dataset with name-based filtering

---

## Mapping Configuration

### Field Mappings for Customer Tables

**Field Name** (large text): `field_mappings_customer`

- Description: JSON configuration defining source-to-destination field mappings for customer/account table synchronization
- Data type: Large Text Area (or hybrid with UAC Data Script option per Question 5.C)
- Conditionality: Required if `target_mode` includes "Customer Tables"
- Validation: Must be valid JSON; at runtime, validate all referenced fields exist
- Example mapping structure:
```json
{
  "mappings": [
    {
      "source_field": "agent_count",
      "destination_field": "managed_agents_count",
      "transformation": "count",
      "notes": "Aggregate: number of agents per account"
    },
    {
      "source_field": "primary_calendar_name",
      "destination_field": "calendar_reference",
      "transformation": "field_copy",
      "aggregation_strategy": "first_match",
      "notes": "Use first calendar per account"
    },
    {
      "source_field": "last_update",
      "destination_field": "last_sync_timestamp",
      "transformation": "timestamp",
      "notes": "When synchronization last ran"
    }
  ],
  "account_association": {
    "strategy": "external_key",
    "external_key_field": "external_id",
    "business_service_to_account_mapping": {
      "bs_prod_001": "12345abcd",
      "bs_staging_001": "67890efgh"
    },
    "notes": "Each Business Service maps to exactly one ServiceNow account sys_id"
  },
  "related_records": {
    "strategy": "mixed",
    "related_record_mappings": [
      {
        "source_collection": "agents",
        "related_table": "customer_agents",
        "related_key_field": "customer_account",
        "source_key_field": "agent_id",
        "notes": "One related record per agent per account"
      }
    ],
    "notes": "Some data maps to related tables (1:N relationships); some to account fields (N:1 aggregation)"
  }
}
```

### Account Association Configuration

**Field Name** (large text): `account_association_config`

- Description: JSON configuration for how source objects are associated with ServiceNow customer accounts
- Data type: Large Text Area
- Conditionality: Required if `target_mode` includes "Customer Tables" and not using explicit `customer_record` selection
- Validation: Must be valid JSON; Business Service IDs must exist in UAC
- Example:
```json
{
  "association_strategy": "business_service_mapping",
  "business_service_to_account": {
    "bs_prod_001": {
      "account_sys_id": "12345abcd",
      "account_name": "ACME Production",
      "external_key_lookup": {
        "field": "external_id",
        "value": "ACME_PROD"
      }
    },
    "bs_staging_001": {
      "account_sys_id": "67890efgh",
      "account_name": "ACME Staging",
      "external_key_lookup": {
        "field": "external_id",
        "value": "ACME_STAGING"
      }
    }
  },
  "behavior_on_missing_account": "error_and_skip",
  "behavior_on_multiple_matches": "error_and_skip",
  "notes": "Each Business Service must have exactly one account mapping. Objects with missing or ambiguous mappings are reported and skipped."
}
```

### Decision Table Mapping Configuration

**Field Name** (large text): `decision_mapping_config`

- Description: JSON configuration for synchronizing to Decision Table rows and updating condition/result values
- Data type: Large Text Area
- Conditionality: Required if `target_mode` includes "Decision Tables"
- Validation: Must be valid JSON; Decision Table sys_id must exist in ServiceNow
- Example:
```json
{
  "decision_table_sys_id": "dt_sys_id_12345",
  "managed_row_strategy": "by_composite_key",
  "managed_row_key": "{{business_service_id}}_{{source_type}}_{{source_id}}",
  "managed_row_key_storage": "decision_row_name_field",
  "notes": "Composite key ensures idempotent updates; stored in a name or label field for reference",
  "condition_mappings": [
    {
      "condition_field_sys_id": "sys_id_input_001",
      "condition_field_name": "environment",
      "source_field": "agent_os",
      "source_values": ["Linux"],
      "operator": "IN",
      "notes": "Map agent OS type to decision condition"
    },
    {
      "condition_field_sys_id": "sys_id_input_002",
      "condition_field_name": "business_service",
      "source_field": "business_service_id",
      "operator": "equals",
      "notes": "Exact match on Business Service ID"
    }
  ],
  "answer_mappings": [
    {
      "result_field_sys_id": "sys_id_result_001",
      "result_field_name": "assigned_agent",
      "source_field": "agent_name",
      "transformation": "field_copy",
      "notes": "Copy agent name to decision result"
    },
    {
      "result_field_sys_id": "sys_id_result_002",
      "result_field_name": "run_calendar",
      "source_field": "calendar_name",
      "transformation": "field_copy",
      "notes": "Map calendar to decision answer"
    }
  ],
  "row_priority_order": 10,
  "notes": "Decision rows are evaluated in priority order; higher priority rows match first. Preserve unrelated/manual rows."
}
```

---

## Optional Configuration Fields

### HTTP Request Timeout (per-task override)

**Field Name** (integer): `http_timeout_seconds`

- Description: Per-task override for HTTP request timeout (in seconds)
- Data type: Integer
- Conditionality: Optional
- Example: 45
- Default Value: Uses environment variable `UE_HTTP_TIMEOUT` (default 30 seconds)
- Applicability: All actions
- Validation: Must be positive integer between 5 and 300

### Result Verbosity

**Field Name** (choice): `output_verbosity`

- Description: Control level of detail in output results
- Data type: Choice / Enum
- Conditionality: Optional
- Default Value: "Summary and Errors"
- Available options:
  - "Summary Only" (report aggregate counts and high-level status)
  - "Summary and Errors" (include per-record error details)
  - "Full Details" (include per-record changes, proposed values, mapping details)
- Applicability: All actions

---

# Output Requirements

## On Success

### Validate Configuration Action

**Return code:** `0`

**Status description format:**
```
Configuration validated successfully. [X] UAC sources readable, [Y] ServiceNow tables accessible, [Z] mappings validated.
```

**Extension output (JSON):**
See Action 1 section above.

**STDOUT output:**
Human-readable formatted summary:
```
VALIDATION REPORT
═════════════════════════════════════════
Start:     2026-09-10T12:55:32Z
End:       2026-09-10T12:55:45Z
Status:    SUCCESS

Checks Performed
─────────────────────────────────────────
✓ UAC connectivity
✓ ServiceNow connectivity
✓ Source dataset access (42 agents readable)
✓ Target table schema (all fields found)
✓ Business Service mappings (3 valid)
✓ Field type compatibility
✓ Account resolution

Result: Ready to proceed with Preview or Synchronize.
```

### Preview Action

**Return code:** `0`

**Status description format:**
```
Preview completed. Proposed: [C] creates, [U] updates, [D] decision rows. No writes performed.
```

**Extension output (JSON):**
See Action 2 section above.

**STDOUT output:**
```
PREVIEW REPORT
═════════════════════════════════════════
Run ID:    run_20260910_125532_abc123
Action:    Preview
Dataset:   agents
Mode:      both
Start:     2026-09-10T12:55:32Z
End:       2026-09-10T12:55:45Z

Source Statistics
─────────────────────────────────────────
Retrieved:        42 agents
In scope:         38 agents (filtered by Business Service)
With mapping:     36 agents (valid account association)
Mapping errors:   2 agents (skipped)

Proposed Changes
─────────────────────────────────────────
Customer Table Updates:    36
Decision Table Updates:    12
No writes performed (Preview mode).

Errors (2)
─────────────────────────────────────────
1. Agent 'backup-server' (id: 789)
   Error: No mapped account for Business Service 'Staging'
   Fix: Add Business Service mapping in configuration

2. Job 'Z_PROD_JOB' (id: 456)
   Error: SAP program 'Z_UNKNOWN' not found in Decision Table conditions
   Fix: Verify mapping conditions match actual ABAP programs
```

### Synchronize Action

**Return code:** `0` (if all writes succeed)

**Status description format:**
```
Synchronization complete. [C] created, [U] updated, [S] skipped. [D] decision rows updated.
```

**Extension output (JSON):**
See Action 3 section above.

**STDOUT output:**
```
SYNCHRONIZATION REPORT
═════════════════════════════════════════
Run ID:    run_20260910_130015_xyz789
Action:    Synchronize
Dataset:   agents
Mode:      both
Start:     2026-09-10T13:00:15Z
End:       2026-09-10T13:01:32Z

Source Statistics
─────────────────────────────────────────
Retrieved:        42 agents
Processed:        38 agents
Skipped:          4 agents

Write Results
─────────────────────────────────────────
Customer Table:
  Created:        0 (creation disabled in config)
  Updated:        36 ✓
  Unchanged:      0
  Failed:         0

Decision Table Rows:
  Created:        0 (creation disabled in config)
  Updated:        12 ✓
  Unchanged:      0
  Failed:         0

Overall Status: SUCCESS (all writes completed)
```

---

## On Error

### Validation Errors (return code 20)

**Status description format:**
```
Configuration validation failed: [Specific reason]. Correct configuration and retry.
```

**Extension output (JSON):**
Include validation_checks array with failed checks detailed.

**STDERR output (if applicable):**
Do not output credentials, full payloads, or sensitive data. Output only:
```
[VALIDATION ERROR] Check: [name]
Reason: [Sanitized error message]
Detail: [Generic recovery instruction]
```

### Runtime Errors (return code 1)

**Status description format:**
```
[Action name] failed: [Reason]. See output for details.
```

**Extension output (JSON):**
Include error_category, error_message, and recovery_action.

**Error Categories:**

1. **authentication_error**: Invalid credentials, permission denied, or service unavailable
   - Return code: `1`
   - Example error message: "Cannot authenticate to ServiceNow. Verify credentials and network connectivity."
   - Recovery: Validate credentials, check network, retry

2. **configuration_error**: Mapping configuration is invalid or stale
   - Return code: `1`
   - Example: "Mapping references field 'old_field_name' which no longer exists in target table."
   - Recovery: Update mapping configuration with current field names

3. **data_validation_error**: Source/target data is incomplete or incompatible
   - Return code: `1` (for runtime validation failure) or `20` (for pre-write validation)
   - Example: "Account resolution failed: Business Service 'Unknown_BS' has no mapping."
   - Recovery: Add Business Service mapping or filter differently

4. **account_resolution_error**: Cannot uniquely identify target customer account
   - Return code: `1` (Synchronize) or `20` (Validation)
   - Per-record error in Synchronize; validation error in Validate/Preview
   - Example: "Agent 'server-01' in Business Service 'Staging' resolves to 0 accounts."
   - Recovery: Fix Business Service mapping or account lookup configuration

5. **mapping_incompatibility_error**: Source and destination field types incompatible
   - Return code: `20` (caught during validation)
   - Example: "Field mapping 'created_date' (DateTime) -> 'agent_count' (Integer) is incompatible."
   - Recovery: Define conversion rule or select different destination field

6. **network_error**: Transient network failure (timeout, DNS failure, connection reset)
   - Return code: `1`
   - Example: "Request to UAC timed out after 30 seconds. Retrying."
   - Recovery: Synchronize automatically retries up to 3 times; if still failing, check network and retry

7. **rate_limit_error**: ServiceNow or UAC returned HTTP 429 (too many requests)
   - Return code: `1`
   - Example: "ServiceNow rate limit reached. Retry-After: 60 seconds."
   - Recovery: Automatically retries after Retry-After delay; user can manually retry if exhausted

8. **concurrent_edit_error**: Target record modified by another process during write
   - Return code: `1` (for affected record) or `0` with partial success (for unaffected records)
   - Example: "Update skipped for account '12345abcd': concurrent modification detected (sys_updated_on changed)."
   - Recovery: Rerun Synchronize; revalidation will detect current state and reconcile

9. **decision_table_error**: Decision Table operation failed (not found, not supported, adapter unavailable)
   - Return code: `1`
   - Example: "Decision Table adapter not responding at [URL]. Verify installation and permissions."
   - Recovery: Check Decision Table adapter status, restart if needed, retry

10. **partial_write_error**: Some writes succeeded, some failed
    - Return code: `1`
    - Example: "36 records succeeded, 2 failed. See errors for details."
    - Recovery: Fix issues identified in error details, rerun to synchronize remaining objects

---

### Input Validation Requirements

**Field validation rules (checked during Validate Configuration and Preview/Synchronize before writes):**

1. **UAC Credential:** Must be non-null, must have URL and authentication type set
2. **ServiceNow Credential:** Must be non-null, must have URL and authentication method set
3. **Source Dataset:** Must be one of {Agents, Calendars, Scripts, SAP/ABAP Jobs}
4. **Target Mode:** Must be one of {Customer Tables, Decision Tables, Both}
5. **Business Service ID:** Must exist in UAC and have a configured account mapping
6. **Account Mapping:** For multi-object scenarios, must map uniquely to one account (zero or multiple = error)
7. **Field Mappings:** Must reference valid fields in selected tables; no null source/destination pairs
8. **Decision Table Config:** Decision Table sys_id must exist; condition/result field sys_ids must be valid
9. **HTTP Timeout:** Must be integer between 5 and 300 seconds
10. **JSON Configuration:** Must be valid JSON; required keys must be present

**Validation error handling:**
- Report specific field and reason
- Do not silently skip invalid fields
- Do not proceed to writes if validation fails
- Provide actionable recovery message for each error

---

# Authentication Requirements

The extension uses credential objects from the Universal Controller to authenticate to both UAC and ServiceNow.

**UAC Authentication:**
- Supported methods: HTTP Basic Authentication (username/password) or token-based (if configured in UAC)
- Credential storage: UAC credential object with URL, username, password, and auth type
- TLS verification: Enabled by default; custom CA bundle via `REQUESTS_CA_BUNDLE` environment variable
- No session token caching; each API call authenticates independently

**ServiceNow Authentication:**
- Supported methods:
  - HTTP Basic Authentication (username/password for service account)
  - OAuth 2.0 (if configured in ServiceNow; requires pre-configured OAuth client and access token)
  - Custom headers (e.g., API key, if ServiceNow instance uses third-party auth)
- Credential storage: UAC credential object with URL, auth method, and auth details (password or OAuth token)
- TLS verification: Enabled by default; custom CA bundle via `REQUESTS_CA_BUNDLE` environment variable
- Token refresh (OAuth): Not handled by extension; use pre-granted, non-expiring tokens or handle token refresh in credential management

**Credential Delivery:**
- Credentials are resolved by the SDK at task execution time
- Credentials are passed to dynamic choice handlers and action handlers
- Passwords, tokens, and auth headers are kept in memory and never logged or output

---

# Environment Variables

The extension supports configuration through environment variables set at the UAC Agent level:

### UE_HTTP_TIMEOUT

- **Purpose:** Default HTTP request timeout (in seconds) for all REST API calls
- **Type:** Integer
- **Default:** 30 seconds
- **Valid range:** 5–300 seconds
- **Override:** Per-task HTTP timeout field overrides this value
- **Example:** `UE_HTTP_TIMEOUT=45`

### REQUESTS_CA_BUNDLE

- **Purpose:** Path to custom TLS CA certificate bundle for HTTPS verification
- **Type:** File path (absolute)
- **Default:** Uses built-in Mozilla CA bundle (via certifi module)
- **Usage:** Set when behind corporate proxy, using self-signed certificates, or internal CA
- **Example:** `REQUESTS_CA_BUNDLE=/etc/ssl/certs/company-ca-bundle.crt`

### UE_MAX_RECORDS

- **Purpose:** Maximum number of records to fetch from ServiceNow in a single query operation
- **Type:** Integer
- **Default:** 10,000
- **Valid range:** 100–100,000
- **Behavior:** Queries that would exceed this limit are truncated; user must narrow filter
- **Example:** `UE_MAX_RECORDS=5000`

### UE_MAX_OUTPUT_RECORDS

- **Purpose:** Maximum number of records to include in inline STDOUT/Extension Output
- **Type:** Integer
- **Default:** 100
- **Valid range:** 10–1,000
- **Behavior:** Results exceeding this limit are truncated; details written to file; file path returned
- **Example:** `UE_MAX_OUTPUT_RECORDS=50`

---

# Operational Behavior Section

## Dynamic Choice Fields

**Behavior:**
- Dynamic choice fields execute on the selected Universal Agent during task configuration (when user clicks the choice field)
- Each handler has declared dependencies on input fields (credentials, selections, filters)
- Handlers make actual REST calls to UAC and ServiceNow to fetch current data
- Results are paginated: 100 items maximum by default; truncation is indicated
- Search/filter support: users can narrow results if pagination indicates more items exist
- Results are cached for the configuration session only; stale choices after dependent settings change are revalidated
- No ServiceNow writes or UAC mutations occur during discovery
- Distinction between no matches and authentication/network errors is made explicit

**Error handling in dynamic choice discovery:**
- Authentication failure: return error message (do not silently return empty list)
- Network timeout: return error message with retry guidance
- Permission denied: return error message indicating restricted access
- API error: return error message with status code

## Cancel Action

**Behavior:**
- User clicks Cancel in the UAC task instance UI during a running action (Preview or Synchronize)
- Extension detects cancellation and stops issuing new requests
- In-flight requests are allowed to complete (graceful shutdown)
- Completed operations are reported accurately
- Pending operations are skipped with "cancelled" status
- No rollback is attempted; completed changes remain in ServiceNow

**Recovery:**
- User can rerun action after cancellation; rerun will reconcile by stable key without duplicating
- Idempotency ensures no side effects from partial cancellation

## Re-run Capability

**Behavior:**
- The same action can be rerun multiple times without adverse effects
- Synchronize is idempotent: stable source keys prevent duplicate creations
- If a record was successfully written, rerunning does not create a duplicate or reverify old data
- If a record is renamed in UAC, stable key identification detects the change and updates the corresponding ServiceNow record
- Account changes do not cause duplicate creation; account association is part of the stable key
- Preview can be rerun before Synchronize without state changes

**Idempotency:**
- Defined by: UAC Controller identity + source type + stable source ID, qualified by customer identity
- Names alone are not stable keys; use permanent IDs (Agent ID, Calendar ID, Task ID)
- ServiceNow update uses stable key lookup before issuing PATCH

## Progress Reporting

**Progress Bar:**
- No native progress bar support in this extension
- Extensions run to completion in UAC; no interim progress updates

**Logging:**
- Standard logging to UAC task instance logs
- Key milestones logged:
  - "Configuration validation starting..."
  - "Collecting source data from UAC..."
  - "Validating account mappings..."
  - "Writing to ServiceNow: [record] update [fields]..."
  - "Completed [count] writes. [count] errors."
- Sensitive data (credentials, full payloads) never logged
- Errors logged with sanitized diagnostics (HTTP status, not auth headers)

## Dynamic Commands

**No dynamic commands** are implemented for this extension. All configuration is through task form fields and mappings.

---

# Implementation Notes

## Python Compatibility

**Target Python version:** 3.11+

The extension is built using Python 3.11 and must run on UAC Agents with Python 3.11 or later. No earlier Python versions are supported.

## Target Platform

**Platform:** Linux (manylinux_2_17_x86_64)

The extension is built to run on Linux Universal Agents. It uses the manylinux_2_17_x86_64 platform specification, allowing use of precompiled C-extension wheels (e.g., cryptography, PyYAML) that have certified Linux wheels.

**Build system:** setup.py with platform constraints enforced during packaging.

## Third-Party Services and Tools Section

### HTTP Client Library: requests

- **Description:** Python HTTP client library for synchronous REST API calls to UAC and ServiceNow
- **Version:** 2.34.2 (stable)
- **Type:** Pure Python
- **Integration approach:**
  - Used for all UAC REST calls (GET /resources/agent/list, POST /resources/task/list, etc.)
  - Used for all ServiceNow REST calls (GET /api/now/table/*, PATCH /api/now/table/*/*)
  - Configured to use custom CA bundle via REQUESTS_CA_BUNDLE environment variable
  - Retry logic implemented using urllib3's Retry class
  - Timeouts configured via UE_HTTP_TIMEOUT environment variable or per-task field
- **Required dependencies:** urllib3, certifi (transitive)

### Table Formatting Library: tabulate

- **Description:** Formats Python data structures into human-readable ASCII tables for STDOUT output
- **Version:** 0.10.0 (stable)
- **Type:** Pure Python
- **Integration approach:**
  - Used to render validation/preview/sync reports as formatted tables
  - Table format: "rounded_outline" for professional appearance
  - No runtime dependencies

### OpenAPI Snapshot Reference

- **Description:** Local copy of UAC 8.0.0.0 /resources/openapi.json for API contract verification
- **Version:** UAC 8.0.0.0
- **Integration approach:**
  - Serves as reference for documenting supported UAC endpoints and request/response schemas
  - All live calls revalidate against the target Controller's live /resources/openapi.json
  - Used during testing and mocking for contract-driven test generation

### ServiceNow REST API

- **Service:** ServiceNow instance (target release Xanadu or later)
- **Endpoints:**
  - Table API: GET /api/now/table/{tableName}, PATCH /api/now/table/{tableName}/{sys_id}
  - Metadata: GET /api/now/table/sys_db_object, GET /api/now/table/sys_dictionary
  - Decision Tables: Native REST API (Xanadu+) or Scripted REST API adapter (older releases)
- **Authentication:** Basic auth or OAuth 2.0 via credential object
- **Version constraint:** Xanadu (January 2024) or later; older releases require Decision Table Scripted REST API adapter

### Universal Controller REST API

- **Service:** UAC Controller instance (UAC 8.0.0.0 or compatible)
- **Base URL:** Configured via UAC credential
- **Key endpoints:**
  - GET /resources/agent/list, GET /resources/agent/listadv
  - GET /resources/calendar/list, GET /resources/calendar?calendarid=<id>, GET /resources/calendar/customdays?calendarid=<id>
  - GET /resources/script/list
  - POST /resources/task/list (SAP task discovery), GET /resources/task/listadv, GET /resources/task?taskid=<id>
  - GET /resources/businessservice/list
- **Version:** 8.0.0.0 (as per provided OpenAPI snapshot)

---

## Error Handling

**Error Categories:**

1. **Authentication / Authorization Errors**
   - HTTP 401 Unauthorized, HTTP 403 Forbidden, invalid credentials
   - Handled: Report explicitly, do not retry, fail action
   - Recovery: Fix credentials, verify permissions

2. **Network / Connectivity Errors**
   - Timeouts, connection refused, DNS failure, temporary service unavailable
   - Handled: Retry with bounded exponential backoff (3 retries, max delay 30 seconds)
   - Recovery: Check network, verify URLs, retry

3. **Rate Limit Errors**
   - HTTP 429 Too Many Requests, Retry-After header
   - Handled: Retry after specified delay or exponential backoff
   - Recovery: Automatic retry; if exhausted, user can retry

4. **Data Validation Errors**
   - Missing required fields, type mismatches, field not found, incompatible values
   - Handled: Report error before writes, skip affected records
   - Recovery: Fix configuration, correct data, retry

5. **Concurrent Edit Errors**
   - ServiceNow record modified by another process (sys_updated_on changed)
   - Handled: Detect via read-before-write comparison, skip affected record
   - Recovery: Rerun Synchronize; revalidation detects current state

6. **Partial Write Errors**
   - Some writes succeed, some fail during a single Synchronize run
   - Handled: Report completed writes, skip failed records, stop further processing
   - Recovery: Fix issues, rerun to reconcile

**Error Handling Strategy:**

- All errors caught and logged with sanitized diagnostics (no credentials, no full payloads)
- Per-record errors reported in Extension Output with recovery action
- Critical errors (auth, network after retries) cause action failure
- Configuration errors cause action failure before writes
- Partial writes reported accurately; both successful and failed counts included
- No silent failures or data loss

**Recovery Mechanisms:**

- Transient errors (network, rate limit): automatic retry with backoff
- Configuration errors: user fixes configuration, reruns action
- Concurrent edits: rerun Synchronize; stable-key reconciliation prevents duplicates
- Partial writes: rerun Synchronize; idempotency ensures no adverse effects

---

## Resource Cleanup

**Cleanup Scenarios:**

1. **Successful action completion:**
   - No cleanup required; all resources released automatically
   - HTTP connections closed by requests library
   - In-memory data structures garbage collected

2. **Action cancellation:**
   - In-flight HTTP requests allowed to complete gracefully
   - No temporary files or resource locks left behind
   - Completed changes remain in ServiceNow (no rollback)

3. **Action failure:**
   - HTTP connections closed
   - Partial writes remain in ServiceNow (not rolled back)
   - Extension terminates; no background threads or processes left running

4. **Timeout/Exception:**
   - Stack unwound; resources released
   - No partial state stored in ServiceNow or UAC (read-only except for writes during Synchronize)
   - Safe to rerun without cleanup steps

**Strategy:**
- Use Python context managers for resource allocation (with statements)
- No persistent temporary files; use in-memory data structures
- No external process spawning or background threads
- HTTP connections pooled and reused; closed on exception or completion

---

# References

- **Original Requirements Document:** memory/initial-1/requirements.md
- **Original Requirements Q&A Document:** memory/initial-1/requirements-QnA.md
- **UAC OpenAPI Snapshot:** ../openapi.json (UAC 8.0.0.0)
- **ServiceNow Table API Reference:** https://www.servicenow.com/docs/r/xanadu/api-reference/rest-apis/c_TableAPI.html
- **ServiceNow DecisionTableAPI:** https://www.servicenow.com/docs/r/api-reference/server-api-reference/DecisionTableAPI.html
- **ServiceNow Scripted REST APIs:** https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/c_CustomWebServices.html
- **Stonebranch Dynamic Choice Field Tutorial:** https://stonebranchdocs.atlassian.net/wiki/spaces/UC75/pages/206404116/Dynamic%2BChoice%2BField
