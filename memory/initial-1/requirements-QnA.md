# Requirements Completeness Assessment

## Assessment Summary

**Detail Level: HIGH DETAIL**

The requirements document is exceptionally comprehensive and well-structured. It establishes the core objective clearly (read UAC data via REST APIs, update ServiceNow tables), specifies scope constraints (read-only on Controller, no deletes or arbitrary creates), and defines rigorous acceptance criteria. The document details the complete user workflow, native Dynamic Choice field requirements, REST API endpoints, security principles, and output expectations.

The requirements are not vague. Rather, they leave specific tactical decisions to be made collaboratively: **target platform (Linux/Windows/cross-platform), HTTP library preference, ServiceNow release specifics, and mapping configuration schema**. These decisions don't indicate incomplete requirements—they reflect design decisions that benefit from external input about your infrastructure and deployment strategy.

---

# Platform Compatibility

**Platform Compatibility from Requirements**: Not explicitly stated

**Platform Compatibility Agreement**: [Placeholder - awaiting clarification]

The requirements reference a Python `setup.py` that supports both Linux and Windows builds (lines 107-109 show Linux-specific `manylinux_2_17_x86_64` constraints). The document does not specify which platform(s) the extension must target, making this the foundational decision that gates all other module and dependency choices.

---

# Python Modules and Versions

## Researched Modules

**HTTP Library (requests)**
- **Module Purpose**: Making HTTP requests to UAC REST APIs and ServiceNow REST APIs
- **Version**: 2.34.2 (latest stable)
- **Type**: Pure Python
- **Research Notes**: Stable, mature, widely used. Supports custom CA bundles via environment variables (REQUESTS_CA_BUNDLE, CURL_CA_BUNDLE). Simpler mental model than httpx for synchronous code.

**HTTP Library (httpx)**
- **Module Purpose**: Alternative HTTP client with fine-grained timeout control and encrypted client certificate support
- **Version**: 0.28.1 (latest stable)
- **Type**: Pure Python
- **Research Notes**: Modern async-capable library. Better timeout granularity (separate connect/read/write timeouts). Requires more code complexity for sync-only usage. Environment variable support differs from requests.

**Tabulate**
- **Module Purpose**: Format data as human-readable ASCII tables for STDOUT output
- **Version**: 0.10.0 (latest stable)
- **Type**: Pure Python
- **Research Notes**: Lightweight, well-maintained. Recommended `tablefmt="rounded_outline"` for professional output appearance. No runtime dependencies.

**Certifi**
- **Module Purpose**: CA certificate bundle for HTTPS verification (fallback when custom CA bundle not configured)
- **Version**: 2026.7.22 (latest stable, included as dependency of requests/httpx)
- **Type**: Pure Python
- **Research Notes**: Automatically installed as a transitive dependency. Provides Mozilla's CA certificate bundle.

**PyYAML**
- **Module Purpose**: Parse YAML configuration if mapping examples use YAML format (alternative to JSON)
- **Version**: 6.0.3 (latest stable)
- **Type**: Has manylinux_2_17_x86_64 wheel available; pure-Python fallback also available
- **Research Notes**: Optional—only needed if mappings are YAML-based. Requirements specify "versioned JSON mappings," suggesting JSON is primary format.

**No C-extension dependencies identified as blocking.** All candidate modules are pure-Python or have manylinux_2_17 wheels. Module selection does not create platform portability constraints—the platform decision (Question 1) is orthogonal to module viability.

## Agreed Python Modules and Versions

[Placeholder - to be populated after user answers questions. Will include: HTTP library choice, tabulate, certifi, pyyaml (conditional)]

---

# Question Rationale

The requirements are detailed and concrete. These questions are not about fundamental understanding—they're about **locking in infrastructure and deployment decisions** that your team must make before implementation. Each question directly impacts:

