---
extension_name: Universal Controller to ServiceNow Table Synchronization
work_item_id: initial-1
ticket_id: ""
status: pending_review
approved_by: ""
approved_at: ""
---

# Universal Controller to ServiceNow Table Synchronization - Implementation Analysis

**Extension Name:** Universal Controller to ServiceNow Table Synchronization (ue-servicenow-table-sync)
**Universal Template Name:** ServiceNow Table Sync
**Builds On:** initial-1
**Target Platform:** Linux

---

## Extension Overview

This Universal Extension synchronizes Universal Controller (UAC) inventory data—agents, calendars, scripts, and SAP jobs—to ServiceNow customer/account tables and Decision Tables. Users configure source datasets, target tables, field mappings, and account associations through a rich task form, then execute validation, preview, or synchronization operations. The extension reads from UAC REST APIs and writes to ServiceNow via standard Table API and Decision Table APIs without modifying Controller state.

---

## Template Fields

### 1. Input Fields

**action**
- **Type**: Choice Field (Single-select)
- **Required When**: always
- **Options**:
  - Validate Configuration - Test connectivity and configuration without writing
  - Preview - Display proposed changes without writing to ServiceNow
  - Synchronize - Execute actual writes to ServiceNow
- **Default**: Preview
- **Validation**:
  - Must be one of the options
- **Purpose**: Specifies which operation to perform

**universal_agent**
- **Type**: Text Field
- **Required When**: always
- **Validation**:
  - Must not be empty
- **Purpose**: Name or ID of the Universal Agent on which this extension executes
- **Example**: uac-agent-prod-01

**uac_credential**
- **Type**: Credential Field
- **Required When**: always
- **Validation**:
  - Must have URL and authentication (Basic or token)
- **Purpose**: UAC controller connection and authentication
- **Example**: Credential named "uac-production"

**servicenow_credential**
- **Type**: Credential Field
- **Required When**: always
- **Validation**:
  - Must have URL and authentication (Basic or OAuth 2.0)
- **Purpose**: ServiceNow instance connection and authentication
- **Example**: Credential named "servicenow-prod"

**target_mode**
- **Type**: Choice Field (Single-select)
- **Required When**: always
- **Options**:
  - Customer Tables - Synchronize to existing customer/account tables
  - Decision Tables - Synchronize to ServiceNow Decision Table rows
  - Both Customer Tables and Decision Tables - Synchronize to both target types
- **Default**: Customer Tables
- **Validation**:
  - Must be one of the options
- **Purpose**: Which target type(s) to synchronize
- **Visible When**: always
- **Shows/Hides**:
  - If "Customer Tables" or "Both": show customer_table, target_fields, field_mappings_customer, account_association_config
  - If "Decision Tables" or "Both": show decision_table, decision_inputs, decision_results, decision_mapping_config

**source_dataset**
- **Type**: Choice Field (Single-select)
- **Required When**: always
- **Options**:
  - Agents - UAC Agent definitions
  - Calendars - UAC Calendar definitions
  - Scripts - UAC Script definitions
  - SAP/ABAP Jobs - UAC SAP task definitions
- **Default**: Agents
- **Validation**:
  - Must be one of the options
- **Purpose**: Which UAC inventory type to collect and synchronize
- **Shows/Hides**:
  - If "Calendars": show include_calendar_custom_days
  - If "SAP/ABAP Jobs": show sap_filter_strategy, and conditionally sap_job_name_filter

**source_scope**
- **Type**: Choice Field (Single-select)
- **Required When**: always
- **Options**:
  - All Objects - Fetch all objects of the selected dataset type
  - By Business Service - Fetch objects associated with a specific Business Service
  - Selected Object - Fetch a single specific object
- **Default**: All Objects
- **Validation**:
  - Must be one of the options
- **Purpose**: Filtering strategy for source objects
- **Shows/Hides**:
  - If "By Business Service": show business_service
  - If "Selected Object": show source_object
  - If "All Objects": show neither

**business_service**
- **Type**: Choice Field (Single-select, Dynamic)
- **Required When**: source_scope value is equal to "By Business Service"
- **Depends On**:
  - uac_credential
  - universal_agent
- **Validation**:
  - Must be one of the dynamically retrieved options
- **Purpose**: Restrict source objects to those associated with a specific Business Service
- **Display Format**: "[Label] | [Business Service ID]"

**source_object**
- **Type**: Choice Field (Single-select, Dynamic)
- **Required When**: source_scope value is equal to "Selected Object"
- **Depends On**:
  - uac_credential
  - universal_agent
  - source_dataset
  - business_service (optional, if present filters to Business Service scope)
- **Validation**:
  - Must be one of the dynamically retrieved options
- **Purpose**: Select a single specific source object to synchronize
- **Display Format**: "[Label (type)] | [Stable ID]"

**customer_table**
- **Type**: Choice Field (Single-select, Dynamic)
- **Required When**: target_mode values are "Customer Tables" or "Both Customer Tables and Decision Tables"
- **Depends On**:
  - servicenow_credential
  - universal_agent
- **Validation**:
  - Must be one of the dynamically retrieved options
- **Purpose**: Select the target customer/account table in ServiceNow
- **Display Format**: "[Table Label (technical name)]"

**target_fields**
- **Type**: Choice Field (Multi-select, Dynamic)
- **Required When**: target_mode values are "Customer Tables" or "Both Customer Tables and Decision Tables"
- **Depends On**:
  - servicenow_credential
  - universal_agent
  - customer_table
- **Validation**:
  - Must be from dynamically retrieved options
  - At least one field must be selected when visible
- **Purpose**: Select which columns in the target customer table to include in mappings
- **Display Format**: "[Field Label (type)] | [field_name]"

**decision_table**
- **Type**: Choice Field (Single-select, Dynamic)
- **Required When**: target_mode values are "Decision Tables" or "Both Customer Tables and Decision Tables"
- **Depends On**:
  - servicenow_credential
  - universal_agent
- **Validation**:
  - Must be one of the dynamically retrieved options