1. **Module selection** (e.g., requests vs httpx depends on timeout granularity needs)
2. **Test strategy** (e.g., Decision Table API capability determines mock setup)
3. **Mapping schema** (e.g., JSON structure must match your instance's table/field names)
4. **ServiceNow adapter delivery** (e.g., whether a Scripted REST API is needed depends on your ServiceNow release)
5. **Account association logic** (e.g., Business Service → account mapping is instance-specific)

---

# Clarifying Questions for Requirements Refinement

## Critical Decision Path Questions

### Question 1: Target UAC Agent Platform

**Question**: Which platform(s) should the extension support when deployed to Universal Agents?

**Options**:
- **Option 1.A (Recommended)**: Linux-only (UAC agents running on Linux hosts)
- **Option 1.B**: Windows-only (UAC agents running on Windows hosts)  
- **Option 1.C**: Cross-platform (same extension archive must work on both Linux and Windows agents)

**Question Type**: New Discussion topic

**Context & Resources**: The `setup.py` build system (lines 107–109) enforces `manylinux_2_17_x86_64` constraints when building on Linux, allowing C-extension modules with Linux-specific wheels. Building on Windows does not apply platform constraints, but a Windows build cannot run on Linux agents. A single cross-platform archive uses only pure-Python modules.
- **Architect Notes reference**: Platform Compatibility and Dependency Bundling section (lines 91–109)

**Question Dependencies**: No dependencies. This is the foundational decision.

**Recommended Answer**: Option 1.A (Linux-only)

**Rationale**: Linux-only targets are the most permissive and align with modern containerized UAC deployments. This choice unlocks the full range of Python modules if performance-critical libraries (e.g., compiled regex, JSON parsing) become necessary. Cross-platform is the next most flexible (pure-Python only); Windows-only is the most restrictive.

**Trade-offs**: 
- **Optimizing for**: Maximum flexibility in future module choices and potential performance optimization.
- **Deprioritizing**: Windows-only agent deployments. If your organization has Windows UAC agents, select Option 1.C (cross-platform) and accept the constraint to pure-Python modules only.

**Requirement Impact**: No changes to the scope, goals, or acceptance criteria. This decision simply gates which Python modules are viable candidates for dependency selection.

**User's Answer**: [Placeholder]

---

### Question 2: HTTP Library Selection (requests vs httpx)

**Question**: Which HTTP client library should the extension use for REST API calls to UAC and ServiceNow?

**Options**:
- **Option 2.A (Recommended)**: `requests` (2.34.2) — simpler mental model, mature ecosystem, widely familiar
- **Option 2.B**: `httpx` (0.28.1) — fine-grained timeout control (separate connect/read/write), better for modern async patterns, encrypted client certificate support

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements specify "request timeouts" (section 8, field configuration) but don't detail whether granular per-phase timeout control is needed. Both libraries support:
- Custom CA bundles via environment variables (REQUESTS_CA_BUNDLE for requests; HTTPX_VERIFY or custom client for httpx)
- Retry logic with bounded backoff (requirements section 9)
- TLS verification enabled by default

The requirements also mention supporting HTTPS and trusted CA bundles. Both libraries handle this, but the timeout strategy differs.

- **requests**: Single timeout value applies to entire request (connect + read + write)
- **httpx**: Can specify separate `connect_timeout`, `read_timeout`, `write_timeout`

**Question Dependencies**: No blocking dependencies. This is a library choice.

**Recommended Answer**: Option 2.A (requests)

**Rationale**: `requests` has the widest familiarity, simpler synchronous API (this extension has no async requirement), and a mature ecosystem. The timeout handling is adequate for UAC/ServiceNow REST calls, where a single timeout covering the entire operation is a reasonable policy. Unless your organization has stringent timeout granularity requirements or uses encrypted client certificates, requests is the pragmatic choice.

**Trade-offs**:
- **Optimizing for**: Simplicity, team familiarity, stable mature library
- **Deprioritizing**: Fine-grained timeout control, encrypted client certificates, modern async capability (not needed here)

**Requirement Impact**: No changes to scope. Impacts internal HTTP handling implementation and test mocking strategy.

**User's Answer**: [Placeholder]

---

### Question 3: ServiceNow Release and Decision Table API Availability

**Question**: Which ServiceNow release(s) will the extension target, and is a REST management API available for Decision Table row updates?

**Options**:
- **Option 3.A (Recommended)**: Assume ServiceNow **Xanadu (latest LTS)** or later; verify REST API support for Decision Table row creation/updates at your instance (the API may be available via `/api/now/decisiontable` or equivalent endpoints depending on installed plugins)
- **Option 3.B**: Specify a target release (e.g., "Xanadu," "Washoe," "Vancouver"); we will verify what Decision Table REST APIs are available for that release and design accordingly
- **Option 3.C**: Decision Table REST API is **NOT available** in your target release; plan to deliver a Scripted REST API adapter as an integration-specific installation artifact (section 7 of requirements)

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 7, lines 196–208) note: *"Verify the supported REST operations in the target release. Where a suitable REST management API is absent, deliver a narrowly scoped Scripted REST API adapter calling supported server-side DecisionTableAPI methods."*

This is conditional: if REST API exists, use it (simpler). If not, the extension must include a supplementary Scripted REST API that the extension calls. The ServiceNow DecisionTableAPI is server-side only and does not expose a standard REST endpoint in all releases.

- **ServiceNow Table API reference**: https://www.servicenow.com/docs/r/xanadu/api-reference/rest-apis/c_TableAPI.html
- **ServiceNow DecisionTableAPI**: https://www.servicenow.com/docs/r/api-reference/server-api-reference/DecisionTableAPI.html
- **Scripted REST API documentation**: https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/c_CustomWebServices.html

**Question Dependencies**: None. However, if Answer = Option 3.C, a follow-up discussion will address the Scripted REST API adapter scope.

**Recommended Answer**: Option 3.B with your specific target release

**Rationale**: ServiceNow release information determines API surface area. Confirming your target release lets us verify exact endpoint availability and design accordingly. Xanadu (latest LTS) is a reasonable default if you don't have a specific constraint.

**Trade-offs**:
- **Optimizing for**: Clarity and certainty about API surface at your instance
- **Deprioritizing**: Generalization across multiple ServiceNow versions (we design for your target release)

**Requirement Impact**: May require addition of Scripted REST API adapter delivery artifact (section 11, deliverables) if REST API is unavailable. No change to core extension logic—only the Decision Table update mechanism.

**User's Answer**: [Placeholder]

---

### Question 4: UAC Controller Version and API Stability

**Question**: What is the target **Universal Controller version** for API calls, and are there known deviations from the UAC 8.0.0.0 OpenAPI snapshot provided?

**Options**:
- **Option 4.A (Recommended)**: Use the provided `../openapi.json` (UAC 8.0.0.0) as the canonical reference; assume the Controller instance will match this version or be backward-compatible with it
- **Option 4.B**: Target a different Controller version (specify version); we will verify API endpoint schemas against that version's `/resources/openapi.json`
- **Option 4.C**: The provided snapshot is outdated; provide the actual Controller's live `openapi.json` endpoint or a recent export

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 5, lines 109–132) reference a local `../openapi.json` snapshot identifying itself as UAC 8.0.0.0. The requirements specifically state: *"Verify request methods, schemas, accepted filter values, and response shapes against the target Controller's /resources/openapi.json before live calls."*

This is sound practice: API contracts can drift between versions. The snapshot defines:
- GET /resources/agent/list, /resources/agent/listadv
- GET /resources/calendar/list, /resources/calendar?calendarid=<id>, /resources/calendar/customdays?calendarid=<id>
- GET /resources/script/list
- POST /resources/task/list (with TaskQueryFilterWsData JSON)
- GET /resources/task/listadv
- GET /resources/task?taskid=<id>

**Question Dependencies**: No blocking dependencies. However, if the Controller version deviates significantly, API integration tests and mocking strategies will be affected.

**Recommended Answer**: Option 4.A

**Rationale**: UAC 8.0.0.0 is a stable, well-documented release. The provided snapshot is a reliable baseline. If your Controller instance is the same or newer, the APIs should be compatible. Testing against the live instance's `/resources/openapi.json` during acceptance testing (section 10, AC02–AC10) will catch any deviations.

**Trade-offs**:
- **Optimizing for**: Using the provided reference snapshot as-is, reducing initial coordination overhead
- **Deprioritizing**: Support for older Controller versions (if you have legacy instances, Option 4.B addresses that)

**Requirement Impact**: No changes to scope or acceptance criteria. If deviations are found during acceptance testing, we'll refine the implementation incrementally.

**User's Answer**: [Placeholder]

---

### Question 5: Mapping Configuration Format and Storage

**Question**: How should mapping configurations (source-to-destination field mappings, account associations, Decision Table conditions) be defined and stored?

**Options**:
- **Option 5.A (Recommended)**: Store mappings as **JSON** in a native **Large Text Field** on the task form; examples provided as template/documentation; schema validated at runtime
- **Option 5.B**: Store mappings in a **UAC Data Script** (versioned, reusable, shareable across multiple task definitions); examples provided as reference scripts
- **Option 5.C**: Hybrid: Small/simple mappings in a Large Text Field; complex/shared mappings in a Data Script; task form has a "Modality" choice field to select which
- **Option 5.D**: Use a **configuration file** bundled in the extension archive; mappings are not per-task but shared across all task instances

**Question Type**: New Discussion topic

**Context & Resources**: 
The requirements (section 8, lines 229–244) state: *"Provide native task fields for action, target mode, source dataset/scope, UAC URL/credential, ServiceNow URL/authentication/credential, Controller identity, dynamic selections, mappings, request timeouts, and page/result limits. Use documented versioned JSON mappings in a native multiline field or supported attached configuration."*

This explicitly allows both inline ("native multiline field") and attached ("supported attached configuration") options. The Large Input Text Modality Selection Pattern (architect notes, lines 725–748) is directly applicable here—users can choose inline or script-based based on mapping complexity.

**Question Dependencies**: None. However, if Answer = Option 5.C, we'll implement the Large Input Text Modality Selection Pattern with choice field logic.

**Recommended Answer**: Option 5.A or 5.C (with 5.C being more flexible for power users)

**Rationale**: 
- **Option 5.A** is simplest for first implementation: JSON in a Large Text Field, easy to test, easy to document with examples.
- **Option 5.C** evolves to meet both simple and complex use cases without friction.

**Trade-offs**:
- **Optimizing for** (5.A): Simplicity, single-task configuration, all configuration visible on form
- **Optimizing for** (5.C): Flexibility, reusability, better for complex/shared mappings
- **Deprioritizing** (5.D): Config-as-code (extension archive level); this approach is less flexible for multi-tenant instances where mappings vary per environment

**Requirement Impact**: No change to functional scope. Impacts task form field organization and configuration persistence strategy.

**Example (Option 5.A JSON structure)**:
```json
{
  "customer_table_mapping": {
    "table": "customer_account",
    "external_key": "external_id",
    "external_key_value": "{{business_service_id}}",
    "field_mappings": [
      {"source": "agent_count", "destination": "managed_agents_count", "type": "count"},
      {"source": "calendar_name", "destination": "primary_calendar", "type": "text"}
    ]
  },
  "decision_table_mapping": {
    "table_sys_id": "{{decision_table_sys_id}}",
    "managed_row_key": "{{business_service_id}}",
    "conditions": [
      {"input_name": "environment", "operator": "IN", "source_field": "agent_os"}
    ],
    "answers": [
      {"result_name": "script_name", "source_field": "script_name"}
    ]
  }
}
```

**User's Answer**: [Placeholder]

---

### Question 6: Business Service Association Policy

**Question**: When a UAC source object (agent, calendar, script, job) belongs to **multiple Business Services**, how should the extension associate it with ServiceNow customer accounts?

**Options**:
- **Option 6.A (Recommended)**: Require explicit configuration: a **Business Service → Account mapping** (e.g., a JSON array or UAC Data Script defining which Business Service IDs map to which ServiceNow account sys_ids). If an object's Business Services are not in the mapping, skip it (error in report, not a silent skip)
- **Option 6.B**: Use the **"selected" Business Service** from the task form as a filter; only process objects whose Business Services include the selected one. If an object belongs to multiple Business Services including the selected one, create/update the account record associated with that selected Business Service's mapping
- **Option 6.C**: Do not support multiple Business Services initially; require source objects to belong to exactly one Business Service. Reject objects with multiple associations as a configuration error

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 3, step 3 and section 5, line 20) reference filtering by Business Service and optional customer association. Section 6 (lines 188–190) states: *"Objects in multiple Business Services require an explicit association policy; do not send data to every customer by default."*

This is a critical data correctness issue: synchronizing the same object to multiple unrelated customer accounts could create data leakage or duplication. The requirement mandates explicit policy, not implicit behavior.