- **Purpose**: Select the target Decision Table in ServiceNow
- **Display Format**: "[Table Name] | [sys_id]"

**decision_inputs**
- **Type**: Choice Field (Multi-select, Dynamic)
- **Required When**: target_mode values are "Decision Tables" or "Both Customer Tables and Decision Tables"
- **Depends On**:
  - servicenow_credential
  - universal_agent
  - decision_table
- **Validation**:
  - Must be from dynamically retrieved options
- **Purpose**: Input condition fields within the selected Decision Table
- **Display Format**: "[Field Label] | [Field sys_id]"

**decision_results**
- **Type**: Choice Field (Multi-select, Dynamic)
- **Required When**: target_mode values are "Decision Tables" or "Both Customer Tables and Decision Tables"
- **Depends On**:
  - servicenow_credential
  - universal_agent
  - decision_table
- **Validation**:
  - Must be from dynamically retrieved options
- **Purpose**: Result/answer fields within the selected Decision Table
- **Display Format**: "[Field Label] | [Field sys_id]"

**customer_record**
- **Type**: Choice Field (Single-select, Dynamic)
- **Required When**: not required (optional override)
- **Visible When**: target_mode values are "Customer Tables" or "Both Customer Tables and Decision Tables"
- **Depends On**:
  - servicenow_credential
  - universal_agent
  - customer_table
- **Validation**:
  - If populated, must be one of the dynamically retrieved options
- **Purpose**: Explicitly select a single customer/account record for single-account synchronization (optional override of account_association_config)
- **Display Format**: "[Account Name] | [sys_id]"

**include_calendar_custom_days**
- **Type**: Boolean Field
- **Required When**: always (when visible)
- **Visible When**: source_dataset value is equal to "Calendars"
- **Default Value**: true
- **Validation**:
  - Must be true or false
- **Purpose**: Include custom business days and holiday definitions in synchronization

**sap_filter_strategy**
- **Type**: Choice Field (Single-select)
- **Required When**: always (when visible)
- **Visible When**: source_dataset value is equal to "SAP/ABAP Jobs"
- **Options**:
  - By Business Service and Type - Fetch SAP tasks in the selected Business Service
  - By Job Name Partial Match - Fetch SAP tasks matching a partial name pattern
  - All SAP Tasks - Fetch all SAP tasks without filtering
- **Default**: By Business Service and Type
- **Validation**:
  - Must be one of the options
- **Purpose**: Filtering strategy for SAP task discovery
- **Shows/Hides**:
  - If "By Job Name Partial Match": show sap_job_name_filter

**sap_job_name_filter**
- **Type**: Text Field
- **Required When**: sap_filter_strategy value is equal to "By Job Name Partial Match"
- **Visible When**: sap_filter_strategy value is equal to "By Job Name Partial Match"
- **Validation**:
  - Must not be empty when visible
  - Must be a valid partial name pattern
- **Purpose**: Partial name pattern to match SAP task names
- **Example**: Z_PROD_

**field_mappings_customer**
- **Type**: Large Text Field
- **Required When**: target_mode values are "Customer Tables" or "Both Customer Tables and Decision Tables"
- **Visible When**: target_mode values are "Customer Tables" or "Both Customer Tables and Decision Tables"
- **Validation**:
  - Must be valid JSON
  - All referenced source and destination fields must exist
- **Purpose**: JSON configuration defining source-to-destination field mappings for customer/account table synchronization
- **Example**: A JSON object with mappings array, account_association, and related_records sections

**account_association_config**
- **Type**: Large Text Field
- **Required When**: target_mode values are "Customer Tables" or "Both Customer Tables and Decision Tables" (and customer_record not specified)
- **Visible When**: target_mode values are "Customer Tables" or "Both Customer Tables and Decision Tables"
- **Validation**:
  - Must be valid JSON
  - Business Service IDs must exist in UAC
- **Purpose**: JSON configuration for how source objects are associated with ServiceNow customer accounts
- **Example**: A JSON object with association_strategy, business_service_to_account mapping, and behavior configuration

**decision_mapping_config**
- **Type**: Large Text Field
- **Required When**: target_mode values are "Decision Tables" or "Both Customer Tables and Decision Tables"
- **Visible When**: target_mode values are "Decision Tables" or "Both Customer Tables and Decision Tables"
- **Validation**:
  - Must be valid JSON
  - Decision Table sys_id must exist in ServiceNow
- **Purpose**: JSON configuration for synchronizing to Decision Table rows and updating condition/result values
- **Example**: A JSON object with decision_table_sys_id, managed_row_strategy, condition_mappings, answer_mappings

**http_timeout_seconds**
- **Type**: Integer Field
- **Required When**: not required (optional)
- **Visible When**: always
- **Default Value**: Uses UE_HTTP_TIMEOUT environment variable (default 30)
- **Validation**:
  - Must be integer between 5 and 300
- **Purpose**: Per-task override for HTTP request timeout

**output_verbosity**
- **Type**: Choice Field (Single-select)
- **Required When**: always
- **Options**:
  - Summary Only - Report aggregate counts and high-level status
  - Summary and Errors - Include per-record error details
  - Full Details - Include per-record changes and mapping details
- **Default**: Summary and Errors
- **Validation**:
  - Must be one of the options
- **Purpose**: Control level of detail in output results

---

### 2. Output Fields

**status**
- **Type**: Text Output
- **Purpose**: Overall status of the action execution
- **Examples**: "Success", "Failed", "Partial Success"

**details**
- **Type**: Text Output
- **Purpose**: Summary of operation results (e.g., counts of created, updated, skipped records)
- **Examples**: "36 customer table records updated, 12 decision rows updated"

**error_summary**
- **Type**: Text Output
- **Visible When**: action is not equal to "Validate Configuration" and errors occurred
- **Purpose**: Summary of errors encountered during execution
- **Examples**: "2 errors: 1 account resolution failure, 1 permission denied"

---

### 3. Field Ordering

The task form uses a **2-column grid layout**. Fields can be displayed in two ways:

- **Full-width fields**: Span both columns (typically for action selection, credentials, primary selections)
- **Half-width fields**: Occupy one column, allowing two fields side-by-side (typically for related pairs)

**Layout Rules:**
- Credential fields ALWAYS span full-width (both columns)
- Action selection fields span full-width
- Related choice fields (e.g., source_dataset and source_scope) can be grouped when logical
- JSON configuration fields (mappings) span full-width

**Field Order (Visual Layout):**

```
┌─────────────────────────────────────────┐
│              action                     │  ← Full-width
├─────────────────────────────────────────┤
│            universal_agent              │  ← Full-width
├─────────────────────────────────────────┤
│          uac_credential                 │  ← Full-width (credential)
├─────────────────────────────────────────┤
│       servicenow_credential             │  ← Full-width (credential)
├─────────────────────────────────────────┤
│           target_mode                   │  ← Full-width
├─────────────────────────────────────────┤
│  source_dataset   │  source_scope       │  ← Half-width pair
├─────────────────────┼───────────────────┤
│      business_service (if visible)      │  ← Full-width
├─────────────────────────────────────────┤
│      source_object (if visible)         │  ← Full-width
├─────────────────────────────────────────┤
│    include_calendar_custom_days (bool)  │  ← Full-width
├─────────────────────────────────────────┤
│   sap_filter_strategy (if visible)      │  ← Full-width
├─────────────────────────────────────────┤
│  sap_job_name_filter (if visible)       │  ← Full-width
├─────────────────────────────────────────┤
│     customer_table (if visible)         │  ← Full-width
├─────────────────────────────────────────┤
│     target_fields (if visible)          │  ← Full-width
├─────────────────────────────────────────┤
│     decision_table (if visible)         │  ← Full-width
├─────────────────────────────────────────┤
│    decision_inputs (if visible)         │  ← Full-width
├─────────────────────────────────────────┤
│    decision_results (if visible)        │  ← Full-width
├─────────────────────────────────────────┤
│   customer_record (if visible)          │  ← Full-width
├─────────────────────────────────────────┤
│  field_mappings_customer (if visible)   │  ← Full-width
├─────────────────────────────────────────┤
│account_association_config (if visible)  │  ← Full-width
├─────────────────────────────────────────┤
│ decision_mapping_config (if visible)    │  ← Full-width
├─────────────────────────────────────────┤
│ http_timeout_seconds │ output_verbosity │  ← Half-width pair
├─────────────────────┼───────────────────┤
│          status (Output Only)           │  ← Full-width
├─────────────────────────────────────────┤
│         details (Output Only)           │  ← Full-width
├─────────────────────────────────────────┤
│      error_summary (Output Only)        │  ← Full-width
└─────────────────────────────────────────┘
```

---

## Actions

### Action 1: Validate Configuration

**Description**: Test connectivity to UAC and ServiceNow, verify target tables and fields exist, validate field mappings for type compatibility, and verify all Business Service mappings are configured. Performs zero writes; returns pass/fail status with detailed error messages.

#### Input Requirements

- **uac_credential** (validates URL and authentication)
- **servicenow_credential** (validates URL and authentication)
- **target_mode** (determines which target validations to perform)
- **source_dataset** (determines which source data to test)
- **source_scope** (determines filtering to apply)
- **business_service** (if scope is "By Business Service")
- **source_object** (if scope is "Selected Object")
- **customer_table** (if target mode includes Customer Tables)
- **target_fields** (if target mode includes Customer Tables)
- **decision_table** (if target mode includes Decision Tables)
- **decision_inputs** (if target mode includes Decision Tables)
- **decision_results** (if target mode includes Decision Tables)
- **field_mappings_customer** (if target mode includes Customer Tables)
- **account_association_config** (if target mode includes Customer Tables)
- **decision_mapping_config** (if target mode includes Decision Tables)
- **include_calendar_custom_days** (if source dataset is Calendars)
- **sap_filter_strategy** (if source dataset is SAP/ABAP Jobs)
- **sap_job_name_filter** (if sap_filter_strategy is "By Job Name Partial Match")

#### Execution Flow

**Step 1: Validate Input Fields**
- Check all required fields are non-null and have valid structure
- Validate JSON syntax for all JSON configuration fields
- Return exit code 20 if validation fails

**Step 2: Test UAC Connectivity**
- Call UAC /resources/openapi.json with provided credential and URL
- On success, retrieve controller identity (name, version, capabilities)
- On failure (401, 403, connection error), record error and report

**Step 3: Test ServiceNow Connectivity**
- Call ServiceNow /api/now/sys_user/me endpoint to verify authentication
- On success, retrieve instance info (name, version)
- On failure (401, 403, connection error), record error and report

**Step 4: Test Source Dataset Access**
- Call UAC endpoint appropriate to source_dataset type (agents, calendars, scripts, tasks)
- Apply filtering based on source_scope (all, business service, selected object)
- Attempt to retrieve at least 1 object to confirm read access
- Record count of objects retrieved and any permission errors
- On failure (0 objects, permission denied), record error

**Step 5: Validate Target Tables Exist**
- For customer tables: call ServiceNow /api/now/table/sys_db_object?name={customer_table}
- For decision tables: call ServiceNow /api/now/table/sn_decision_table?sys_id={decision_table_sys_id}
- Verify table exists and is accessible; record sys_id and metadata
- On failure (table not found, permission denied), record error

**Step 6: Validate Target Fields Exist and Match Types**
- For customer tables: call ServiceNow /api/now/table/sys_dictionary?name={customer_table}
- For each field in target_fields or field_mappings_customer, verify field exists
- For each mapped field, compare source and destination field types for compatibility
- Record each field's type and compatibility status
- On failure (field not found, type incompatible), record error

**Step 7: Validate Business Service Mappings**
- Parse account_association_config JSON
- For each configured Business Service ID, verify it exists in UAC (GET /resources/businessservice?businessserviceid=<id>)
- Verify each Business Service has a mapped account sys_id in ServiceNow
- Attempt external-key lookup for each Business Service to resolve account (optional but recommended)
- Record mapping status for each Business Service
- On failure (Business Service not found, no account mapping, multiple account matches), record error