**Question Dependencies**: Blocked by Answer to Question 1 (platform). Not blocked. However, if your instance has complex multi-Business Service setups, Answer = Option 6.A is safer.

**Recommended Answer**: Option 6.A

**Rationale**: Explicit configuration is explicit intent. Option 6.A forces the mapping to be documented, audited, and version-controlled. It prevents silent data leakage and makes troubleshooting straightforward.

**Trade-offs**:
- **Optimizing for**: Data correctness, auditability, zero silent failures
- **Deprioritizing**: Convenience for simple single-Business-Service setups (Option 6.B is simpler but less safe)

**Requirement Impact**: Adds a required configuration field: Business Service → Account mapping. May be stored as JSON (alongside mappings, Question 5) or as a separate Data Script. No change to functional scope; pure configuration clarity.

**User's Answer**: [Placeholder]

---

### Question 7: Related Record Aggregation Strategy

**Question**: When multiple source objects (e.g., multiple Agents, multiple ABAP steps, multiple calendars) belong to the same customer account, how should the extension represent them in ServiceNow related records?

**Options**:
- **Option 7.A (Recommended)**: Aggregate into **existing related-record tables** (e.g., if customer_account has a relationship field `agents` linking to a one-to-many `customer_agents` junction table, create or update one record per Agent per customer)
- **Option 7.B**: Aggregate into **existing customer account fields** (e.g., a multi-line text field, a JSON field, a count field). Requires explicit data transformation in the mapping (e.g., "concatenate agent names into a multi-line field")
- **Option 7.C**: Both A and B: allow the mapping configuration to specify which aggregation strategy per field (some fields use related records, others use account fields)

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 6, lines 183–186) state: *"Handle many Agents/jobs per account deliberately: aggregate into appropriate existing fields or use existing related inventory records. Never repeatedly overwrite one scalar account field with different source records. If existing fields cannot represent the data, report the schema gap; do not put inventory into unrelated fields such as account name or contact details."*

This is about data modeling: your ServiceNow instance already has tables and relationships designed to hold this data. The question is whether to use related records (1:N relationships) or aggregation into account fields (N:1 transformation).

**Question Dependencies**: Blocked by the answer to Question 5 (mapping format). Mapping configuration must include the aggregation strategy per field.

**Recommended Answer**: Option 7.C

**Rationale**: Different data types have different natural representations. Agents are naturally 1:N with an account (many agents per customer). Calendars might fit into a single "primary_calendar" field or a related-record table. Flexibility in configuration lets the mapping be accurate for each field type without introducing data duplication or schema misuse.

**Trade-offs**:
- **Optimizing for**: Correctness, schema-aware data representation
- **Deprioritizing**: Simplicity (requires mapping configuration to be more explicit about aggregation)

**Requirement Impact**: Mapping schema (Question 5) must include an `aggregation_strategy` field per mapped field. No change to acceptance criteria or scope.

**Example mapping addition**:
```json
"field_mappings": [
  {
    "source": "agents",
    "strategy": "related_record",
    "related_table": "customer_agents",
    "related_key": "customer_account",
    "source_key": "agent_id"
  },
  {
    "source": "primary_calendar",
    "strategy": "field_aggregate",
    "aggregation": "first_match"
  }
]
```

**User's Answer**: [Placeholder]

---

### Question 8: Account Association Handling — Missing or Ambiguous Matches

**Question**: When the extension cannot uniquely identify a ServiceNow account for a source object (no match, multiple matches, or ambiguous match), what should the behavior be?

**Options**:
- **Option 8.A (Recommended)**: Report error and skip that source object; include details in the error report (e.g., "Agent 'server-01' in Business Service 'Production' has no mapped account"). Do NOT create an account or silently skip
- **Option 8.B**: Allow configuration to specify fallback behavior per source object (e.g., "if no exact match, use default account" or "if multiple matches, pick the first")
- **Option 8.C**: Hybrid: Report error for ambiguous/missing matches by default; allow optional configuration to enable fallback behavior for specific Business Services or source types

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 6, lines 188–189) explicitly state: *"Zero or multiple account matches is a mapping error, never permission to create an account or update all matches."*

And (section 8, lines 247–250): *"Defaults: ... Missing customer account: error; never create."*

This is a firm requirement: no implicit behavior. The question is how detailed the error reporting should be and whether any fallback is allowed.

**Question Dependencies**: Related to Question 6 (Business Service association). Both govern customer identification.

**Recommended Answer**: Option 8.A

**Rationale**: Explicit error reporting with details makes troubleshooting immediate. Matching errors are usually configuration issues, not operational failures. Clear reporting helps users fix their Business Service mappings or external-key lookups.

**Trade-offs**:
- **Optimizing for**: Data correctness, auditability, visibility into why objects are skipped
- **Deprioritizing**: Convenience for complex Business Service setups (Option 8.B adds flexibility but also adds silent complexity)

**Requirement Impact**: Output fields (STDOUT and Extension Output) must include detailed per-object error messages. Acceptance criteria AC04 and AC08 directly apply.

**User's Answer**: [Placeholder]

---

### Question 9: SAP Task Discovery and Filtering

**Question**: For SAP/ABAP job discovery, should the extension support filtering by:

**Options**:
- **Option 9.A (Recommended)**: Filter by **job type** (e.g., `type=taskSap` in the list request), **Business Service** (optional), and **partial name matching** (optional); no filtering by individual ABAP program names or variant names
- **Option 9.B**: Full filtering: by job type, Business Service, ABAP program name (exact or partial), ABAP variant name, and custom Controller filter parameters if exposed in the OpenAPI schema
- **Option 9.C**: No filtering; fetch all SAP tasks and let the mapping configuration filter by ABAP program name or variant name post-retrieval

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 5, lines 115–132) list the OpenAPI endpoints:
- GET /resources/task/listadv (with documented query parameters)
- POST /resources/task/list (with TaskQueryFilterWsData JSON)

The snapshot states: *"Verify the accepted SAP filter representation for the chosen list endpoint; display labels and serialized type values may differ."* (line 130–131)

Filtering at the source (REST call) is more efficient than post-retrieval filtering; however, the OpenAPI schema must be checked for supported parameters.

**Question Dependencies**: Related to Question 4 (UAC Controller version). The OpenAPI snapshot will document which filter parameters are available.

**Recommended Answer**: Option 9.A

**Rationale**: Job type and Business Service filtering are common use cases and likely supported by the OpenAPI schema. Full filtering by ABAP program/variant names adds complexity and requires deep knowledge of the Controller's data model. Option 9.C (post-retrieval filtering in the extension) is viable if filtering at the source isn't available.

**Trade-offs**:
- **Optimizing for**: Efficient source-level filtering, simple task form
- **Deprioritizing**: Deep SAP-specific filtering (can be added in a later work item if needed)

**Requirement Impact**: Task form fields for source discovery and filtering. Acceptance criteria AC03 (all four source datasets work) includes SAP; filtering specifics are not acceptance-level requirements.

**User's Answer**: [Placeholder]

---

### Question 10: Calendar Custom Days Representation

**Question**: When discovering and synchronizing calendar custom days (business days, custom/local holidays), how should they be represented in the ServiceNow mapping?

**Options**:
- **Option 10.A (Recommended)**: Serialize custom days as a **JSON array or text field** in the customer account or related calendar record (e.g., `custom_days: [{"date": "2026-12-25", "label": "Company Holiday"}]`). Store the calendar definition metadata, not the calculated future schedules
- **Option 10.B**: Store only the **calendar ID** and calendar **name** in the customer account; custom day details are fetched on-demand from the Controller during synchronization (no pre-computed storage)
- **Option 10.C**: Create or update a **related calendar table** (e.g., `customer_calendars`) with one record per calendar per account, including custom day details as a JSON column or related records

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 2, line 30–32) define: *"'Loaded calendars' means calendar definitions currently available in UAC, including configured business/custom days when requested. Calculating future schedules or extracting SAP factory calendars is not assumed."*

And (section 5, line 139) state the endpoint: GET /resources/calendar/customdays?calendarid=<id>

The requirements specify fetching custom day definitions, not calculating future schedule. This is about calendar metadata, not schedule projection.

**Question Dependencies**: Blocked by Question 7 (related-record aggregation). Related calendars might be modeled as related records or aggregated into account fields.

**Recommended Answer**: Option 10.A or 10.C (preferred 10.C if your instance has existing related calendar tables)

**Rationale**: 
- **Option 10.A**: Simple, fits in existing account fields if you have a JSON-capable field
- **Option 10.C**: Scalable if you need to track multiple calendars per account with full metadata

**Trade-offs**:
- **Optimizing for**: Storing metadata once, for reuse in downstream processes
- **Deprioritizing**: On-demand fetching (Option 10.B) works but adds latency and tight coupling to the Controller

**Requirement Impact**: Mapping schema (Question 5) must include calendar field representation. Acceptance criteria AC03 includes "multiple Agents with different calendars" scenario.

**User's Answer**: [Placeholder]

---

### Question 11: Preview vs. Synchronize Behavioral Differences

**Question**: Beyond not writing to ServiceNow, are there other functional differences between Preview and Synchronize actions?

**Options**:
- **Option 11.A (Recommended)**: Preview and Synchronize **share identical collection, validation, and planning logic**; Synchronize applies the write operations, Preview reports what *would* be written but doesn't persist; both return the same proposed change counts
- **Option 11.B**: Preview is **limited in scope** (e.g., fetch only first page of source objects for a quick preview); Synchronize fetches complete data. Preview is a quick sanity check, not a full dry-run
- **Option 11.C**: Preview includes **additional verbosity** (e.g., field-by-field change details, expected post-write state) that Synchronize omits for performance

**Question Type**: Verification of existing requirement

**Context & Resources**: 
The requirements (section 10, lines 274–276) state: *"Preview and Synchronize share collection/normalization/planning logic. Synchronize revalidates current state instead of blindly applying an old preview."*

This is clear: they share logic and Preview is a full dry-run. Option 11.A aligns with this. The question exists to confirm your expectations and ensure the implementation detail is correct.

**Question Dependencies**: None. This is clarification on existing requirement.

**Recommended Answer**: Option 11.A

**Rationale**: The requirement is explicit. Full dry-run (Preview) gives users confidence in proposed changes before they're applied.

**Trade-offs**:
- **Optimizing for**: User confidence, correctness (no surprises in production)
- **Deprioritizing**: Preview performance (full data fetch may be slower, but correctness wins)

**Requirement Impact**: No change. This is a verification of existing requirement intent.

**User's Answer**: [Placeholder]

---

## Essential Input/Output Questions

### Question 12: Dynamic Choice Field Performance and Limits

**Question**: For the Dynamic Choice fields (customer_table, decision_table, target_field, etc.), what are the acceptable performance characteristics and result limits?