**Step 8: Validate Decision Table Structure** (if target mode includes Decision Tables)
- Verify decision_inputs and decision_results field sys_ids match fields in the decision table
- Call ServiceNow /api/now/table/sn_decision_table_input and sn_decision_table_result
- Record field validation results
- On failure (field sys_id not found, schema mismatch), record error

**Step 9: Compile Validation Report**
- Aggregate all check results (pass/fail)
- Build validation_checks array with one entry per check
- Determine overall status (all pass = success, any fail = validation error)
- Set return code: 0 for success, 20 for validation error

#### Output Examples

**STDOUT**:
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

**Extension Output result object (JSON)**:

```json
{
  "result": {
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
}
```

#### Success Criteria

- UAC and ServiceNow are both reachable and user is authenticated
- Source dataset is accessible and contains at least 1 object matching scope
- All target tables and fields exist and are accessible
- Business Service mappings are complete and all services exist in both systems
- Field types are compatible (source to destination)
- No permission errors encountered

---

### Action 2: Preview

**Description**: Collect current source data from UAC and target data from ServiceNow, apply field mappings without persisting changes, generate complete plan of proposed changes, report counts and per-record errors. Returns zero ServiceNow writes (read-only).

#### Input Requirements

Same as Validate Configuration, plus:
- Configuration should have passed Validate Configuration check (recommended, not enforced)

#### Execution Flow

**Step 1: Collect Source Data**
- Retrieve all source objects from UAC using configured dataset and scope
- Handle pagination; merge all pages into complete dataset
- Record total objects retrieved, objects in scope, objects with mapping errors
- For each object, extract all relevant fields needed for mapping

**Step 2: Collect Target Data**
- Retrieve all existing records from target ServiceNow table(s)
- For customer tables: fetch all existing customer/account records
- For decision tables: fetch all existing decision rows
- Build lookup maps by stable key for conflict detection in Synchronize

**Step 3: Apply Field Mappings**
- For each source object, apply transformations and field mappings
- Execute mapping logic: count aggregations, field copies, timestamp conversions
- Resolve account associations using Business Service mappings or customer_record override
- Attempt external-key lookup if configured; on failure, record error and skip object
- Validate mapped values match destination field types

**Step 4: Plan Proposed Changes**
- For customer tables: compare mapped data against existing records
  - Identify records to create (stable key not found in ServiceNow)
  - Identify records to update (stable key found, values differ)
  - Identify records to leave unchanged (stable key found, values match)
- For decision tables: compare condition/result values
  - Identify decision rows to create (composite key not found)
  - Identify decision rows to update (composite key found, values differ)
  - Identify decision rows unchanged

**Step 5: Compile Proposed Change Plan**
- Build proposed_changes object with counts of creates, updates, unchanged
- Build errors array with per-record errors (account resolution, mapping errors, validation failures)
- Build sample_proposed_record showing a typical update operation
- Set return code: 0 (preview completes successfully even if errors occur)

#### Output Examples