**Options**:
- **Option 12.A (Recommended)**: Dynamic choices are loaded on-demand during task configuration (when a user clicks a choice field); limit results to **100 items** by default; indicate truncation if more exist; require filter/search to narrow (implements the "Pagination/Search" pattern from architect notes)
- **Option 12.B**: Load **all results** (unlimited); no pagination/search; acceptable if instances typically have <500 tables/decisions
- **Option 12.C**: Configurable limits via **environment variable** (e.g., `UE_CHOICE_LIMIT=50`); default to 100; allow power users to override

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 4, lines 100–107) specify: *"Support filtering/search and pagination within documented SDK result limits. Indicate result truncation and require a narrower filter when limits are reached. ... Distinguish no matches from authentication, permission, network, and API errors."*

The architect notes (lines 721–722) mention the Large Output Safety Net Pattern using `UE_MAX_OUTPUT_RECORDS` for inline output. A similar pattern could apply to choice field loading.

**Question Dependencies**: None. However, if Answer = Option 12.C, this drives environment variable strategy.

**Recommended Answer**: Option 12.A

**Rationale**: 100-item limit with search/filter is a good balance. Prevents slow UI loading with thousands of choices. Most ServiceNow instances have <100 customer tables; if they have more, filtering is necessary anyway.

**Trade-offs**:
- **Optimizing for**: Responsive task form, clear indication when results are truncated
- **Deprioritizing**: Unlimited results (requires more server resources; may slow form loading)

**Requirement Impact**: Dynamic choice handler implementation must include pagination and search. No change to acceptance criteria; AC01 covers dynamic choice behavior.

**User's Answer**: [Placeholder]

---

### Question 13: Decision Table Condition/Result Field Mapping

**Question**: For Decision Table mappings, how should condition and result fields be identified and matched?

**Options**:
- **Option 13.A (Recommended)**: Use **Decision Table field sys_ids** (unique identifiers) as the canonical identifiers; require mapping configuration to reference sys_ids; display **human-readable labels** alongside sys_ids in the UI to aid selection
- **Option 13.B**: Use **field names** (strings); simpler for users but fragile if fields are renamed
- **Option 13.C**: Hybrid: sys_ids in the implementation, but provide a **lookup table or mapping file** that translates human-readable names to sys_ids for configuration convenience

**Question Type**: New Discussion topic

**Context & Resources**: 
The requirements (section 7, lines 206–217) specify: *"Deterministic managed row key, including customer/source identity as applicable, with a documented way to store or resolve it using the existing schema. ... Require a decision mapping containing: Decision Table sys_id and existing input/result identifiers."*

The word "identifiers" is intentionally vague—could be names or sys_ids. sys_ids are stable across renames; names are human-readable but fragile.

**Question Dependencies**: Related to Question 5 (mapping format). Mapping schema must document whether identifiers are sys_ids, names, or both.

**Recommended Answer**: Option 13.A

**Rationale**: sys_ids are permanent, stable identifiers. If a Decision Table field is renamed, a sys_id-based mapping continues to work. Configuration can show both sys_id and label for clarity.

**Trade-offs**:
- **Optimizing for**: Robustness, stable references across instance changes
- **Deprioritizing**: Configuration simplicity (users need to know or discover sys_ids)

**Requirement Impact**: Dynamic choice handlers must return both sys_id and label. Mapping schema must document sys_id references. Acceptance criteria AC06 (Decision conditions/results change as configured) implicitly requires stable field references.

**User's Answer**: [Placeholder]

---

### Question 14: Output Field Verbosity and Truncation

**Question**: When the extension produces STDOUT or Extension Output with large datasets (many records, many fields per record), what should the behavior be?

**Options**:
- **Option 14.A (Recommended)**: Use the **Large Output Safety Net Pattern** (architect notes, lines 710–722): cap inline output at **100 records** via environment variable `UE_MAX_OUTPUT_RECORDS`; when truncated, include metadata indicating total count and limit; for complete results, write to a **file and return file path** in Extension Output
- **Option 14.B**: Output **all records** inline (unlimited); no truncation; acceptable if typical runs sync <100 records
- **Option 14.C**: Configurable verbosity: use a **choice field** (e.g., "Output Options") to let users select "Summary Only," "Per-Record Details," or "Full Details" at task definition time

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 10, line 291) specify: *"Return a readable task summary and structured JSON containing run ID, action, source dataset, target IDs, start/end times, status, read/matched counts, planned/actual created and updated counts, unchanged/skipped/failed counts, and sanitized per-record errors."*

This suggests summary + per-record errors, but doesn't specify limits. The architect notes provide two applicable patterns: Large Output Safety Net and Output Verbosity Selection.

**Question Dependencies**: None, but related to overall output strategy.

**Recommended Answer**: Option 14.A + Option 14.C (hybrid)

**Rationale**: Default to safe truncation (Option 14.A) for large runs. Offer verbosity selection (Option 14.C) for users who want summary vs. details. This balances safety with flexibility.

**Trade-offs**:
- **Optimizing for**: Database storage efficiency (UAC stores STDOUT/Extension Output), clarity under load
- **Deprioritizing**: Showing all records inline (requires more storage, may exceed database limits)

**Requirement Impact**: Implement Output Verbosity Selection Pattern and Large Output Safety Net Pattern. Environment variable `UE_MAX_OUTPUT_RECORDS` (default 100). No change to acceptance criteria; AC10 covers partial writes and error reporting.

**User's Answer**: [Placeholder]

---

## Extension-Specific Configuration Questions

### Question 15: Cancel Action and In-Flight Request Handling

**Question**: If a user cancels a running Synchronize task (clicks Cancel in the UAC UI), what should the extension do with in-flight API requests and partially applied changes?

**Options**:
- **Option 15.A (Recommended)**: When cancellation is detected, finish current request if in progress; stop issuing new requests; skip pending updates; report what was completed and what was skipped
- **Option 15.B**: Immediately abort all requests (don't wait for completion); report what was completed and what failed
- **Option 15.C**: Provide no custom cancellation logic; use default behavior (framework sends SIGTERM; extension exits without cleanup)

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The architect notes (lines 477–491) detail Cancel behavior. The default is SIGTERM; custom logic can be implemented if needed. The requirements (section 3, lines 59–65) don't explicitly mention cancel behavior for Preview/Synchronize actions, but cancel is available (section 34, "Task Instance Commands").

**Question Dependencies**: None. This is an operational detail.

**Recommended Answer**: Option 15.A

**Rationale**: Graceful handling—complete what's in flight, stop new work. This balances responsiveness to cancellation with data consistency. Partially applied changes are reported (acceptance criteria AC10).

**Trade-offs**:
- **Optimizing for**: Data consistency, user visibility into what was applied
- **Deprioritizing**: Immediate cancellation (Option 15.B may leave databases in partial state)

**Requirement Impact**: Implementation detail only. No change to task form or acceptance criteria. The architect notes guidance on cancellation applies here.

**User's Answer**: [Placeholder]

---

### Question 16: Configuration Validation Depth

**Question**: When validating configuration (the "Validate Configuration" action), what should be checked?

**Options**:
- **Option 16.A (Recommended)**: Validate:
  - Connectivity to UAC and ServiceNow (ping URLs, verify credentials)
  - Readable source existence (fetch 1 agent/calendar/script/job to confirm access)
  - Target table existence and field accessibility
  - Mapping field compatibility (source/destination types match, no incompatible conversions)
  - Account matching (can find accounts for configured Business Services)
  - Do NOT test write access (no actual PATCH/POST to ServiceNow)

- **Option 16.B**: Minimal validation only (connectivity and credentials); defer field compatibility checks to Preview
- **Option 16.C**: Full validation including write access test (issue a trial PATCH to a test record or a "read-your-own-write" test); confirm permissions before user sees "Synchronize" button

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 3, lines 59–62) list the "Validate Configuration" action: *"Validate Configuration: verify connectivity, readable sources, target existence, mappings, field compatibility, account matching, and Decision Table capabilities. Do not test write access by changing records; report unverified permissions."*

This is explicit: don't test write access. Option 16.A aligns with this.

**Question Dependencies**: Related to Question 8 (account matching). Validation should include account matching logic.

**Recommended Answer**: Option 16.A

**Rationale**: The requirement is explicit. Validation confirms you *can* read and *can* access; testing writes is deferred to Preview (dry-run).

**Trade-offs**:
- **Optimizing for**: Confidence in configuration, non-destructive validation
- **Deprioritizing**: Pre-flight permission testing (users discover write permission issues in Preview, not in Validate)

**Requirement Impact**: "Validate Configuration" action implementation. Acceptance criteria AC02 (zero writes during validation/preview) directly applies.

**User's Answer**: [Placeholder]

---

### Question 17: Return Codes and Exit Status Strategy

**Question**: Which exit code convention should the extension use to report success, validation errors, and partial failures?

**Options**:
- **Option 17.A (Recommended)**: Use the standard convention from architect notes:
  - `0`: Full success (all intended operations completed)
  - `1`: Complete failure (no operations completed; error in setup or early validation)
  - `20`: Validation error (detected before any writes)
  - No code for partial success in this design (Synchronize doesn't support Fail Fast vs. Continue modes)

- **Option 17.B**: Add support for partial success (Partial Success / Error Behavior Pattern from architect notes):
  - `0`: Full success
  - `1`: Complete failure or Fail Fast mode (stop on first error)
  - `2`: Partial success (Continue mode completed but some items failed)
  - `20`: Validation error

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The architect notes (lines 395–412) recommend Option 17.A as the simplest approach. The Partial Success / Error Behavior Pattern (lines 660–675) is optional and adds complexity. The requirements don't specify partial success behavior; they state (section 10, line 292): *"Success requires all requested target operations to succeed; partial writes and configuration/required-source failures must produce a nonzero task result."*

This suggests Option 17.A (all-or-nothing for a given run).

**Question Dependencies**: Related to overall error handling strategy and user expectations.

**Recommended Answer**: Option 17.A

**Rationale**: Simpler, aligns with requirements. A failed Synchronize is a failed Synchronize—no ambiguity. Users can rerun after fixing issues.

**Trade-offs**:
- **Optimizing for**: Clarity, simplicity
- **Deprioritizing**: Partial run completions (Option 17.B allows "continue on error")

**Requirement Impact**: Output format (exit code, status description) in Extension Output. Acceptance criteria AC10 includes error reporting; this specifies the code scheme.

**User's Answer**: [Placeholder]

---

## Environment Variable Configuration Questions

### Question 18: Custom TLS Certificate Bundle Configuration

**Question**: How should users provide a custom TLS CA certificate bundle for ServiceNow or UAC if they're behind a corporate proxy or use self-signed certificates?

**Options**:
- **Option 18.A (Recommended)**: Use standard environment variables:
  - `REQUESTS_CA_BUNDLE`: Path to CA bundle for requests library
  - Both set at UAC task definition level (Environment Variables field)
  - No extension code changes needed; requests library respects these automatically
  
- **Option 18.B**: Create a task form **Text Field** for custom CA bundle path; extension code explicitly uses it
- **Option 18.C**: Hybrid: environment variables are the primary mechanism; document in setup guide; provide an optional task field as a fallback for environments where setting env vars is complex

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 8, line 253) specify: *"TLS verification: enabled; support a configured trusted CA bundle."*