**STDOUT**:
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
```

**Extension Output result object (JSON)**:

```json
{
  "result": {
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
}
```

#### Success Criteria

- All source data successfully retrieved and processed
- All target data successfully retrieved for conflict detection
- Field mappings successfully applied to all in-scope objects
- Account associations successfully resolved for all objects with valid mappings
- Complete proposed change plan generated and reported
- Return code 0 (preview always succeeds; errors reported in output, not as failures)

---

### Action 3: Synchronize

**Description**: Revalidate configuration, collect source and target data, apply mappings, issue PATCH/POST requests to ServiceNow, handle transient errors with retry, detect concurrent edits, report results accurately.

#### Input Requirements

Same as Preview action.

#### Execution Flow

**Step 1: Revalidate Configuration**
- Perform same validation as Validate Configuration action
- On validation failure, return exit code 1 with configuration error
- Do not proceed to writes if validation fails

**Step 2: Collect and Process Source Data**
- Execute same data collection as Preview action
- Apply same field mappings and account associations
- Identify creates, updates, unchanged

**Step 3: Prepare Write Operations**
- For updates: identify only changed fields (PATCH operations)
- For creates: prepare full record data (POST operations, if enabled in configuration)
- For decision tables: prepare condition and result field updates

**Step 4: Execute Writes with Retry**
- For each write operation (PATCH or POST):
  - Execute HTTP request to ServiceNow
  - On success (200-204): record as succeeded
  - On conflict (409 or sys_updated_on changed): skip record, record as failed
  - On transient error (429, 5xx, timeout): implement exponential backoff, retry up to 3 times
  - On permanent error (4xx non-409, auth): record as failed, skip further retries
- Stop processing remaining records on first non-retryable failure (fail-fast behavior)

**Step 5: Detect Concurrent Edits**
- Before PATCH: read current record's sys_updated_on timestamp
- If current timestamp differs from timestamp captured during Preview, skip update with conflict error
- Report conflict in errors array

**Step 6: Handle Decision Table Updates**
- Use native Decision Table REST API (Xanadu+) or Scripted REST adapter (older releases)
- Update condition and result fields according to decision_mapping_config
- On adapter failure, record error and report

**Step 7: Compile Synchronization Report**
- Build write_results object with counts of created, updated, unchanged, failed per target type
- Build error_summary with error categories and counts
- Build errors array with per-record errors and recovery actions
- Determine overall status: success (0 failures), partial (some failures), failed (no writes completed)
- Set return code: 0 for success, 1 for partial or complete failure

#### Output Examples

**STDOUT**:
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

**Extension Output result object (JSON)**:

```json
{
  "result": {
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
      }
    ]
  }
}
```

#### Success Criteria

- All writes complete without critical errors (authentication, configuration)
- At least one record writes successfully (or all skipped due to unchanged)
- Concurrent edit conflicts properly detected and skipped
- Transient errors automatically retried and either succeed or exhaust retries
- All completed and failed writes accurately reported
- Run ID and timestamps recorded for audit trail

---

## Progress Reporting

Progress Reporting (percentage of completion report) is not required. Extensions run to completion in UAC; no interim progress updates are necessary. Task instance logging provides audit trail of key milestones.

---

## Dynamic Choice Field Population

### business_service

**Purpose**: Populate Business Service dropdown based on UAC controller; support filtering and pagination; provide stable IDs for configuration persistence.

**Fields**: 
- Depends on: uac_credential, universal_agent
- Used in: source_scope choice (when "By Business Service")

**Trigger**: User clicks the choice field dropdown in UAC UI to load available Business Services.

**Execution Flow**:

1. Read uac_credential and extract URL and authentication
2. Call UAC GET /resources/businessservice/list with authentication
3. Parse response; extract business service ID and label
4. Return list of "[Label] | [Business Service ID]" strings (max 100 items)
5. If more than 100 items exist, append note indicating truncation

**Returned to UAC**:
```json
[
  "Production | bs_prod_001",
  "Staging | bs_staging_001",
  "Development | bs_dev_001"
]
```

**Error Handling**:
- Exception is "Timeout": Return empty list, log error message
- Exception is "Authentication": Return error message, do not return empty list
- Exception is "ServiceNotAvailable": Return empty list, log error message
- Exception is "HTTP 404 or endpoint not found": Return empty list, log error message

---

### source_object

**Purpose**: Populate source object dropdown based on selected dataset type, source scope, and optional Business Service filter; provide stable IDs for configuration persistence.

**Fields**:
- Depends on: uac_credential, universal_agent, source_dataset, business_service (optional)
- Used in: source_scope choice (when "Selected Object")

**Trigger**: User clicks the choice field dropdown in UAC UI to load available source objects.

**Execution Flow**:

1. Read uac_credential, source_dataset, and business_service (if present)
2. Determine UAC endpoint based on source_dataset:
   - Agents: GET /resources/agent/list or /resources/agent/listadv
   - Calendars: GET /resources/calendar/list
   - Scripts: GET /resources/script/list
   - SAP Jobs: POST /resources/task/list (filtered by type=taskSap)
3. Apply business_service filter if business_service is selected
4. Call endpoint; parse response; extract object ID and label
5. Return list of "[Label (type)] | [Stable ID]" strings (max 100 items)
6. If more than 100 items exist, append note indicating truncation

**Returned to UAC**:
```json
[
  "prod-app-01 (Agent) | agent_prod_app_01",
  "backup-server (Agent) | agent_backup_001",
  "Z_SYNC_PROD (SAP Job) | task_prod_abap_123"
]
```

**Error Handling**:
- Exception is "Timeout": Return empty list, log error message
- Exception is "Authentication": Return error message, do not return empty list
- Exception is "Business Service not found": Return empty list, log error message
- Exception is "Endpoint not available": Return empty list, log error message

---

### customer_table

**Purpose**: Populate customer table dropdown from ServiceNow; filter to tables accessible to integration user; provide stable technical names for configuration persistence.

**Fields**:
- Depends on: servicenow_credential, universal_agent
- Used in: target_mode (when "Customer Tables" or "Both")

**Trigger**: User clicks the choice field dropdown in UAC UI to load available customer tables.

**Execution Flow**:

1. Read servicenow_credential and extract URL and authentication
2. Call ServiceNow GET /api/now/table/sys_db_object?sysparm_query=name LIKE customer%20OR%20account&sysparm_limit=100
3. Parse response; filter to tables accessible with current credential (test read access if needed)
4. Extract table name and label
5. Return list of "[Table Label (technical name)]" strings (max 100 items)
6. If more than 100 items exist, append note indicating truncation

**Returned to UAC**:
```json
[
  "Customer Account (customer_account)",
  "Account (account)",
  "Customer Record (customer_record)"
]
```

**Error Handling**:
- Exception is "Timeout": Return empty list, log error message
- Exception is "Authentication": Return error message, do not return empty list
- Exception is "Permission denied": Return error message ("Access to table metadata denied"), do not return empty list
- Exception is "No tables found": Return empty list with note ("No customer tables found")

---

### target_field

**Purpose**: Populate target field dropdown from selected customer table; filter to writable fields; provide stable field names for mapping configuration.

**Fields**:
- Depends on: servicenow_credential, universal_agent, customer_table
- Used in: Multiple dynamic choice calls (for target_fields selection)

**Trigger**: User clicks the target_fields choice field dropdown in UAC UI.

**Execution Flow**:

1. Read servicenow_credential and customer_table (technical name)
2. Call ServiceNow GET /api/now/table/sys_dictionary?name={customer_table}&sysparm_limit=200
3. Parse response; filter out system fields (sys_*, internal_*, read-only fields)
4. Extract field name and label, include field type (String, Integer, DateTime, Reference, etc.)
5. Return list of "[Field Label (type)] | [field_name]" strings (max 100 items)
6. Sort by frequency/importance (commonly used fields first)

**Returned to UAC**:
```json
[
  "Managed Agents Count (Integer) | managed_agents_count",
  "Primary Calendar (String) | primary_calendar",
  "Last Sync Timestamp (DateTime) | last_sync_timestamp",
  "Account Name (String) | name"
]
```

**Error Handling**:
- Exception is "Timeout": Return empty list, log error message
- Exception is "Authentication": Return error message, do not return empty list
- Exception is "Table not found": Return error message ("Customer table not found"), do not return empty list
- Exception is "No fields available": Return empty list with note ("No writable fields found in this table")

---

### decision_table

**Purpose**: Populate Decision Table dropdown from ServiceNow; provide stable sys_ids for configuration persistence.

**Fields**:
- Depends on: servicenow_credential, universal_agent
- Used in: target_mode (when "Decision Tables" or "Both")

**Trigger**: User clicks the decision_table choice field dropdown in UAC UI.

**Execution Flow**:

1. Read servicenow_credential and extract URL and authentication
2. Call ServiceNow GET /api/now/table/sn_decision_table?sysparm_limit=100
3. Parse response; extract sys_id (canonical identifier), name, and description
4. Return list of "[Table Name] | [sys_id]" strings (max 100 items)
5. If more than 100 items exist, append note indicating truncation

**Returned to UAC**:
```json
[
  "agent_assignment | dt_sys_id_12345",
  "calendar_routing | dt_sys_id_67890",
  "script_execution | dt_sys_id_11111"
]
```

**Error Handling**:
- Exception is "Timeout": Return empty list, log error message
- Exception is "Authentication": Return error message, do not return empty list
- Exception is "Permission denied": Return error message ("Access to Decision Tables denied"), do not return empty list
- Exception is "No Decision Tables found": Return empty list with note ("No Decision Tables available")

---

### decision_input / decision_result

**Purpose**: Populate input/result field dropdown from selected Decision Table; provide stable field sys_ids for mapping configuration.

**Fields**:
- Depends on: servicenow_credential, universal_agent, decision_table
- Used in: decision_inputs and decision_results (multi-select)

**Trigger**: User clicks decision_inputs or decision_results dropdown in UAC UI.

**Execution Flow**:

1. Read servicenow_credential and decision_table (sys_id)
2. For inputs: Call ServiceNow GET /api/now/table/sn_decision_table_input?decision_table={sys_id}&sysparm_limit=100
3. For results: Call ServiceNow GET /api/now/table/sn_decision_table_result?decision_table={sys_id}&sysparm_limit=100
4. Parse response; extract field name, sys_id, and data type
5. Return list of "[Field Name (type)] | [sys_id]" strings (max 50 items)

**Returned to UAC**:
```json
[
  "environment (Choice) | sys_id_input_001",
  "business_service (String) | sys_id_input_002",
  "assigned_agent (String) | sys_id_result_001",
  "run_calendar (Reference) | sys_id_result_002"
]
```

**Error Handling**:
- Exception is "Timeout": Return empty list, log error message
- Exception is "Authentication": Return error message, do not return empty list
- Exception is "Decision Table not found": Return error message ("Decision Table not found"), do not return empty list
- Exception is "No fields in Decision Table": Return empty list with note ("Decision Table has no input/result fields")

---

## Cancellation Behavior

Default cancellation logic is used (TERM Signal). No custom cancellation logic is required. When a user clicks Cancel in the UAC task instance UI, the extension detects cancellation and stops issuing new requests. In-flight requests are allowed to complete gracefully. Completed operations are reported accurately; pending operations are skipped.

---

## Re-Run Behavior

Re-runs are treated as initial executions. The extension does not maintain special re-run state. However, if this is a re-run of a previous failed Synchronize action, idempotency ensures no adverse effects: stable source keys prevent duplicate creations, and existing records are updated using stable key lookup to avoid duplicating or re-creating records already written in the prior run.

---

## Dynamic Commands

No Dynamic commands should be implemented. All configuration and execution is through task form fields and standard action selection.

---

## Utility Modules

### Required Utility Modules

#### 1. UAC Connection Handler

**Purpose:** Manages HTTP connections to UAC controller, handles authentication, implements retry logic with exponential backoff, and provides safe error reporting.

**Required Capabilities:**
- Initialize authenticated session with UAC controller URL and credential
- Execute GET requests to UAC endpoints (agents, calendars, scripts, tasks, business services)
- Execute POST requests to UAC endpoints (task queries)
- Handle pagination and merge paginated results
- Implement exponential backoff retry for transient errors (429, 5xx)
- Parse OpenAPI schema for endpoint validation
- Raise custom exceptions for auth errors, network timeouts, validation errors
- Handle SSL/TLS verification with custom CA bundle support (REQUESTS_CA_BUNDLE)

**Used By:** Validate Configuration action, Preview action, Synchronize action, all dynamic choice field handlers

---

#### 2. ServiceNow Connection Handler

**Purpose:** Manages HTTP connections to ServiceNow instance, handles authentication (Basic or OAuth 2.0), implements retry logic, and provides safe error reporting.

**Required Capabilities:**
- Initialize authenticated session with ServiceNow URL and credential
- Execute GET requests to ServiceNow Table API endpoints
- Execute PATCH requests for record updates
- Execute POST requests for new records
- Execute queries against metadata tables (sys_db_object, sys_dictionary, sn_decision_table, sn_decision_table_input, sn_decision_table_result)
- Implement exponential backoff retry for transient errors (429, 5xx)
- Detect concurrent edit conflicts via sys_updated_on timestamp comparison
- Raise custom exceptions for auth errors, network timeouts, conflict errors
- Handle SSL/TLS verification with custom CA bundle support
- Support HTTP request timeout override from field or environment variable

**Used By:** Validate Configuration action, Preview action, Synchronize action, all dynamic choice field handlers

---

#### 3. Field Mapper

**Purpose:** Applies source-to-destination field transformations and mappings, handles type conversions, aggregates data from collections, and validates mapping compatibility.

**Required Capabilities:**
- Parse field_mappings_customer JSON configuration
- Support transformation types: count (aggregate), field_copy (direct), timestamp (convert to RFC3339)
- Support aggregation strategies: first_match, all_values, sum, count
- Apply transformations to source data and produce mapped output
- Validate source field types against destination field types
- Report mapping errors per record (source field missing, type incompatible, transformation failed)
- Merge related records (1:N mappings) into account-level fields
- Handle null/missing source values gracefully (skip vs. error based on configuration)

**Used By:** Preview action, Synchronize action

---

#### 4. Account Resolution Handler

**Purpose:** Resolves source objects to target ServiceNow customer accounts using Business Service mappings, external-key lookups, or explicit customer_record selections.

**Required Capabilities:**
- Parse account_association_config JSON configuration
- Look up Business Service mapping to get target account sys_id
- Perform external-key lookups in ServiceNow to resolve accounts by field value
- Detect and report multiple account matches (ambiguous resolution)
- Detect and report zero matches (no account found)
- Handle optional customer_record override (explicit single-account mode)
- Raise custom exceptions for resolution failures
- Support cascading parent→child account lookups (if configured)

**Used By:** Preview action, Synchronize action, Validate Configuration action

---

#### 5. Decision Table Operations Handler

**Purpose:** Manages Decision Table row creation, updates, and condition/result field population; provides abstraction over native API vs. Scripted REST adapter.

**Required Capabilities:**
- Determine if native Decision Table API is available (ServiceNow Xanadu+) or fallback to Scripted REST adapter
- Create composite keys for idempotent row identification (e.g., "bs_prod_001_agent_agent_001")
- Parse decision_mapping_config JSON configuration
- Apply condition mappings (map source fields to decision condition fields)
- Apply result/answer mappings (map source fields to decision result fields)
- Execute PATCH/POST operations on Decision Table rows
- Handle Decision Table adapter unavailability gracefully
- Raise custom exceptions for row creation/update failures

**Used By:** Preview action, Synchronize action, Validate Configuration action

---

#### 6. Output Formatter

**Purpose:** Formats validation results, preview plans, and synchronization reports for both STDOUT (human-readable) and Extension Output (JSON) with respect to output_verbosity setting.

**Required Capabilities:**
- Format validation check results as structured list (passed/failed/details)
- Format preview proposed changes with record counts and samples
- Format synchronization results with write counts and error details
- Implement output_verbosity filtering (Summary Only, Summary and Errors, Full Details)
- Generate ASCII tables for STDOUT (using tabulate library)
- Apply UE_MAX_OUTPUT_RECORDS environment variable cap for inline output
- Generate structured JSON for Extension Output
- Apply credential masking and sanitization (no passwords, tokens, full payloads)

**Used By:** Validate Configuration action, Preview action, Synchronize action

---

#### 7. Exception Mapper

**Purpose:** Translates caught exceptions into extension-specific exceptions with appropriate exit codes, error categories, and recovery actions.

**Required Capabilities:**
- Catch HTTP exceptions (connection errors, timeouts, 4xx/5xx responses)
- Catch JSON parsing errors
- Catch UAC/ServiceNow API errors
- Map to custom exception classes with exit code, error category, and error message
- Provide recovery action text for each exception type
- Log sanitized error details to STDERR (no sensitive data)
- Distinguish between retryable (network, rate limit) and non-retryable errors

**Used By:** All actions and dynamic choice handlers

---

## Exception Mapping Strategy

**HTTP Communication Errors:**
- Connection timeout (socket timeout, read timeout) → NetworkException (exit code 1, retryable)
- Connection refused (ECONNREFUSED) → NetworkException (exit code 1, retryable)
- DNS resolution failure (ENOTFOUND) → NetworkException (exit code 1, retryable)
- SSL/TLS certificate validation error → SSLException (exit code 1, non-retryable)
- Proxy error (407 Proxy Authentication Required) → AuthenticationException (exit code 1, non-retryable)

**HTTP Status Errors:**
- HTTP 401 Unauthorized → AuthenticationException (exit code 1, non-retryable)
- HTTP 403 Forbidden → PermissionException (exit code 1, non-retryable)
- HTTP 404 Not Found → ResourceNotFoundException (exit code 1, non-retryable)
- HTTP 409 Conflict (sys_updated_on mismatch) → ConcurrentEditException (exit code 1, non-retryable)
- HTTP 429 Too Many Requests → RateLimitException (exit code 1, retryable)
- HTTP 5xx Server Error → TemporaryServiceException (exit code 1, retryable)

**Data Validation Errors:**
- JSON parse error → ConfigurationException (exit code 20, non-retryable)
- Missing required JSON key → ConfigurationException (exit code 20, non-retryable)
- Field type mismatch (source to destination) → ValidationException (exit code 20, non-retryable)
- Invalid field reference (field does not exist in table) → ValidationException (exit code 20, non-retryable)
- Business Service not found in UAC → ValidationException (exit code 20, non-retryable)
- Account resolution ambiguous (multiple matches) → ValidationException (exit code 20, non-retryable)

**Mapping/Transformation Errors:**
- Source field missing from source object → MappingException (exit code 1, non-retryable, skip record)
- Transformation logic error (count on non-numeric, etc.) → MappingException (exit code 1, non-retryable, skip record)
- Aggregation failed (incompatible values) → MappingException (exit code 1, non-retryable, skip record)

**External Service Errors:**
- UAC service unavailable (HTTP 503, connection refused) → TemporaryServiceException (exit code 1, retryable)
- ServiceNow service unavailable (HTTP 503, connection refused) → TemporaryServiceException (exit code 1, retryable)
- Decision Table adapter unreachable → TemporaryServiceException (exit code 1, retryable)

**Exit Code Guide:**
- Exit code 0: Action completed successfully; all writes succeeded (if applicable)
- Exit code 1: Action failed after retries exhausted, or permanent error occurred, or partial success (some writes failed)
- Exit code 20: Configuration or validation error; no writes attempted

---

## Dependencies

### 1. External API Dependencies

**1. Universal Controller REST API**
- **Endpoint**: Configured via `uac_credential` (base URL + endpoints)
- **Purpose**: Retrieve agent, calendar, script, and task definitions; query Business Services
- **Protocol**: HTTPS
- **Method**: GET, POST
- **Authentication**: Basic Auth or token-based (configured in credential)
- **Response Format**: JSON
- **Data Retrieved/Sent**:
  - GET /resources/agent/list: agent definitions
  - GET /resources/calendar/list: calendar definitions
  - GET /resources/script/list: script definitions
  - POST /resources/task/list: task definitions with filtering
  - GET /resources/businessservice/list: Business Service definitions
  - GET /resources/openapi.json: API schema for validation

**General API Requirements:**
- UAC version 8.0.0.0 or compatible
- Credential must have read access to all required resource endpoints
- Rate limits: Depends on UAC configuration; extension respects HTTP 429 responses with backoff

---

**2. ServiceNow REST API**
- **Endpoint**: Configured via `servicenow_credential` (base URL + table API endpoints)
- **Purpose**: Read/write customer records, Decision Table rows, retrieve metadata
- **Protocol**: HTTPS
- **Method**: GET, PATCH, POST
- **Authentication**: Basic Auth or OAuth 2.0 (configured in credential)
- **Response Format**: JSON
- **Data Retrieved/Sent**:
  - GET /api/now/table/{tableName}: read customer/account records
  - PATCH /api/now/table/{tableName}/{sys_id}: update customer records
  - POST /api/now/table/{tableName}: create new records
  - GET /api/now/table/sys_db_object: retrieve table metadata
  - GET /api/now/table/sys_dictionary: retrieve field metadata
  - GET /api/now/table/sn_decision_table: retrieve Decision Table definitions
  - GET /api/now/table/sn_decision_table_input: retrieve Decision Table input fields
  - GET /api/now/table/sn_decision_table_result: retrieve Decision Table result fields

**General API Requirements:**
- ServiceNow release: Xanadu (January 2024) or later (native Decision Table API); older releases require Scripted REST API adapter
- Credential must have read/write access to target tables and read access to metadata tables
- Rate limits: Standard ServiceNow limits (typically 1000 requests/min); extension respects HTTP 429 responses

---

### 2. Python version dependency

Python 3.11 or later (3.11, 3.12, 3.13 are supported).

---

### 3. Target Platform

Linux (manylinux_2_17_x86_64). C extension modules with a confirmed manylinux_2_17_x86_64 wheel are viable in addition to pure-Python modules.

---

### 4. Python Library Dependencies

**1. requests**
- **Purpose**: Python HTTP client library for synchronous REST API calls to UAC and ServiceNow
- **Version**: 2.34.2 or compatible
- **Installation**: `pip install requests==2.34.2`
- **Usage**: All HTTP GET/PATCH/POST operations to UAC and ServiceNow
- **Features Used**: Session management, basic auth, custom headers, request timeouts, retry handling via urllib3
- **Note**: Pure-Python module; no platform constraints

**2. tabulate**
- **Purpose**: Formats Python data structures into human-readable ASCII tables for STDOUT output
- **Version**: 0.10.0 or compatible
- **Installation**: `pip install tabulate==0.10.0`
- **Usage**: Render validation/preview/sync reports as formatted ASCII tables in STDOUT
- **Features Used**: Table format "rounded_outline", multi-row formatting
- **Note**: Pure-Python module; no platform constraints

---

### 5. Python Standard Library Dependencies

**1. json**
- **Purpose**: Parse and generate JSON for configuration (field_mappings_customer, account_association_config, decision_mapping_config) and API responses
- **Usage**: Parse field mapping configurations, serialize Extension Output
- **Features Used**: json.loads(), json.dumps()

**2. logging**
- **Purpose**: Standard logging to UAC task instance logs and STDERR
- **Usage**: Log milestones, errors, and sanitized diagnostics
- **Features Used**: logging.getLogger(), logging.DEBUG, logging.ERROR

**3. urllib3**
- **Purpose**: Underlying HTTP library for requests; provides retry logic and connection pooling
- **Usage**: Transitive dependency of requests library; used for exponential backoff retry
- **Features Used**: urllib3.util.Retry, urllib3.exceptions.HTTPError

**4. http.client**
- **Purpose**: Low-level HTTP protocol handling (used by requests and urllib3)
- **Usage**: Support HTTPS connections with custom CA certificate verification
- **Features Used**: HTTP status code constants and error classes

**5. os**
- **Purpose**: Access environment variables for configuration (REQUESTS_CA_BUNDLE, UE_HTTP_TIMEOUT, UE_MAX_RECORDS, UE_MAX_OUTPUT_RECORDS)
- **Usage**: Read environment variables for timeout, CA bundle, and output limits
- **Features Used**: os.environ

**6. datetime**
- **Purpose**: Generate and parse RFC3339 timestamps for field mappings
- **Usage**: Convert UAC timestamps to ServiceNow format
- **Features Used**: datetime.datetime, datetime.timezone

**7. copy**
- **Purpose**: Deep copy of complex Python objects (source records, mapped data)
- **Usage**: Avoid side effects when processing multiple records
- **Features Used**: copy.deepcopy()

---

### 6. CLI Tool Dependencies

No CLI tool dependencies are required. All operations are performed via Python HTTP libraries (requests) and UAC/ServiceNow REST APIs.

---

### 7. Environment Variables

**UE_HTTP_TIMEOUT** (integer, optional):
- **Purpose**: Default HTTP request timeout (in seconds) for all REST API calls to UAC and ServiceNow
- **Default**: 30 seconds
- **Valid range**: 5–300 seconds
- **Usage**: Set timeout for all HTTP requests unless overridden by per-task http_timeout_seconds field
- **Example**: `UE_HTTP_TIMEOUT=45`

**REQUESTS_CA_BUNDLE** (file path, optional):
- **Purpose**: Path to custom TLS CA certificate bundle for HTTPS verification
- **Default**: Uses built-in Mozilla CA bundle (via certifi module, transitive dependency of requests)
- **Usage**: Set when behind corporate proxy, using self-signed certificates, or internal CA
- **Example**: `REQUESTS_CA_BUNDLE=/etc/ssl/certs/company-ca-bundle.crt`

**UE_MAX_RECORDS** (integer, optional):
- **Purpose**: Maximum number of records to fetch from ServiceNow in a single query operation
- **Default**: 10,000
- **Valid range**: 100–100,000
- **Usage**: Limit size of target data retrieval to prevent memory exhaustion; queries exceeding limit are truncated
- **Example**: `UE_MAX_RECORDS=5000`

**UE_MAX_OUTPUT_RECORDS** (integer, optional):
- **Purpose**: Maximum number of records to include in inline STDOUT/Extension Output
- **Default**: 100
- **Valid range**: 10–1,000
- **Usage**: Cap output size for safety; results exceeding limit are truncated with note
- **Example**: `UE_MAX_OUTPUT_RECORDS=50`