The architect notes (lines 795–809, HTTPX vs REQUESTS section) discuss CA bundle handling and environment variables. Standard practice is using environment variables (`REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`).

**Question Dependencies**: Related to Question 2 (HTTP library choice). The library used determines which environment variables apply.

**Recommended Answer**: Option 18.A

**Rationale**: Standard, no extension code needed, respects deployed agent's environment. Simplest for users.

**Trade-offs**:
- **Optimizing for**: Standard approach, minimal code
- **Deprioritizing**: Per-task customization (Option 18.B allows task-level override but adds UI complexity)

**Requirement Impact**: Documentation only. Task form doesn't need new fields if Option 18.A is chosen. Setup guide documents environment variable configuration.

**User's Answer**: [Placeholder]

---

### Question 19: HTTP Request Timeout Configuration

**Question**: What default and configurable timeout values should apply to HTTP requests to UAC and ServiceNow?

**Options**:
- **Option 19.A (Recommended)**: 
  - Default timeout: **30 seconds** (reasonable for most REST calls)
  - Configurable via **environment variable** `UE_HTTP_TIMEOUT` (in seconds)
  - Task form has an optional **Integer Field** for per-task timeout override
  - All HTTP calls use the same timeout value

- **Option 19.B**: Granular timeouts (separate values for connect, read, write phases):
  - `UE_HTTP_CONNECT_TIMEOUT`: 10 seconds
  - `UE_HTTP_READ_TIMEOUT`: 30 seconds
  - `UE_HTTP_WRITE_TIMEOUT`: 20 seconds
  - Viable if using httpx (fine-grained timeout support)

- **Option 19.C**: Simple, fixed timeout (no configuration); use requests library default (~30 seconds)

**Question Type**: Clarification on existing requirement

**Context & Resources**: 
The requirements (section 8, line 233) specify: *"Provide native task fields for ... request timeouts ..."*

This suggests some timeout configurability at the task level. The architect notes recommend environment variables for non-commonly-tuned parameters (lines 132–137).

**Question Dependencies**: Related to Question 2 (HTTP library). httpx supports granular timeouts; requests does not.

**Recommended Answer**: Option 19.A

**Rationale**: 30-second default is reasonable for REST calls. Environment variable + optional task field provides both deployment-wide and per-task control. Simple to understand.

**Trade-offs**:
- **Optimizing for**: Simplicity, sufficient for most use cases
- **Deprioritizing**: Granular per-phase timeouts (Option 19.B is more complex)

**Requirement Impact**: Task form adds optional Integer Field for per-task timeout. Environment variable `UE_HTTP_TIMEOUT` documented in setup guide. No change to functional scope.

**User's Answer**: [Placeholder]

---

### Question 20: Result Pagination and Record Limits

**Question**: For ServiceNow queries that return many records (e.g., fetch all customer accounts to perform lookups), what page size and total record limits should apply?

**Options**:
- **Option 20.A (Recommended)**: 
  - Page size: **250 records** (reasonable balance between query efficiency and per-page memory)
  - Max total records to fetch: **10,000** (configurable via `UE_MAX_RECORDS=<number>`)
  - If a query would exceed the limit, report truncation and require a narrower filter
  - Document in setup guide

- **Option 20.B**: No limits; fetch all records (acceptable if instances are small)

- **Option 20.C**: Strict limits: page size 100, max total 1,000; optimized for memory-constrained agents

**Question Type**: New Discussion topic

**Context & Resources**: 
The requirements (section 9, lines 268–269) state: *"Use bounded ServiceNow pages, deterministic ordering, and documented continuation information. A short/empty page may reflect ACL filtering after page limits; do not silently treat it as proof of exhaustion."*

This implies pagination with awareness of potential filtering. The architect notes Large Output Safety Net Pattern suggests capping at 100–1000 records for output; internal fetches can be higher.

**Question Dependencies**: Related to Question 12 (dynamic choice limits) and Question 14 (output truncation).

**Recommended Answer**: Option 20.A

**Rationale**: 250 per page + 10,000 total is a reasonable balance. Covers typical deployments without exhausting memory on agents. Configurable for power users.

**Trade-offs**:
- **Optimizing for**: Robustness, memory efficiency, scalability
- **Deprioritizing**: Fetching all records in very large instances (users can adjust via env var)

**Requirement Impact**: Pagination logic in ServiceNow fetching. Environment variable `UE_MAX_RECORDS`. Acceptance criteria AC09 (multi-page reads complete correctly) directly applies.

**User's Answer**: [Placeholder]

---

# Summary

This Q&A document provides **20 clarifying questions** organized into four categories:

1. **Critical Decision Path Questions** (1–11): Platform selection, HTTP library, ServiceNow release, UAC version, mapping format, Business Service association, related record aggregation, account matching, SAP filtering, calendar representation, and Preview/Sync verification
2. **Essential Input/Output Questions** (12–14): Dynamic choice performance, Decision Table field identification, output verbosity
3. **Extension Configuration Questions** (15–17): Cancellation handling, validation depth, return codes
4. **Environment Variables** (18–20): TLS certificates, HTTP timeouts, pagination limits

**Each question includes:**
- Multiple realistic options (recommended as primary choice)
- Clear context and references to requirements / architect notes
- Dependency information (which answers affect this question)
- Explicit trade-offs
- Recommended answers (to be auto-applied as User's Answer if not overridden)

Answering these 20 questions will resolve all remaining tactical decisions and provide sufficient detail for robust implementation planning.

---

**Ready for user feedback.** Each question has a `User's Answer` placeholder; once populated, the answers feed directly into the implementation blueprint phase.
